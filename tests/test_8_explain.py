"""
TEST 8 — Explainability Layer
Run: python tests/test_8_explain.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.explain.explain_core  import ExplainCore
from core.explain.decision_text import DecisionTextGenerator
from core.explain.shap_explain  import SHAPExplainer
from core.twin.twin_core        import DigitalTwin
from core.optimizer.solver      import Solver


def test_explain():
    print("\n" + "="*50)
    print("  TEST 8 — EXPLAINABILITY")
    print("="*50)

    twin    = DigitalTwin(pv_area_m2=500.0, battery_capacity_kwh=100.0)
    solver  = Solver()
    explain = ExplainCore()

    # ---- Test 1: SHAP importance ----
    print("\n--- Test 1: Feature importance ---")
    shap = SHAPExplainer()
    state_vec = [0.30, 0.5, 0.6, 0.8, 0.75,
                 1.0,  0.9, 0.0, 0.5, 0.02]
    result = shap.compute_importance(state_vec, cost=0.05)
    print(f"   Method      : {result['method']}")
    print(f"   Top factor  : {result['top_factor']}")
    print(f"   Importances : {result['importances']}")
    assert result['top_factor'] in shap.FEATURE_NAMES, \
        "❌ Top factor must be a valid feature name"
    total_imp = sum(result['importances'].values())
    assert abs(total_imp - 1.0) < 0.01, "❌ Importances must sum to 1"
    print(f"   ✅ Importance sum = {total_imp:.4f} (should be 1.0)")

    # ---- Test 2: Decision text ----
    print("\n--- Test 2: Decision text generation ---")
    text_gen = DecisionTextGenerator()
    state_dict = {
        "soc"                   : 0.30,
        "pv_power_kw"           : 150.0,
        "load_kw"               : 600.0,
        "grid_price"            : 0.25,
        "battery_health"        : 0.85,
        "demand_response_active": False
    }
    cost_bd = {
        "total_cost"      : 0.0450,
        "import_cost"     : 0.0375,
        "degradation_cost": 0.0050,
        "export_revenue"  : 0.0,
        "carbon_cost"     : 0.0025
    }
    text_result = text_gen.generate(
        action_name    = "peak_shaving",
        state_dict     = state_dict,
        cost_breakdown = cost_bd
    )
    print(f"   Action text : {text_result['action_text']}")
    print(f"   Reason text : {text_result['reason_text'][:80]}...")
    print(f"   Cost text   : {text_result['cost_text']}")
    print(f"   Full text   : {text_result['full_text'][:100]}...")
    assert len(text_result['action_text']) > 0, "❌ Action text empty"
    assert len(text_result['reason_text']) > 0, "❌ Reason text empty"
    print(f"   ✅ Text generation working")

    # ---- Test 3: Full explanation ----
    print("\n--- Test 3: Full explanation pipeline ---")
    twin.reset(0.30)
    state  = twin.twin_step(hour_of_day=18.0, day_type="weekday")
    result = solver.optimize(state)
    best   = result["best_action"]

    if best:
        cost_bd = best.get("cost_breakdown", {})
        exp     = explain.explain(state, best, cost_bd)
        print(f"   Action      : {exp['action_name']}")
        print(f"   Decision    : {exp['decision']}")
        print(f"   Reason      : {exp['reason'][:70]}...")
        print(f"   Top factor  : {exp['top_factor']}")
        print(f"   Top factors : {exp['top_factors']}")
        print(f"   Cost summary: {exp['cost_summary']}")
        assert exp['action_name'] is not None, "❌ Action name required"
        assert len(exp['decision']) > 0, "❌ Decision text required"
        assert exp['top_factor'] is not None, "❌ Top factor required"
        print(f"   ✅ Full explanation pipeline working")

    # ---- Test 4: Multiple explanations + history ----
    print("\n--- Test 4: History tracking ---")
    for hour in [6.0, 10.0, 14.0, 18.0, 22.0]:
        twin.reset(0.50)
        state  = twin.twin_step(hour_of_day=hour)
        result = solver.optimize(state)
        best   = result.get("best_action", {})
        if best:
            explain.explain(state, best, best.get("cost_breakdown", {}))

    history = explain.get_explanation_history()
    freq    = explain.get_action_frequency()
    latest  = explain.get_latest_explanation()

    print(f"   History length  : {len(history)}")
    print(f"   Action frequency: {freq}")
    print(f"   Latest action   : {latest.get('action_name') if latest else 'None'}")
    assert len(history) > 0, "❌ History should not be empty"
    print(f"   ✅ History tracking working")

    # ---- Test 5: Schedule summary ----
    print("\n--- Test 5: Schedule summary text ---")
    twin.reset(0.50)
    state    = twin.twin_step(hour_of_day=0.0)
    schedule = solver.optimize_horizon(state)
    summary  = explain.get_schedule_summary_text(schedule)
    print(f"   {summary}")
    assert len(summary) > 0, "❌ Summary should not be empty"
    print(f"   ✅ Schedule summary working")

    print("\n" + "="*50)
    print("  ✅ ALL EXPLAINABILITY TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_explain()