"""
Run ALL tests in order
Run: python tests/run_all_tests.py
"""

import sys
import os
import time
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# TEST REGISTRY
# ============================================================

TEST_REGISTRY = [
    {
        "id"      : 1,
        "name"    : "Battery Model",
        "module"  : "test_1_battery",
        "function": "test_battery",
        "layer"   : "Models"
    },
    {
        "id"      : 2,
        "name"    : "PV Solar Model",
        "module"  : "test_2_pv",
        "function": "test_pv",
        "layer"   : "Models"
    },
    {
        "id"      : 3,
        "name"    : "Load Model",
        "module"  : "test_3_load",
        "function": "test_load",
        "layer"   : "Models"
    },
    {
        "id"      : 4,
        "name"    : "Kalman SOC Filter",
        "module"  : "test_4_kalman",
        "function": "test_kalman",
        "layer"   : "Models"
    },
    {
        "id"      : 5,
        "name"    : "Digital Twin",
        "module"  : "test_5_twin",
        "function": "test_twin",
        "layer"   : "Twin"
    },
    {
        "id"      : 6,
        "name"    : "Optimizer / Solver",
        "module"  : "test_6_optimizer",
        "function": "test_optimizer",
        "layer"   : "Optimizer"
    },
    {
        "id"      : 7,
        "name"    : "Policy Layer",
        "module"  : "test_7_policy",
        "function": "test_policy",
        "layer"   : "Policy"
    },
    {
        "id"      : 8,
        "name"    : "Explainability",
        "module"  : "test_8_explain",
        "function": "test_explain",
        "layer"   : "Explain"
    },
    {
        "id"      : 9,
        "name"    : "Full Pipeline (24h)",
        "module"  : "test_9_full_pipeline",
        "function": "test_full_pipeline",
        "layer"   : "Integration"
    },
]


# ============================================================
# IMPORT HELPER
# ============================================================

def import_test(module_name, func_name):
    """Safely import a test function."""
    try:
        import importlib
        mod  = importlib.import_module(f"tests.{module_name}")
        func = getattr(mod, func_name)
        return func, None
    except Exception as e:
        return None, str(e)


# ============================================================
# SMOKE TEST — checks all imports work
# ============================================================

def run_smoke_test():
    """
    Ultra-quick smoke test.
    Just checks all core files can be imported correctly.
    Run this FIRST before individual tests.
    """
    print("\n" + "=" * 60)
    print("   SMOKE TEST — Checking all imports")
    print("=" * 60)

    imports_to_check = [
        # Models
        ("core.models.battery_model",  "BatteryModel"),
        ("core.models.pv_model",       "PVModel"),
        ("core.models.load_model",     "LoadModel"),
        ("core.models.kalman_soc",     "KalmanSOCEstimator"),
        # Twin
        ("core.twin.twin_state",       "TwinState"),
        ("core.twin.twin_state",       "ForecastBundle"),
        ("core.twin.forecast",         "Forecaster"),
        ("core.twin.state_estimator",  "StateEstimator"),
        ("core.twin.twin_core",        "DigitalTwin"),
        # Optimizer
        ("core.optimizer.cost_function","CostFunction"),
        ("core.optimizer.degradation",  "DegradationModel"),
        ("core.optimizer.constraints",  "Constraints"),
        ("core.optimizer.scenario",     "ScenarioGenerator"),
        ("core.optimizer.sizing",       "SystemSizer"),
        ("core.optimizer.solver",       "Solver"),
        # Learning
        ("core.learning.reward",       "RewardFunction"),
        ("core.learning.rl_env",       "MicrogridEnv"),
        ("core.learning.rl_agent",     "RLAgent"),
        ("core.learning.trainer",      "Trainer"),
        # Explain
        ("core.explain.shap_explain",  "SHAPExplainer"),
        ("core.explain.decision_text", "DecisionTextGenerator"),
        ("core.explain.explain_core",  "ExplainCore"),
        # Policy
        ("core.policy.tariff",         "TariffManager"),
        ("core.policy.carbon",         "CarbonPolicy"),
        ("core.policy.demand_response","DemandResponseManager"),
        ("core.policy.user_rules",     "UserRules"),
        ("core.policy.policy_manager", "PolicyManager"),
    ]

    passed  = []
    failed  = []

    for module_path, class_name in imports_to_check:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            passed.append(f"{module_path}.{class_name}")
            print(f"   ✅  {module_path}.{class_name}")
        except ImportError as e:
            failed.append((f"{module_path}.{class_name}", str(e)))
            print(f"   ❌  {module_path}.{class_name}  →  ImportError: {e}")
        except AttributeError as e:
            failed.append((f"{module_path}.{class_name}", str(e)))
            print(f"   ❌  {module_path}.{class_name}  →  AttributeError: {e}")
        except Exception as e:
            failed.append((f"{module_path}.{class_name}", str(e)))
            print(f"   ❌  {module_path}.{class_name}  →  {type(e).__name__}: {e}")

    print(f"\n   ✅ Passed : {len(passed)}/{len(imports_to_check)}")
    print(f"   ❌ Failed : {len(failed)}/{len(imports_to_check)}")

    if failed:
        print(f"\n   Failed imports:")
        for name, err in failed:
            print(f"      {name}  →  {err}")
        print(f"\n   ⚠️  Fix above imports before running tests.")
    else:
        print(f"\n   🎉 All imports OK — safe to run tests.")

    return len(failed) == 0


# ============================================================
# LAYER-BY-LAYER RUNNER
# ============================================================

def run_layer(layer_name: str):
    """
    Run only tests for a specific layer.

    Args:
        layer_name : "Models" / "Twin" / "Optimizer" /
                     "Policy" / "Explain" / "Integration"
    """
    layer_tests = [t for t in TEST_REGISTRY
                   if t["layer"] == layer_name]

    if not layer_tests:
        print(f"   No tests found for layer: {layer_name}")
        return

    print(f"\n{'='*60}")
    print(f"   RUNNING LAYER: {layer_name}")
    print(f"   Tests: {len(layer_tests)}")
    print(f"{'='*60}")

    passed = []
    failed = []

    for test in layer_tests:
        func, err = import_test(test["module"], test["function"])
        if func is None:
            print(f"\n   ⚠️  [{test['id']}] {test['name']} — SKIPPED: {err}")
            continue

        print(f"\n   Running [{test['id']}] {test['name']}...")
        start = time.time()
        try:
            func()
            elapsed = time.time() - start
            passed.append(test["name"])
            print(f"   ✅ PASSED ({elapsed:.3f}s)")
        except Exception as e:
            elapsed = time.time() - start
            failed.append(test["name"])
            print(f"   ❌ FAILED: {e}")

    print(f"\n   Layer '{layer_name}' result: "
          f"{len(passed)} passed, {len(failed)} failed")


# ============================================================
# SINGLE TEST RUNNER
# ============================================================

def run_single(test_id: int):
    """
    Run a single test by ID.

    Args:
        test_id : 1–9
    """
    test = next((t for t in TEST_REGISTRY if t["id"] == test_id), None)

    if test is None:
        print(f"   No test with ID: {test_id}")
        return

    print(f"\n{'='*60}")
    print(f"   RUNNING [{test['id']}] {test['name']}")
    print(f"{'='*60}")

    func, err = import_test(test["module"], test["function"])
    if func is None:
        print(f"   ⚠️  SKIPPED: {err}")
        return

    start = time.time()
    try:
        func()
        elapsed = time.time() - start
        print(f"\n   ✅ PASSED ({elapsed:.3f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n   ❌ FAILED: {e}")
        traceback.print_exc()


# ============================================================
# FULL TEST RUNNER
# ============================================================

def run_all_tests(stop_on_fail: bool = False):
    """
    Run all tests in order.

    Args:
        stop_on_fail : Stop after first failure
    """
    print("\n" + "🔋" * 30)
    print("   INTELLIGENT MICROGRID EMS — FULL TEST SUITE")
    print("🔋" * 30)
    print(f"\n   Total tests  : {len(TEST_REGISTRY)}")
    print(f"   Stop on fail : {stop_on_fail}")

    passed  = []
    failed  = []
    skipped = []

    start_total = time.time()

    for test in TEST_REGISTRY:
        test_id   = test["id"]
        test_name = test["name"]
        layer     = test["layer"]

        print(f"\n{'='*60}")
        print(f"  [{test_id}/{len(TEST_REGISTRY)}] {layer} — {test_name}")
        print(f"{'='*60}")

        func, import_err = import_test(test["module"], test["function"])

        if func is None:
            print(f"  ⚠️  SKIPPED — Could not import: {import_err}")
            skipped.append({
                "id"    : test_id,
                "name"  : test_name,
                "reason": import_err
            })
            continue

        start = time.time()
        try:
            func()
            elapsed = time.time() - start
            passed.append({
                "id"     : test_id,
                "name"   : test_name,
                "elapsed": round(elapsed, 3)
            })
            print(f"\n  ✅ PASSED ({elapsed:.3f}s)")

        except AssertionError as e:
            elapsed = time.time() - start
            print(f"\n  ❌ FAILED (AssertionError): {e}")
            failed.append({
                "id"     : test_id,
                "name"   : test_name,
                "error"  : str(e),
                "elapsed": round(elapsed, 3)
            })
            if stop_on_fail:
                print("  Stopping on first failure.")
                break

        except Exception as e:
            elapsed = time.time() - start
            print(f"\n  ❌ FAILED ({type(e).__name__}): {e}")
            traceback.print_exc()
            failed.append({
                "id"     : test_id,
                "name"   : test_name,
                "error"  : str(e),
                "elapsed": round(elapsed, 3)
            })
            if stop_on_fail:
                print("  Stopping on first failure.")
                break

    total_elapsed = time.time() - start_total

    # ============================================================
    # FINAL REPORT
    # ============================================================

    print("\n\n" + "=" * 60)
    print("   FINAL TEST REPORT")
    print("=" * 60)

    print(f"\n   Total time  : {total_elapsed:.2f}s")
    print(f"   Tests run   : {len(passed) + len(failed)} / {len(TEST_REGISTRY)}")
    print(f"   ✅ Passed   : {len(passed)}")
    print(f"   ❌ Failed   : {len(failed)}")
    print(f"   ⚠️  Skipped  : {len(skipped)}")

    if passed:
        print(f"\n   ✅ PASSED:")
        for p in passed:
            print(f"      [{p['id']}] {p['name']:35s}  {p['elapsed']}s")

    if failed:
        print(f"\n   ❌ FAILED:")
        for f in failed:
            print(f"      [{f['id']}] {f['name']:35s}  → {f['error'][:60]}")

    if skipped:
        print(f"\n   ⚠️  SKIPPED:")
        for s in skipped:
            print(f"      [{s['id']}] {s['name']:35s}  → {s['reason'][:60]}")

    print("\n" + "=" * 60)
    if len(failed) == 0 and len(skipped) == 0:
        print("   🎉 ALL TESTS PASSED — CORE IS FULLY WORKING")
    elif len(failed) == 0:
        print("   ✅ ALL RUN TESTS PASSED (some skipped)")
    else:
        print(f"   ⚠️  {len(failed)} TEST(S) FAILED — SEE ABOVE")
    print("=" * 60 + "\n")

    return {
        "passed" : len(passed),
        "failed" : len(failed),
        "skipped": len(skipped),
        "total"  : len(TEST_REGISTRY)
    }


# ============================================================
# MAIN — CLI INTERFACE
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("   MICROGRID EMS TEST RUNNER")
    print("=" * 60)
    print("\n   Options:")
    print("     python tests/run_all_tests.py          → Run all tests")
    print("     python tests/run_all_tests.py smoke    → Smoke test only")
    print("     python tests/run_all_tests.py 1        → Run test 1 only")
    print("     python tests/run_all_tests.py models   → Run Models layer")
    print("     python tests/run_all_tests.py twin     → Run Twin layer")
    print("     python tests/run_all_tests.py opt      → Run Optimizer layer")
    print("     python tests/run_all_tests.py policy   → Run Policy layer")
    print("     python tests/run_all_tests.py explain  → Run Explain layer")
    print("     python tests/run_all_tests.py full     → Run Integration test")
    print("     python tests/run_all_tests.py stop     → Run all, stop on fail")

    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if arg == "smoke":
        run_smoke_test()

    elif arg.isdigit():
        run_single(int(arg))

    elif arg == "models":
        run_layer("Models")

    elif arg == "twin":
        run_layer("Twin")

    elif arg in ("opt", "optimizer"):
        run_layer("Optimizer")

    elif arg == "policy":
        run_layer("Policy")

    elif arg == "explain":
        run_layer("Explain")

    elif arg in ("full", "integration"):
        run_layer("Integration")

    elif arg == "stop":
        run_all_tests(stop_on_fail=True)

    else:
        # First run smoke test, then all tests
        smoke_ok = run_smoke_test()
        if smoke_ok:
            run_all_tests(stop_on_fail=False)
        else:
            print("\n   ⚠️  Smoke test failed.")
            print("   Fix import errors before running full suite.")