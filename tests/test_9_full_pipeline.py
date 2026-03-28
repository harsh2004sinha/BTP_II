"""
TEST 9 — Full Core Pipeline (24-hour)
Run: python tests/test_9_full_pipeline.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.twin.twin_core        import DigitalTwin
from core.optimizer.solver      import Solver
from core.explain.explain_core  import ExplainCore
from core.policy.policy_manager import PolicyManager


def test_full_pipeline():
    print("\n" + "="*60)
    print("  TEST 9 — FULL PIPELINE (24-HOUR SIMULATION)")
    print("="*60)

    # Build all layers
    twin   = DigitalTwin(
        battery_capacity_kwh = 100.0,
        pv_area_m2           = 500.0,
        base_load_kw         = 200.0,
        peak_load_kw         = 800.0,
        initial_soc          = 0.50
    )
    solver  = Solver()
    explain = ExplainCore()
    policy  = PolicyManager()

    dt_hours    = 0.25
    n_steps     = 96
    total_cost  = 0.0
    total_solar = 0.0
    total_import= 0.0

    print(f"\n{'Step':>4} | {'Hour':>5} | {'SOC':>6} | "
          f"{'PV kW':>7} | {'Load kW':>7} | "
          f"{'Action':>20} | {'Cost':>8}")
    print("-" * 70)

    for t in range(n_steps):
        hour = t * dt_hours

        # Step 1: Twin
        state = twin.twin_step(
            hour_of_day = hour,
            day_type    = "weekday",
            cloud_factor= 0.90
        )

        # Step 2: Optimize
        opt     = solver.optimize(state)
        action  = opt.get("best_action", {})

        # Step 3: Policy
        pol     = policy.evaluate(state, action, state.cycle_count)
        final   = pol["final_action"]

        # Step 4: Explain
        cost_bd = action.get("cost_breakdown", {})
        exp     = explain.explain(state, action, cost_bd)

        # Accumulate
        step_cost    = cost_bd.get("total_cost", 0.0)
        total_cost  += step_cost
        total_solar += state.pv_power_kw * dt_hours
        total_import+= final.get("grid_import_kw", 0.0) * dt_hours

        # Print every 4 steps (every hour)
        if t % 4 == 0:
            print(
                f"{t:>4} | "
                f"{hour:>5.1f} | "
                f"{state.soc:>5.1%} | "
                f"{state.pv_power_kw:>7.1f} | "
                f"{state.load_kw:>7.1f} | "
                f"{action.get('action_name','unknown'):>20} | "
                f"${step_cost:>7.5f}"
            )

    # Final assertions
    print("\n" + "="*60)
    print("  FINAL CHECKS")
    print("="*60)

    final_state = twin.current_state
    print(f"\n  Final SOC          : {final_state.soc:.4f}")
    print(f"  Total cost         : ${total_cost:.4f}")
    print(f"  Total solar used   : {total_solar:.2f} kWh")
    print(f"  Total grid import  : {total_import:.2f} kWh")

    if (total_solar + total_import) > 0:
        solar_frac = total_solar / (total_solar + total_import)
        print(f"  Solar fraction     : {solar_frac:.1%}")

    carbon = policy.get_carbon_summary()
    print(f"  Total CO2          : {carbon['total_carbon_kg']:.2f} kg")

    freq = explain.get_action_frequency()
    print(f"\n  Action distribution:")
    for name, count in freq.items():
        pct = count / n_steps * 100
        print(f"    {name:30}: {count:3d} ({pct:.1f}%)")

    # Assertions
    assert 0.10 <= final_state.soc <= 0.95, "❌ SOC out of range"
    assert total_cost >= 0, "❌ Total cost must be non-negative"
    assert total_solar >= 0, "❌ Solar must be non-negative"
    assert len(freq) > 0, "❌ Must have at least one action type"

    print("\n" + "="*60)
    print("  ✅ FULL PIPELINE TEST PASSED")
    print("="*60)


if __name__ == "__main__":
    test_full_pipeline()