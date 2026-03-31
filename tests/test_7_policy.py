"""
TEST 7 — Policy Layer
Run: python tests/test_7_policy.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.policy.tariff          import TariffManager
from core.policy.carbon          import CarbonPolicy
from core.policy.demand_response import DemandResponseManager
from core.policy.user_rules      import UserRules
from core.policy.policy_manager  import PolicyManager
from core.twin.twin_core         import DigitalTwin


def test_policy():
    print("\n" + "="*50)
    print("  TEST 7 — POLICY LAYER")
    print("="*50)

    # ---- Test 1: Tariff ----
    print("\n--- Test 1: TOU Tariff ---")
    tariff = TariffManager()
    prices = {
        2.0 : ("off_peak",  0.08),
        10.0: ("mid_peak",  0.15),
        19.0: ("on_peak",   0.25)
    }
    for hour, (expected_period, expected_price) in prices.items():
        price  = tariff.get_price(hour)
        period = tariff.get_period_name(hour)
        print(f"   Hour {hour:5.1f}: ${price:.2f} ({period})")
        assert abs(price - expected_price) < 0.001, \
            f"❌ Wrong price at hour {hour}"
    print(f"   Feed-in rate: ${tariff.get_feed_in_rate():.3f}/kWh")
    print(f"   ✅ Tariff pricing correct")

    # ---- Test 2: Carbon ----
    print("\n--- Test 2: Carbon Policy ---")
    carbon = CarbonPolicy(
        carbon_price_per_kg    = 0.02,
        grid_type              = "average_us",
        daily_carbon_budget_kg = 1000.0
    )
    result = carbon.compute_carbon_cost(200.0, dt_hours=0.25)
    print(f"   Import 200kW × 0.25h: {result['carbon_kg']:.4f} kg CO2")
    print(f"   Carbon cost        : ${result['carbon_cost']:.6f}")
    print(f"   Budget remaining   : {result['budget_remaining']:.2f} kg")
    assert result['carbon_kg'] > 0, "❌ Carbon should be tracked"
    assert result['budget_remaining'] < 1000.0, "❌ Budget should decrease"

    avoided = carbon.compute_avoided_emissions(100.0, dt_hours=0.25)
    print(f"   Avoided (100kW PV) : {avoided:.4f} kg CO2")
    print(f"   ✅ Carbon tracking correct")

    # ---- Test 3: Demand Response ----
    print("\n--- Test 3: Demand Response ---")
    dr = DemandResponseManager()

    assert not dr.check_active(12.0), "❌ No event should be active"

    dr.activate_event(
        start_hour          = 17.0,
        end_hour            = 21.0,
        target_reduction_kw = 150.0,
        event_type          = "mandatory"
    )
    assert dr.check_active(18.0), "❌ Event should be active at 18:00"
    assert not dr.check_active(22.0), "❌ Event should not be active at 22:00"

    constraint = dr.get_dr_constraint(
        hour=18.0, current_load_kw=700.0, current_import_kw=500.0)
    print(f"   DR constraint at 18:00: max_import={constraint['max_import_kw']} kW")
    assert constraint['dr_active'], "❌ DR should be active"
    assert constraint['max_import_kw'] < 700.0, "❌ Import should be limited"

    deact = dr.deactivate_event()
    print(f"   Credits earned: ${deact['credits_earned']}")
    print(f"   ✅ Demand response working")

    # ---- Test 4: User Rules ----
    print("\n--- Test 4: User Rules ---")
    rules = UserRules()

    # Test SOC reserve
    state_dict = {"soc": 0.15, "grid_price": 0.25}
    action     = {"action_name": "battery_discharge",
                  "charge_kw": 0.0, "discharge_kw": 30.0,
                  "grid_import_kw": 0.0, "grid_export_kw": 0.0}

    result = rules.check_action(action, state_dict, hour=18.0)
    print(f"   SOC=0.15, discharge: allowed={result['is_allowed']}")
    print(f"   Violations: {result['violations']}")
    assert not result['is_allowed'], "❌ Discharge below reserve should be blocked"
    print(f"   ✅ SOC reserve rule enforced")

    # Test export blackout
    rules.update_rules({"export_blackout_hours": [22, 23, 0, 1]})
    action2 = {"action_name": "export_surplus",
               "charge_kw": 0.0, "discharge_kw": 0.0,
               "grid_import_kw": 0.0, "grid_export_kw": 50.0}
    state2  = {"soc": 0.80, "grid_price": 0.08}
    result2 = rules.check_action(action2, state2, hour=23.0)
    print(f"   Export at blackout hour 23:00: allowed={result2['is_allowed']}")
    assert not result2['is_allowed'], "❌ Export should be blocked at blackout hour"
    print(f"   ✅ Export blackout rule working")

    # ---- Test 5: Policy Manager ----
    print("\n--- Test 5: Policy Manager Integration ---")
    twin   = DigitalTwin(pv_area_m2=500.0, battery_capacity_kwh=100.0)
    policy = PolicyManager()

    state  = twin.twin_step(hour_of_day=18.0, day_type="weekday",
                             grid_import_kw=300.0)
    action = {
        "action_name"   : "peak_shaving",
        "charge_kw"     : 0.0,
        "discharge_kw"  : 30.0,
        "grid_import_kw": 200.0,
        "grid_export_kw": 0.0
    }

    result = policy.evaluate(state, action, cycle_count=0.5)
    print(f"   Grid price     : ${result['grid_price']:.3f}/kWh")
    print(f"   Tariff period  : {result['tariff_period']}")
    print(f"   Total penalty  : {result['total_penalty']:.4f}")
    print(f"   Carbon kg      : {result['policy_costs']['carbon_kg']:.5f}")
    print(f"   Final action   : {result['final_action'].get('action_name')}")
    assert result['grid_price'] > 0, "❌ Grid price must be set"
    assert "final_action" in result, "❌ Must return final action"
    print(f"   ✅ Policy manager integration working")

    print("\n" + "="*50)
    print("  ✅ ALL POLICY TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_policy()