"""
TEST 3 — Load Model
Run: python tests/test_3_load.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.load_model import LoadModel


def test_load():
    print("\n" + "="*50)
    print("  TEST 3 — LOAD MODEL")
    print("="*50)

    load = LoadModel(
        base_load_kw  = 200.0,
        peak_load_kw  = 800.0
    )

    print(f"\n✅ Load model created")
    print(f"   Base load : {load.base_load_kw} kW")
    print(f"   Peak load : {load.peak_load_kw} kW")

    # ---- Test 1: Different hours ----
    print("\n--- Test 1: Load at different hours ---")
    hours = [0.0, 6.0, 9.0, 12.0, 14.0, 18.0, 22.0]
    for h in hours:
        kw = load.load_power(h, "weekday", add_noise=False)
        print(f"   Hour {h:5.1f}: {kw:.1f} kW")

    noon = load.load_power(13.0, "weekday", False)
    midnight = load.load_power(2.0, "weekday", False)
    assert noon > midnight, "❌ Noon should be higher than midnight"
    print(f"   ✅ Load profile shape is correct (peak > night)")

    # ---- Test 2: Day type multipliers ----
    print("\n--- Test 2: Day type comparison ---")
    for dtype in ["weekday", "saturday", "sunday", "holiday"]:
        kw = load.load_power(10.0, dtype, add_noise=False)
        print(f"   {dtype:10s} at 10:00: {kw:.1f} kW")

    weekday = load.load_power(10.0, "weekday", False)
    holiday = load.load_power(10.0, "holiday", False)
    assert weekday > holiday, "❌ Weekday should be higher than holiday"
    print(f"   ✅ Day multipliers working")

    # ---- Test 3: Daily profile ----
    print("\n--- Test 3: 15-min daily profile ---")
    profile = load.generate_daily_profile("weekday", dt_hours=0.25, add_noise=False)
    print(f"   Timesteps: {len(profile)}")
    print(f"   First entry: {profile[0]}")
    print(f"   Peak load  : {max(p['load_kw'] for p in profile):.1f} kW")
    print(f"   Min load   : {min(p['load_kw'] for p in profile):.1f} kW")
    assert len(profile) == 96, "❌ Should have 96 timesteps"
    print(f"   ✅ Daily profile has 96 steps (24h × 4)")

    # ---- Test 4: Bill scaling ----
    print("\n--- Test 4: Monthly bill scaling ---")
    target_monthly = 15000.0
    profile = load.from_monthly_bill(target_monthly, "weekday", dt_hours=0.25)
    daily_kwh = sum(p["energy_kwh"] for p in profile)
    expected_daily = target_monthly / 30.0
    error_pct = abs(daily_kwh - expected_daily) / expected_daily * 100
    print(f"   Target monthly  : {target_monthly} kWh")
    print(f"   Expected daily  : {expected_daily:.2f} kWh")
    print(f"   Actual daily    : {daily_kwh:.2f} kWh")
    print(f"   Error           : {error_pct:.2f}%")
    assert error_pct < 1.0, "❌ Bill scaling error too large"
    print(f"   ✅ Bill scaling accurate")

    # ---- Test 5: Noise ----
    print("\n--- Test 5: Load noise (stochastic) ---")
    readings = [load.load_power(10.0, "weekday", True) for _ in range(20)]
    unique = len(set(round(r, 1) for r in readings))
    print(f"   20 readings at 10:00, all different: {unique > 1}")
    print(f"   Min: {min(readings):.1f}, Max: {max(readings):.1f}")
    assert unique > 1, "❌ Noise not being applied"
    print(f"   ✅ Noise working")

    print("\n" + "="*50)
    print("  ✅ ALL LOAD TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_load()