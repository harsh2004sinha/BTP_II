"""
TEST 5 — Digital Twin
Run: python tests/test_5_twin.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.twin.twin_core   import DigitalTwin
from core.twin.forecast    import Forecaster
from core.models.pv_model  import PVModel
from core.models.load_model import LoadModel


def test_twin():
    print("\n" + "="*50)
    print("  TEST 5 — DIGITAL TWIN")
    print("="*50)

    twin = DigitalTwin(
        battery_capacity_kwh = 100.0,
        pv_area_m2           = 500.0,
        base_load_kw         = 200.0,
        peak_load_kw         = 800.0,
        initial_soc          = 0.50,
        mode                 = "simulation"
    )
    print(f"\n✅ Digital Twin created")

    # ----------------------------------------------------------------
    # Test 1: Single step daytime
    # ----------------------------------------------------------------
    print("\n--- Test 1: Single twin step (daytime 10 AM) ---")

    # Fresh twin for this test
    twin.reset(initial_soc=0.50)

    state = twin.twin_step(
        hour_of_day    = 10.0,
        day_type       = "weekday",
        charge_kw      = 10.0,
        discharge_kw   = 0.0,
        grid_import_kw = 50.0,
        grid_export_kw = 0.0,
        cloud_factor   = 1.0
    )
    print(f"   Hour           : {state.hour_of_day}")
    print(f"   SOC            : {state.soc:.4f}")
    print(f"   SOC uncertainty: {state.soc_uncertainty:.4f}")
    print(f"   PV Power       : {state.pv_power_kw:.2f} kW")
    print(f"   PV Available   : {state.pv_available_kw:.2f} kW")
    print(f"   Load           : {state.load_kw:.2f} kW")
    print(f"   Grid Price     : ${state.grid_price:.3f}/kWh")
    print(f"   Net Load       : {state.net_load_kw:.2f} kW")
    print(f"   PV Surplus     : {state.pv_surplus_kw:.2f} kW")
    print(f"   Battery Health : {state.battery_health:.4f}")

    assert state.soc > 0,             "❌ SOC must be positive"
    assert state.pv_power_kw >= 0,    "❌ PV must be non-negative"
    assert state.load_kw > 0,         "❌ Load must be positive"
    assert state.pv_available_kw > 0, "❌ PV available should be > 0 at 10 AM"
    print(f"   ✅ Single step working")

    # ----------------------------------------------------------------
    # Test 2: Night step — FRESH twin so EMA has no carryover
    # ----------------------------------------------------------------
    print("\n--- Test 2: Night step (2 AM) ---")

    # KEY FIX: Reset twin so EMA smoother starts fresh
    twin.reset(initial_soc=0.50)

    state_night = twin.twin_step(
        hour_of_day = 2.0,
        day_type    = "weekday",
        cloud_factor= 1.0
    )
    print(f"   PV power (estimated) : {state_night.pv_power_kw:.4f} kW")
    print(f"   PV available (raw)   : {state_night.pv_available_kw:.4f} kW")
    print(f"   Grid price           : ${state_night.grid_price:.3f}/kWh (off-peak)")

    # Use pv_available_kw (raw physics) for the night check
    # pv_power_kw uses EMA which needs a few steps to settle
    assert state_night.pv_available_kw < 1.0, \
        "❌ PV available should be near zero at night (physics)"
    assert state_night.grid_price <= 0.09, \
        "❌ Should be off-peak at 2 AM"
    print(f"   ✅ Night step correct")

    # ----------------------------------------------------------------
    # Test 3: EMA settles to zero after several night steps
    # ----------------------------------------------------------------
    print("\n--- Test 3: EMA convergence at night ---")

    twin.reset(initial_soc=0.50)

    # Run several night steps — EMA should converge toward 0
    for step in range(8):
        s = twin.twin_step(
            hour_of_day = 2.0 + step * 0.25,
            day_type    = "weekday"
        )

    print(f"   PV power after 8 night steps: {s.pv_power_kw:.4f} kW")
    assert s.pv_power_kw < 10.0, \
        "❌ EMA should converge toward 0 after multiple night steps"
    print(f"   ✅ EMA convergence working")

    # ----------------------------------------------------------------
    # Test 4: Peak hour pricing
    # ----------------------------------------------------------------
    print("\n--- Test 4: Peak hour (6 PM) ---")

    twin.reset(initial_soc=0.50)

    state_peak = twin.twin_step(
        hour_of_day = 18.0,
        day_type    = "weekday"
    )
    print(f"   Grid price at 6 PM: ${state_peak.grid_price:.3f}/kWh (on-peak)")
    assert state_peak.grid_price >= 0.20, \
        "❌ Should be on-peak at 6 PM"
    print(f"   ✅ Peak hour pricing correct")

    # ----------------------------------------------------------------
    # Test 5: Forecast bundle
    # ----------------------------------------------------------------
    print("\n--- Test 5: Forecast bundle ---")

    twin.reset(initial_soc=0.50)
    state = twin.twin_step(hour_of_day=9.0)

    assert state.forecast is not None, "❌ Forecast should not be None"
    f = state.forecast
    print(f"   Forecast horizon    : {f.horizon} steps")
    print(f"   PV mean  (step 0)   : {f.pv_mean[0]:.2f} kW")
    print(f"   Load mean(step 0)   : {f.load_mean[0]:.2f} kW")
    print(f"   Price    (step 0)   : ${f.price_mean[0]:.3f}/kWh")
    print(f"   PV std   (step 0)   : {f.pv_std[0]:.4f}")
    print(f"   Load std (step 0)   : {f.load_std[0]:.4f}")

    assert len(f.pv_mean)    == f.horizon, "❌ PV forecast length mismatch"
    assert len(f.load_mean)  == f.horizon, "❌ Load forecast length mismatch"
    assert len(f.price_mean) == f.horizon, "❌ Price forecast length mismatch"
    print(f"   ✅ Forecast bundle working")

    # ----------------------------------------------------------------
    # Test 6: State vector (for RL agent)
    # ----------------------------------------------------------------
    print("\n--- Test 6: State vector (for RL) ---")

    vec = state.to_vector()
    print(f"   Vector length  : {len(vec)}")
    print(f"   Vector values  : {[round(v, 3) for v in vec]}")

    assert len(vec) == 10, \
        f"❌ State vector should have 10 features, got {len(vec)}"
    assert all(isinstance(v, float) for v in vec), \
        "❌ All values must be float"
    print(f"   ✅ State vector correct (10 features)")

    # ----------------------------------------------------------------
    # Test 7: Full 24-hour day
    # ----------------------------------------------------------------
    print("\n--- Test 7: Full 24-hour day simulation ---")

    twin.reset(initial_soc=0.50)
    day_results = twin.run_day(day_type="weekday", cloud_factor=0.85)

    soc_values  = [r["soc"]          for r in day_results]
    pv_values   = [r["pv_available_kw"] for r in day_results]
    load_values = [r["load_kw"]      for r in day_results]

    print(f"   Steps          : {len(day_results)}")
    print(f"   Initial SOC    : {soc_values[0]:.4f}")
    print(f"   Final SOC      : {soc_values[-1]:.4f}")
    print(f"   Max PV (raw)   : {max(pv_values):.2f} kW")
    print(f"   Peak load      : {max(load_values):.2f} kW")
    print(f"   Min SOC in day : {min(soc_values):.4f}")
    print(f"   Max SOC in day : {max(soc_values):.4f}")

    assert len(day_results) == 96, \
        f"❌ Should have 96 timesteps, got {len(day_results)}"
    assert max(pv_values) > 0, \
        "❌ Should have positive PV during daytime"
    assert all(0.05 <= s <= 1.0 for s in soc_values), \
        "❌ SOC went out of range"
    print(f"   ✅ Full 24-hour simulation working")

    # ----------------------------------------------------------------
    # Test 8: State to dict (JSON serializable)
    # ----------------------------------------------------------------
    print("\n--- Test 8: State to dict ---")

    d = state.to_dict()
    required_keys = [
        "soc", "pv_power_kw", "load_kw", "grid_price",
        "hour_of_day", "battery_health", "timestep",
        "grid_import_kw", "grid_export_kw", "feed_in_tariff",
        "carbon_emitted", "cost_so_far"
    ]
    missing = [k for k in required_keys if k not in d]
    print(f"   Keys present   : {list(d.keys())[:8]}...")
    assert len(missing) == 0, f"❌ Missing keys: {missing}"
    print(f"   ✅ State dict complete ({len(d)} keys)")

    # ----------------------------------------------------------------
    # Test 9: Twin reset
    # ----------------------------------------------------------------
    print("\n--- Test 9: Twin reset ---")

    twin.reset(initial_soc=0.80)
    state_after_reset = twin.twin_step(hour_of_day=12.0)

    print(f"   SOC after reset to 0.80: {twin.battery.soc:.4f}")
    print(f"   Timestep reset to      : {twin.timestep}")
    assert twin.battery.soc <= 0.95,  "❌ Battery SOC out of range after reset"
    assert twin.timestep == 1,        "❌ Timestep should be 1 after reset+step"
    print(f"   ✅ Reset working")

    # ----------------------------------------------------------------
    # Test 10: Properties
    # ----------------------------------------------------------------
    print("\n--- Test 10: State properties ---")

    twin.reset(0.50)

    # High PV, low load → surplus
    state_surplus = twin.twin_step(
        hour_of_day = 12.0,
        irradiance  = 1000.0
    )
    print(f"   PV available : {state_surplus.pv_available_kw:.2f} kW")
    print(f"   Load         : {state_surplus.load_kw:.2f} kW")
    print(f"   Net load     : {state_surplus.net_load_kw:.2f} kW")
    print(f"   PV surplus   : {state_surplus.pv_surplus_kw:.2f} kW")

    assert state_surplus.net_load_kw >= 0,  "❌ Net load must be >= 0"
    assert state_surplus.pv_surplus_kw >= 0,"❌ PV surplus must be >= 0"
    print(f"   ✅ State properties correct")

    print("\n" + "="*50)
    print("  ✅ ALL TWIN TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_twin()