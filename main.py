"""
main.py
=======
Entry point for the Energy Management System.

Serves dual purpose:
  1. FastAPI application server (import as module or run with uvicorn)
  2. Core pipeline test suite (run directly with: python main.py)

FastAPI server:
    uvicorn main:app --reload

Core test suite:
    python main.py
"""

import json
import logging
import numpy as np

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import create_tables
from app.config import settings

# Import each router
from app.routers.auth       import router as auth_router
from app.routers.plans      import router as plans_router
from app.routers.upload     import router as upload_router
from app.routers.weather    import router as weather_router
from app.routers.results    import router as results_router
from app.routers.prediction import router as prediction_router


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# SCHEDULER
# ============================================================

scheduler = BackgroundScheduler()


def scheduled_update():
    logger.info("Scheduler: running periodic update...")
    from app.database import SessionLocal
    from app.services.algorithm_service import AlgorithmService

    db = SessionLocal()
    try:
        AlgorithmService.run_scheduled_update(db)
    except Exception as e:
        logger.warning("Scheduler update failed: %s", e)
    finally:
        db.close()


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Energy Management System...")
    create_tables()
    logger.info("Database tables created/verified")
    scheduler.add_job(
        scheduled_update,
        "interval",
        minutes=settings.UPDATE_INTERVAL_MINUTES,
        id="prediction_update"
    )
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Server stopped")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Energy Management System API",
    description="Intelligent Cost-Optimized Energy Management Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(plans_router)
app.include_router(upload_router)
app.include_router(weather_router)
app.include_router(results_router)
app.include_router(prediction_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return JSONResponse({
        "status":  "healthy",
        "version": settings.APP_VERSION
    })


# ============================================================
# TEST SUITE HELPERS
# ============================================================

def section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def subsection(title: str):
    """Print a subsection header."""
    print(f"\n--- {title} ---")


# ============================================================
# 1. MODELS TEST
# ============================================================

def test_models():
    section("LAYER 1 — MODELS")

    from core.models.battery_model import BatteryModel
    from core.models.pv_model      import PVModel
    from core.models.load_model    import LoadModel
    from core.models.kalman_soc    import KalmanSOCEstimator

    # Battery
    subsection("Battery Model")
    batt = BatteryModel(capacity_kwh=100.0, initial_soc=0.50)
    result = batt.step(charge_kw=20.0, discharge_kw=0.0, dt_hours=0.25)
    print(f"  After charging 20kW for 15min:")
    print(f"  SOC: {result['soc']:.4f} | Charge: {result['charge_kw']}kW")
    print(f"  Cycles: {result['cycle_count']:.4f}")

    result = batt.step(charge_kw=0.0, discharge_kw=30.0, dt_hours=0.25)
    print(f"  After discharging 30kW:")
    print(f"  SOC: {result['soc']:.4f} | Discharge: {result['discharge_kw']}kW")

    status = batt.get_status()
    print(f"  Battery status: {status}")

    # PV Model
    subsection("PV Model")
    pv = PVModel()
    result = pv.pv_power(irradiance_wm2=800.0, area_m2=500.0, ambient_temp_c=30.0)
    print(f"  PV at 800 W/m², 500m², 30°C:")
    print(f"  Power: {result['power_kw']:.3f} kW")
    print(f"  Cell temp: {result['cell_temp_c']}°C")
    print(f"  Efficiency: {result['efficiency']:.4f}")

    sizing = pv.size_system(
        target_kwh_per_day=1000.0,
        roof_area_available_m2=1000.0
    )
    print(f"  Sizing for 1000 kWh/day: {sizing}")

    # Load Model
    subsection("Load Model")
    load = LoadModel(base_load_kw=200.0, peak_load_kw=800.0)
    print(f"  Load at 9:00 AM (weekday) : {load.load_power(9.0, 'weekday', False):.1f} kW")
    print(f"  Load at 2:00 AM (weekday) : {load.load_power(2.0, 'weekday', False):.1f} kW")
    print(f"  Load at 6:00 PM (saturday): {load.load_power(18.0, 'saturday', False):.1f} kW")
    print(f"  Daily energy (weekday)    : {load.get_daily_energy_kwh('weekday'):.1f} kWh")

    bill_profile = load.from_monthly_bill(monthly_units_kwh=15000.0)
    total_kwh = sum(p["energy_kwh"] for p in bill_profile)
    print(f"  Bill profile (15000 kWh/month): {total_kwh:.1f} kWh/day")

    # Kalman Filter
    subsection("Kalman SOC Estimator")
    kalman = KalmanSOCEstimator(initial_soc=0.50)
    for i in range(5):
        voltage = 90.0 + np.random.normal(0, 0.5)
        result = kalman.update(
            current_soc_model   = 0.50 + i * 0.02,
            voltage_measurement = voltage
        )
    print(f"  Kalman estimate after 5 steps: {result['soc_estimate']:.4f}")
    print(f"  Uncertainty std             : {result['uncertainty_std']:.4f}")
    print(f"  95% CI                      : {kalman.get_confidence_interval()}")


# ============================================================
# 2. DIGITAL TWIN TEST
# ============================================================

def test_digital_twin():
    section("LAYER 2 — DIGITAL TWIN")

    from core.twin.twin_core    import DigitalTwin
    from core.twin.forecast     import Forecaster
    from core.models.pv_model   import PVModel
    from core.models.load_model import LoadModel

    twin = DigitalTwin(
        battery_capacity_kwh = 100.0,
        pv_area_m2           = 500.0,
        base_load_kw         = 200.0,
        peak_load_kw         = 800.0,
        initial_soc          = 0.60,
        mode                 = "simulation"
    )

    subsection("Single Twin Step")
    state = twin.twin_step(
        hour_of_day    = 10.0,
        day_type       = "weekday",
        charge_kw      = 10.0,
        discharge_kw   = 0.0,
        grid_import_kw = 50.0,
        grid_export_kw = 0.0,
        cloud_factor   = 0.9
    )
    print(f"  Hour        : {state.hour_of_day}")
    print(f"  SOC         : {state.soc:.4f} ({state.soc*100:.1f}%)")
    print(f"  PV Power    : {state.pv_power_kw:.2f} kW")
    print(f"  Load        : {state.load_kw:.2f} kW")
    print(f"  Grid Price  : ${state.grid_price:.3f}/kWh")
    print(f"  Net Load    : {state.net_load_kw:.2f} kW")
    print(f"  PV Surplus  : {state.pv_surplus_kw:.2f} kW")

    subsection("Forecast Bundle")
    forecaster = Forecaster(
        pv_model   = PVModel(),
        load_model = LoadModel(),
        horizon    = 8
    )
    bundle = forecaster.get_forecast_bundle(
        current_hour = 10.0,
        area_m2      = 500.0,
        day_type     = "weekday"
    )
    print(f"  PV mean  (next 8 steps): {[round(v,1) for v in bundle.pv_mean]}")
    print(f"  Load mean(next 8 steps): {[round(v,1) for v in bundle.load_mean]}")
    print(f"  Price    (next 8 steps): {bundle.price_mean}")

    subsection("Run Full Day (96 steps)")
    twin.reset(initial_soc=0.50)
    day_results = twin.run_day(day_type="weekday", cloud_factor=0.85)
    print(f"  Steps simulated         : {len(day_results)}")
    print(f"  Final SOC               : {day_results[-1]['soc']:.4f}")
    print(f"  Max PV in day           : {max(r['pv_power_kw'] for r in day_results):.2f} kW")
    print(f"  Peak load               : {max(r['load_kw'] for r in day_results):.2f} kW")
    print(f"  Total cost              : ${day_results[-1]['cost_so_far']:.4f}")


# ============================================================
# 3. OPTIMIZER TEST
# ============================================================

def test_optimizer():
    section("LAYER 3 — OPTIMIZER")

    from core.twin.twin_core          import DigitalTwin
    from core.optimizer.solver        import Solver
    from core.optimizer.sizing        import SystemSizer
    from core.optimizer.scenario      import ScenarioGenerator
    from core.optimizer.cost_function import CostFunction
    from core.optimizer.degradation   import DegradationModel

    twin   = DigitalTwin(pv_area_m2=500.0, battery_capacity_kwh=100.0)
    solver = Solver()

    subsection("Single Step Optimization")
    state = twin.twin_step(
        hour_of_day    = 17.5,
        day_type       = "weekday",
        grid_import_kw = 0.0,
        grid_export_kw = 0.0
    )

    result = solver.optimize(state)
    best   = result["best_action"]

    print(f"  Hour        : {state.hour_of_day} (On-Peak)")
    print(f"  SOC         : {state.soc:.4f}")
    print(f"  Grid Price  : ${state.grid_price:.3f}/kWh")
    print(f"  PV Power    : {state.pv_power_kw:.2f} kW")
    print(f"  Load        : {state.load_kw:.2f} kW")
    print(f"\n  Best Action : {best.get('action_name')}")
    print(f"  Description : {best.get('description')}")
    print(f"  Total Cost  : ${best.get('total_cost', 0):.6f}")
    print(f"  Charge kW   : {best.get('charge_kw', 0):.2f}")
    print(f"  Discharge kW: {best.get('discharge_kw', 0):.2f}")
    print(f"  Grid Import : {best.get('grid_import_kw', 0):.2f}")
    print(f"  Grid Export : {best.get('grid_export_kw', 0):.2f}")
    print(f"  Violations  : {best.get('violations', [])}")

    subsection("Horizon Optimization (MPC)")
    twin.reset(0.50)
    state    = twin.twin_step(hour_of_day=8.0, day_type="weekday")
    schedule = solver.optimize_horizon(state, forecast=state.forecast)
    print(f"  Schedule steps    : {len(schedule)}")
    print(f"  Actions in plan   :")
    action_counts = {}
    for s in schedule:
        if s:
            n = s.get("action_name", "unknown")
            action_counts[n] = action_counts.get(n, 0) + 1
    for name, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        print(f"    {name:30s}: {count} steps")

    subsection("System Sizing")
    sizer = SystemSizer(
        solar_price_per_kw    = 1000.0,
        battery_price_per_kwh = 300.0,
        grid_price            = 0.15,
        roof_area_m2          = 1000.0
    )
    sizing = sizer.run_sizing(
        monthly_kwh       = 15000.0,
        budget            = 150000.0,
        solar_range_kw    = [0, 50, 100, 150, 200],
        battery_range_kwh = [0, 50, 100, 150]
    )
    print(f"  Best Solar Size   : {sizing['best_solar_kw']} kW")
    print(f"  Best Battery Size : {sizing['best_battery_kwh']} kWh")
    print(f"  Daily Savings     : ${sizing['daily_savings']:.4f}")
    print(f"  Annual Savings    : ${sizing['annual_savings']:.2f}")
    print(f"  Investment        : ${sizing['investment']:.2f}")
    print(f"  ROI               : {sizing['roi_years']:.2f} years")

    subsection("Degradation Model")
    deg = DegradationModel(
        battery_cost_per_kwh = 300.0,
        battery_capacity_kwh = 100.0
    )
    result = deg.degradation_cost(
        charge_kw     = 30.0,
        discharge_kw  = 0.0,
        current_soc   = 0.90,
        dt_hours      = 0.25,
        temperature_c = 35.0
    )
    print(f"  Degradation at SOC=0.90, T=35°C, 30kW charge:")
    print(f"  Cost           : ${result['degradation_cost']:.6f}")
    print(f"  SOC stress     : {result['soc_stress_factor']:.4f}")
    print(f"  C-rate stress  : {result['crate_stress_factor']:.4f}")
    print(f"  Temp stress    : {result['temp_stress_factor']:.4f}")

    subsection("Scenario Generator")
    gen = ScenarioGenerator(n_scenarios=5)
    twin.reset(0.5)
    state = twin.twin_step(hour_of_day=9.0)
    if state.forecast:
        scenarios = gen.generate(state.forecast, n_scenarios=3)
        print(f"  Generated {len(scenarios)} scenarios")
        for sc in scenarios:
            pv_sum   = sum(sc["pv"][:4])
            load_sum = sum(sc["load"][:4])
            print(f"  Scenario {sc['scenario_id']}: PV={pv_sum:.1f}kWh, Load={load_sum:.1f}kWh")


# ============================================================
# 4. POLICY TEST
# ============================================================

def test_policy():
    section("LAYER 6 — POLICY")

    from core.policy.tariff          import TariffManager
    from core.policy.carbon          import CarbonPolicy
    from core.policy.demand_response import DemandResponseManager
    from core.policy.user_rules      import UserRules
    from core.policy.policy_manager  import PolicyManager
    from core.twin.twin_core         import DigitalTwin

    subsection("Tariff Manager")
    tariff = TariffManager()
    for h in [2.0, 10.0, 19.0]:
        print(f"  Hour {h:5.1f}: ${tariff.get_price(h):.2f}/kWh "
              f"({tariff.get_period_name(h)})")
    print(f"  Feed-in rate: ${tariff.get_feed_in_rate():.3f}/kWh")
    print(f"  Cheapest 2h : {tariff.get_cheapest_hours(2)[:4]}")
    print(f"  Peak hours  : {tariff.get_most_expensive_hours(2)[:4]}")

    subsection("Carbon Policy")
    carbon = CarbonPolicy(
        carbon_price_per_kg    = 0.02,
        grid_type              = "average_us",
        daily_carbon_budget_kg = 500.0
    )
    for imp in [100.0, 200.0, 300.0]:
        c = carbon.compute_carbon_cost(imp, dt_hours=0.25)
        print(f"  Import {imp}kW: {c['carbon_kg']:.3f} kg CO2, "
              f"cost ${c['carbon_cost']:.4f}")
    print(f"  Carbon summary: {carbon.get_summary()}")

    subsection("Demand Response")
    dr = DemandResponseManager(
        max_curtailment_kw = 200.0,
        dr_incentive_rate  = 0.50
    )
    activation = dr.activate_event(
        start_hour          = 17.0,
        end_hour            = 21.0,
        target_reduction_kw = 150.0,
        event_type          = "mandatory"
    )
    print(f"  DR activation: {activation['message']}")

    constraint = dr.get_dr_constraint(
        hour              = 18.0,
        current_load_kw   = 700.0,
        current_import_kw = 500.0
    )
    print(f"  DR constraint at 18:00: {constraint}")

    deactivation = dr.deactivate_event()
    print(f"  Credits earned: ${deactivation['credits_earned']}")

    subsection("User Rules")
    rules = UserRules()
    print(rules.get_rule_summary())

    update = rules.update_rules({
        "min_soc_reserve"        : 0.25,
        "allow_grid_export"      : True,
        "max_battery_cycles_day" : 1.5,
        "export_blackout_hours"  : [22, 23, 0, 1]
    })
    print(f"\n  Updated rules   : {list(update['validated'].keys())}")
    print(f"  Rejected rules  : {list(update['rejected'].keys())}")

    subsection("Policy Manager — Full Evaluation")
    twin   = DigitalTwin(pv_area_m2=500.0, battery_capacity_kwh=100.0)
    policy = PolicyManager()

    state = twin.twin_step(
        hour_of_day    = 18.0,
        day_type       = "weekday",
        grid_import_kw = 300.0,
        grid_export_kw = 0.0
    )

    action = {
        "action_name"   : "peak_shaving",
        "charge_kw"     : 0.0,
        "discharge_kw"  : 30.0,
        "grid_import_kw": 200.0,
        "grid_export_kw": 0.0
    }

    eval_result = policy.evaluate(state, action, cycle_count=0.5)
    print(f"  Grid price (policy): ${eval_result['grid_price']:.3f}/kWh")
    print(f"  Tariff period      : {eval_result['tariff_period']}")
    print(f"  Total penalty      : {eval_result['total_penalty']:.4f}")
    print(f"  Rule violations    : {eval_result['rule_violations']}")
    print(f"  Carbon kg          : {eval_result['policy_costs']['carbon_kg']:.4f}")


# ============================================================
# 5. EXPLAINABILITY TEST
# ============================================================

def test_explainability():
    section("LAYER 5 — EXPLAINABILITY")

    from core.explain.explain_core import ExplainCore
    from core.twin.twin_core       import DigitalTwin
    from core.optimizer.solver     import Solver

    twin    = DigitalTwin(pv_area_m2=500.0, battery_capacity_kwh=100.0)
    solver  = Solver()
    explain = ExplainCore()

    subsection("Single Decision Explanation")
    for hour in [10.0, 18.5, 22.0]:
        state  = twin.twin_step(hour_of_day=hour, day_type="weekday")
        result = solver.optimize(state)
        best   = result["best_action"]

        if best:
            cost_breakdown = best.get("cost_breakdown", {})
            explanation    = explain.explain(state, best, cost_breakdown)

            print(f"\n  Hour {hour}:")
            print(f"  Action      : {explanation['action_name']}")
            print(f"  Decision    : {explanation['decision']}")
            print(f"  Reason      : {explanation['reason'][:80]}...")
            print(f"  Top factor  : {explanation['top_factor']}")
            print(f"  Cost summary: {explanation['cost_summary']}")

    subsection("Action Frequency")
    freq = explain.get_action_frequency()
    print(f"  Action frequencies: {freq}")

    subsection("Schedule Summary")
    twin.reset(0.50)
    state    = twin.twin_step(hour_of_day=0.0)
    schedule = solver.optimize_horizon(state)
    summary  = explain.get_schedule_summary_text(schedule)
    print(summary)


# ============================================================
# 6. RL AGENT TEST
# ============================================================

def test_rl_agent():
    section("LAYER 4 — RL AGENT (Rule-Based Fallback)")

    from core.learning.rl_agent import RLAgent
    from core.learning.rl_env   import MicrogridEnv
    from core.twin.twin_core    import DigitalTwin
    from core.optimizer.solver  import Solver
    from core.learning.reward   import RewardFunction

    twin      = DigitalTwin(battery_capacity_kwh=100.0, pv_area_m2=500.0)
    solver    = Solver()
    reward_fn = RewardFunction()
    env       = MicrogridEnv(twin=twin, solver=solver, reward_fn=reward_fn, n_steps=8)
    agent     = RLAgent(env=env)

    subsection("Rule-Based Action Prediction")
    obs, _ = env.reset()
    total_reward = 0.0

    for step in range(8):
        action      = agent.predict_action(env.current_state)
        adjustments = agent.get_weight_adjustments(env.current_state)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

        print(f"  Step {step}: "
              f"SOC={env.current_state.soc:.2%} | "
              f"Action={info['action_name']:20s} | "
              f"Reward={reward:.4f} | "
              f"Source={adjustments['source']}")

        if terminated or truncated:
            break

    print(f"\n  Total reward (8 steps): {total_reward:.4f}")
    print(f"  Episode cost          : ${info['episode_cost']:.4f}")


# ============================================================
# 7. FULL PIPELINE — 24 HOUR SIMULATION
# ============================================================

def test_full_pipeline():
    section("FULL PIPELINE — 24 HOUR SIMULATION")

    from core.twin.twin_core        import DigitalTwin
    from core.optimizer.solver      import Solver
    from core.explain.explain_core  import ExplainCore
    from core.policy.policy_manager import PolicyManager

    twin = DigitalTwin(
        battery_capacity_kwh = 100.0,
        pv_area_m2           = 500.0,
        base_load_kw         = 200.0,
        peak_load_kw         = 800.0,
        initial_soc          = 0.50,
        mode                 = "simulation"
    )
    solver  = Solver()
    explain = ExplainCore()
    policy  = PolicyManager()

    dt_hours     = 0.25
    n_steps      = 96       # 24 hours × 4 steps/hour
    results      = []
    total_cost   = 0.0
    total_solar  = 0.0
    total_import = 0.0
    total_export = 0.0

    print("\n  Running 96-step simulation...")
    print(f"  {'Step':>4} | {'Hour':>5} | {'SOC':>6} | "
          f"{'PV kW':>7} | {'Load kW':>8} | {'Action':>22} | {'Cost':>8}")
    print("  " + "-" * 80)

    for t in range(n_steps):
        hour = t * dt_hours

        # 1. Get twin state
        state = twin.twin_step(
            hour_of_day  = hour,
            day_type     = "weekday",
            cloud_factor = 0.85
        )

        # 2. Optimize
        opt_result  = solver.optimize(state)
        best_action = opt_result.get("best_action", {})

        # 3. Policy check
        policy_result = policy.evaluate(
            state       = state,
            action      = best_action,
            cycle_count = state.cycle_count
        )
        final_action = policy_result["final_action"]

        # 4. Explain
        cost_bd = best_action.get("cost_breakdown", {})
        exp     = explain.explain(state, best_action, cost_bd)

        # 5. Accumulate metrics
        step_cost     = cost_bd.get("total_cost", 0.0)
        total_cost   += step_cost
        total_solar  += state.pv_power_kw * dt_hours
        total_import += final_action.get("grid_import_kw", 0.0) * dt_hours
        total_export += final_action.get("grid_export_kw", 0.0) * dt_hours

        # Print every 8th step (every 2 hours)
        if t % 8 == 0:
            print(
                f"  {t:>4} | "
                f"{hour:>5.2f} | "
                f"{state.soc:>5.1%} | "
                f"{state.pv_power_kw:>7.1f} | "
                f"{state.load_kw:>8.1f} | "
                f"{best_action.get('action_name',''):>22} | "
                f"${step_cost:>7.5f}"
            )

        results.append({
            "step"       : t,
            "hour"       : hour,
            "soc"        : state.soc,
            "pv_kw"      : state.pv_power_kw,
            "load_kw"    : state.load_kw,
            "action"     : best_action.get("action_name", ""),
            "cost"       : step_cost,
            "explanation": exp["full_explanation"]
        })

    # Final summary
    print("\n" + "=" * 60)
    print("  DAILY SUMMARY")
    print("=" * 60)
    print(f"  Total cost       : ${total_cost:.4f}")
    print(f"  Total solar used : {total_solar:.2f} kWh")
    print(f"  Total grid import: {total_import:.2f} kWh")
    print(f"  Total grid export: {total_export:.2f} kWh")
    if (total_solar + total_import) > 0:
        print(f"  Solar fraction   : "
              f"{total_solar / (total_solar + total_import) * 100:.1f}%")
    else:
        print("  Solar fraction   : N/A")
    print(f"  Final SOC        : {results[-1]['soc']:.1%}")

    carbon_summary = policy.get_carbon_summary()
    print(f"  Total CO2        : {carbon_summary['total_carbon_kg']:.2f} kg")
    print(f"  CO2 avoided      : {carbon_summary['total_avoided_kg']:.2f} kg")

    freq = explain.get_action_frequency()
    print(f"\n  Action distribution:")
    for action_name, count in freq.items():
        pct = count / n_steps * 100
        print(f"    {action_name:30s}: {count:3d} ({pct:.1f}%)")

    return results


# ============================================================
# MAIN — TEST SUITE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("\n" + "🔋" * 30)
    print("  INTELLIGENT MICROGRID EMS — CORE TEST SUITE")
    print("🔋" * 30)

    try:
        test_models()
    except Exception as e:
        print(f"  [ERROR] Models: {e}")

    try:
        test_digital_twin()
    except Exception as e:
        print(f"  [ERROR] Twin: {e}")

    try:
        test_optimizer()
    except Exception as e:
        print(f"  [ERROR] Optimizer: {e}")

    try:
        test_policy()
    except Exception as e:
        print(f"  [ERROR] Policy: {e}")

    try:
        test_explainability()
    except Exception as e:
        print(f"  [ERROR] Explainability: {e}")

    try:
        test_rl_agent()
    except Exception as e:
        print(f"  [ERROR] RL Agent: {e}")

    try:
        results = test_full_pipeline()
        print(f"\n  Pipeline complete: {len(results)} steps simulated.")
    except Exception as e:
        print(f"  [ERROR] Full Pipeline: {e}")

    print("\n" + "✅" * 30)
    print("  ALL CORE TESTS COMPLETE")
    print("✅" * 30 + "\n")