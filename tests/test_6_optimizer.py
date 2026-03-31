"""
TEST 6 — Optimizer / Solver
Run: python tests/test_6_optimizer.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.twin.twin_core        import DigitalTwin
from core.optimizer.solver      import Solver
from core.optimizer.cost_function import CostFunction
from core.optimizer.degradation   import DegradationModel
from core.optimizer.constraints   import Constraints
from core.optimizer.scenario      import ScenarioGenerator
from core.optimizer.sizing        import SystemSizer


def test_optimizer():
    print("\n" + "="*50)
    print("  TEST 6 — OPTIMIZER")
    print("="*50)

    twin   = DigitalTwin(pv_area_m2=500.0, battery_capacity_kwh=100.0)
    solver = Solver()

    # ---- Test 1: Cost function ----
    print("\n--- Test 1: Cost Function ---")
    cost_fn = CostFunction()
    result = cost_fn.compute(
        grid_import_kw   = 100.0,
        grid_export_kw   = 0.0,
        charge_kw        = 0.0,
        discharge_kw     = 0.0,
        pv_kw            = 50.0,
        load_kw          = 150.0,
        grid_price       = 0.25,
        feed_in_tariff   = 0.075,
        degradation_cost = 0.001,
        dt_hours         = 0.25
    )
    print(f"   Import cost    : ${result['import_cost']:.4f}")
    print(f"   Carbon cost    : ${result['carbon_cost']:.4f}")
    print(f"   Total cost     : ${result['total_cost']:.4f}")
    assert result['total_cost'] > 0, "❌ Total cost should be positive"
    assert result['import_cost'] > 0, "❌ Import cost should be positive"
    print(f"   ✅ Cost function working")

    # ---- Test 2: Degradation ----
    print("\n--- Test 2: Degradation Model ---")
    deg = DegradationModel(battery_cost_per_kwh=300.0, battery_capacity_kwh=100.0)
    r_normal  = deg.degradation_cost(20.0, 0.0, 0.50, 0.25, 25.0)
    r_extreme = deg.degradation_cost(20.0, 0.0, 0.95, 0.25, 40.0)
    print(f"   Normal  (SOC=0.50, T=25°C): ${r_normal['degradation_cost']:.6f}")
    print(f"   Extreme (SOC=0.95, T=40°C): ${r_extreme['degradation_cost']:.6f}")
    assert r_extreme['degradation_cost'] > r_normal['degradation_cost'], \
        "❌ Extreme conditions should cost more"
    print(f"   ✅ Degradation increases with stress")

    # ---- Test 3: Constraints ----
    print("\n--- Test 3: Constraints ---")
    con = Constraints()
    result = con.check_power_balance(
        load_kw=300.0, pv_kw=100.0,
        discharge_kw=0.0, charge_kw=0.0,
        grid_import_kw=200.0, grid_export_kw=0.0
    )
    print(f"   Balance check: supply={result['supply_kw']}, "
          f"demand={result['demand_kw']}, "
          f"valid={result['is_valid']}")
    assert result['is_valid'], "❌ Power balance should be valid"
    print(f"   ✅ Constraint checking working")

    # ---- Test 4: Single step optimization ----
    print("\n--- Test 4: Optimization at peak hour (18:00) ---")
    twin.reset(0.70)
    state = twin.twin_step(hour_of_day=18.0, day_type="weekday")
    result = solver.optimize(state)
    best   = result["best_action"]

    print(f"   State: SOC={state.soc:.2%}, "
          f"PV={state.pv_power_kw:.1f}kW, "
          f"Load={state.load_kw:.1f}kW, "
          f"Price=${state.grid_price:.3f}")
    print(f"   Best action  : {best.get('action_name')}")
    print(f"   Description  : {best.get('description')}")
    print(f"   Total cost   : ${best.get('total_cost', 0):.6f}")
    print(f"   Candidates   : {len(result['all_candidates'])}")
    assert best is not None, "❌ Should return a best action"
    assert best.get("action_name") is not None, "❌ Action must have name"
    print(f"   ✅ Optimization working at peak hour")

    # ---- Test 5: Off-peak optimization ----
    print("\n--- Test 5: Optimization at off-peak (2:00) ---")
    twin.reset(0.30)   # Low battery
    state = twin.twin_step(hour_of_day=2.0, day_type="weekday")
    result = solver.optimize(state)
    best   = result["best_action"]
    print(f"   State: SOC={state.soc:.2%}, Price=${state.grid_price:.3f}")
    print(f"   Best action  : {best.get('action_name')}")
    print(f"   ✅ Optimization working at off-peak")

    # ---- Test 6: Horizon optimization (MPC) ----
    print("\n--- Test 6: Horizon optimization (24h plan) ---")
    twin.reset(0.50)
    state    = twin.twin_step(hour_of_day=0.0)
    schedule = solver.optimize_horizon(state)
    print(f"   Schedule steps: {len(schedule)}")
    actions  = [s.get("action_name") for s in schedule if s]
    unique   = list(set(actions))
    print(f"   Unique actions: {unique}")
    assert len(schedule) > 0, "❌ Should return schedule"
    print(f"   ✅ Horizon optimization working")

    # ---- Test 7: System sizing ----
    print("\n--- Test 7: System Sizing ---")
    sizer  = SystemSizer(
        solar_price_per_kw    = 1000.0,
        battery_price_per_kwh = 300.0,
        roof_area_m2          = 1000.0
    )
    sizing = sizer.run_sizing(
        monthly_kwh       = 15000.0,
        budget            = 200000.0,
        solar_range_kw    = [0, 50, 100, 200],
        battery_range_kwh = [0, 50, 100]
    )
    print(f"   Best solar    : {sizing['best_solar_kw']} kW")
    print(f"   Best battery  : {sizing['best_battery_kwh']} kWh")
    print(f"   Annual savings: ${sizing['annual_savings']:.2f}")
    print(f"   ROI           : {sizing['roi_years']:.2f} years")
    assert sizing['best_solar_kw'] >= 0, "❌ Solar size must be non-negative"
    print(f"   ✅ System sizing working")

    print("\n" + "="*50)
    print("  ✅ ALL OPTIMIZER TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_optimizer()