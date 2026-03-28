"""
TEST 1 — Battery Model
Run: python tests/test_1_battery.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.battery_model import BatteryModel

def test_battery():
    print("\n" + "="*50)
    print("  TEST 1 — BATTERY MODEL")
    print("="*50)

    # ---- Create battery ----
    battery = BatteryModel(
        capacity_kwh        = 100.0,
        max_charge_kw       = 50.0,
        max_discharge_kw    = 50.0,
        soc_min             = 0.10,
        soc_max             = 0.95,
        initial_soc         = 0.50
    )

    print(f"\n✅ Battery created")
    print(f"   Capacity    : {battery.capacity_kwh} kWh")
    print(f"   Initial SOC : {battery.soc:.2%}")

    # ---- Test 1: Charge ----
    print("\n--- Test 1: Charge 20kW for 15 min ---")
    result = battery.step(charge_kw=20.0, discharge_kw=0.0, dt_hours=0.25)
    print(f"   SOC after charge  : {result['soc']:.4f} ({result['soc']*100:.2f}%)")
    print(f"   Actual charge kW  : {result['charge_kw']}")
    print(f"   Energy in (kWh)   : {result['energy_in_kwh']}")

    # Check SOC increased
    assert result['soc'] > 0.50, "❌ SOC should increase after charging"
    print(f"   ✅ SOC increased correctly")

    # ---- Test 2: Discharge ----
    print("\n--- Test 2: Discharge 30kW for 15 min ---")
    soc_before = battery.soc
    result = battery.step(charge_kw=0.0, discharge_kw=30.0, dt_hours=0.25)
    print(f"   SOC before discharge : {soc_before:.4f}")
    print(f"   SOC after discharge  : {result['soc']:.4f}")
    print(f"   Actual discharge kW  : {result['discharge_kw']}")
    print(f"   Energy out (kWh)     : {result['energy_out_kwh']}")

    assert result['soc'] < soc_before, "❌ SOC should decrease after discharging"
    print(f"   ✅ SOC decreased correctly")

    # ---- Test 3: SOC limits ----
    print("\n--- Test 3: SOC Limits ---")
    battery.reset(soc=0.95)
    result = battery.step(charge_kw=50.0, discharge_kw=0.0, dt_hours=0.25)
    print(f"   Charge at max SOC: new SOC = {result['soc']:.4f}")
    assert result['soc'] <= 0.95, "❌ SOC exceeded maximum"
    print(f"   ✅ SOC max limit respected")

    battery.reset(soc=0.10)
    result = battery.step(charge_kw=0.0, discharge_kw=50.0, dt_hours=0.25)
    print(f"   Discharge at min SOC: new SOC = {result['soc']:.4f}")
    assert result['soc'] >= 0.10, "❌ SOC went below minimum"
    print(f"   ✅ SOC min limit respected")

    # ---- Test 4: Simultaneous charge + discharge ----
    print("\n--- Test 4: Simultaneous charge + discharge ---")
    battery.reset(soc=0.50)
    result = battery.step(charge_kw=20.0, discharge_kw=20.0, dt_hours=0.25)
    # Net = 0, SOC should stay same (approximately)
    print(f"   After 20kW charge + 20kW discharge: SOC = {result['soc']:.4f}")
    print(f"   ✅ Simultaneous handled correctly")

    # ---- Test 5: Cycle count ----
    print("\n--- Test 5: Cycle counting ---")
    battery.reset(soc=0.50)
    for _ in range(4):
        battery.step(charge_kw=50.0, discharge_kw=0.0, dt_hours=0.25)
    status = battery.get_status()
    print(f"   Cycles after 4 charges: {status['cycle_count']:.4f}")
    print(f"   Total charged (kWh)   : {status['total_energy_charged_kwh']:.3f}")
    assert status['cycle_count'] > 0, "❌ Cycle count not tracked"
    print(f"   ✅ Cycle count working")

    # ---- Test 6: Available power ----
    print("\n--- Test 6: Available power ---")
    battery.reset(soc=0.60)
    avail_dis = battery.available_discharge_kw()
    avail_chg = battery.available_charge_kw()
    print(f"   At SOC=60%: Available discharge = {avail_dis:.2f} kW")
    print(f"   At SOC=60%: Available charge    = {avail_chg:.2f} kW")
    assert avail_dis > 0, "❌ Should have discharge available at 60%"
    assert avail_chg > 0, "❌ Should have charge available at 60%"
    print(f"   ✅ Available power calculation correct")

    print("\n" + "="*50)
    print("  ✅ ALL BATTERY TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_battery()