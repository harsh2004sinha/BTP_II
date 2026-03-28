"""
TEST 2 — PV Solar Model
Run: python tests/test_2_pv.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.pv_model import PVModel


def test_pv():
    print("\n" + "="*50)
    print("  TEST 2 — PV SOLAR MODEL")
    print("="*50)

    pv = PVModel(
        panel_efficiency    = 0.20,
        system_losses       = 0.14,
        inverter_efficiency = 0.97
    )

    print(f"\n✅ PV model created")
    print(f"   Base efficiency: {pv.base_efficiency:.4f}")

    # ---- Test 1: Zero irradiance (night) ----
    print("\n--- Test 1: Zero irradiance (night) ---")
    result = pv.pv_power(irradiance_wm2=0.0, area_m2=500.0)
    print(f"   Power at 0 W/m²: {result['power_kw']} kW")
    assert result['power_kw'] == 0.0, "❌ Should be 0 at night"
    print(f"   ✅ Zero power at night")

    # ---- Test 2: Peak irradiance ----
    print("\n--- Test 2: Peak irradiance (1000 W/m²) ---")
    result = pv.pv_power(
        irradiance_wm2 = 1000.0,
        area_m2        = 500.0,
        ambient_temp_c = 25.0
    )
    print(f"   Power at 1000 W/m², 500m², 25°C: {result['power_kw']:.3f} kW")
    print(f"   Cell temperature               : {result['cell_temp_c']:.2f}°C")
    print(f"   Effective efficiency           : {result['efficiency']:.4f}")
    assert result['power_kw'] > 0, "❌ Power should be positive"
    print(f"   ✅ Power generated correctly")

    # ---- Test 3: Temperature effect ----
    print("\n--- Test 3: Temperature derating ---")
    p_25 = pv.pv_power(800.0, 500.0, 25.0)["power_kw"]
    p_45 = pv.pv_power(800.0, 500.0, 45.0)["power_kw"]
    print(f"   Power at 25°C : {p_25:.3f} kW")
    print(f"   Power at 45°C : {p_45:.3f} kW")
    print(f"   Loss due to heat: {p_25-p_45:.3f} kW ({(p_25-p_45)/p_25*100:.1f}%)")
    assert p_25 > p_45, "❌ Higher temp should give lower power"
    print(f"   ✅ Temperature derating working")

    # ---- Test 4: Area scaling ----
    print("\n--- Test 4: Area scaling ---")
    p_500  = pv.pv_power(800.0, 500.0)["power_kw"]
    p_1000 = pv.pv_power(800.0, 1000.0)["power_kw"]
    print(f"   Power at 500m²  : {p_500:.3f} kW")
    print(f"   Power at 1000m² : {p_1000:.3f} kW")
    assert abs(p_1000 / p_500 - 2.0) < 0.01, "❌ Power should double with double area"
    print(f"   ✅ Area scaling correct")

    # ---- Test 5: Daily profile ----
    print("\n--- Test 5: Daily profile (24h) ---")
    irradiance = PVModel.synthetic_irradiance(n_steps=96, peak_irr=900.0)
    profile    = pv.generate_daily_profile(irradiance, area_m2=500.0)
    max_power  = max(p["power_kw"] for p in profile)
    total_kwh  = sum(p["energy_kwh"] for p in profile)
    night_pts  = sum(1 for p in profile if p["power_kw"] == 0.0)
    print(f"   Total timesteps : {len(profile)}")
    print(f"   Peak power      : {max_power:.3f} kW")
    print(f"   Total energy    : {total_kwh:.2f} kWh")
    print(f"   Night timesteps : {night_pts}")
    assert len(profile) == 96, "❌ Should have 96 timesteps"
    assert max_power > 0,      "❌ Should have positive peak power"
    assert night_pts > 0,      "❌ Should have night timesteps"
    print(f"   ✅ Daily profile correct")

    # ---- Test 6: System sizing ----
    print("\n--- Test 6: System sizing ---")
    sizing = pv.size_system(
        target_kwh_per_day     = 500.0,
        roof_area_available_m2 = 1000.0
    )
    print(f"   Target: 500 kWh/day")
    print(f"   Required area  : {sizing['required_area_m2']:.1f} m²")
    print(f"   Peak power     : {sizing['peak_power_kw']:.2f} kW")
    print(f"   Daily energy   : {sizing['daily_energy_kwh']:.2f} kWh")
    print(f"   Roof limited   : {sizing['roof_limited']}")
    assert sizing['peak_power_kw'] > 0, "❌ Should have positive peak power"
    print(f"   ✅ System sizing working")

    print("\n" + "="*50)
    print("  ✅ ALL PV TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_pv()