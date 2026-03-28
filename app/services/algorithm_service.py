"""
app/services/algorithm_service.py
===================================
Business logic layer between routers and core bridge.
Collects all data from DB, then calls core_bridge.
"""

from sqlalchemy.orm import Session
from app.models.plan import Plan
from app.models.consumption import ConsumptionData
from app.models.result import Result
from app.models.prediction import Prediction
from app.algorithm.core_bridge import (
    run_planning,
    run_prediction,
    get_pipeline_status,
    clear_pipeline
)
import json
from datetime import datetime


class AlgorithmService:

    # ============================================================
    # PLANNING
    # ============================================================

    @staticmethod
    def run_optimization(plan_id: str, db: Session) -> dict:
        """
        Collect all data for a plan, run optimization, save result.

        Called by: POST /results/optimize/{plan_id}
        """

        # 1. Get plan from database
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # 2. Get consumption data from database
        consumption = db.query(ConsumptionData).filter(
            ConsumptionData.planId == plan_id
        ).all()

        if not consumption:
            raise ValueError("No consumption data. Upload bill first.")

        # 3. Build monthly_data list from DB
        monthly_data = []
        for record in consumption:
            monthly_data.append({
                "month": record.month,
                "kwh"  : float(record.units)
            })

        # 4. Get irradiance from plan
        # (weather service saves this to plan after fetch)
        irradiance = getattr(plan, "irradiance_wm2", 500.0) or 500.0

        # 5. Get grid cost from plan or use default
        grid_cost = getattr(plan, "grid_cost_per_kwh", 0.12) or 0.12

        # 6. Build complete input for core
        plan_data = {
            "plan_id"                : plan_id,
            "budget"                 : float(plan.budget),
            "roof_area_m2"           : float(plan.roofArea),
            "location"               : plan.location or "Unknown",
            "irradiance_wm2"         : float(irradiance),
            "grid_cost_per_kwh"      : float(grid_cost),
            "solar_price_per_kw"     : float(
                getattr(plan, "solar_price_per_kw", 1000) or 1000),
            "battery_price_per_kwh"  : float(
                getattr(plan, "battery_price_per_kwh", 300) or 300),
            "battery_option"         : getattr(plan, "battery_option", "auto") or "auto",
            "solar_option"           : "yes",
            "day_type"               : "weekday",
            "monthly_data"           : monthly_data
        }

        # 7. Run core optimization
        result = run_planning(plan_data)

        # 8. Save result to database
        AlgorithmService._save_result(plan_id, result, db)

        # 9. Update plan status
        plan.status = "completed"
        db.commit()

        return result

    @staticmethod
    def _save_result(plan_id: str, result: dict, db: Session):
        """Save optimization result to database."""

        # Delete old result if exists
        db.query(Result).filter(Result.planId == plan_id).delete()

        new_result = Result(
            planId           = plan_id,
            solarSize        = result.get("solar_size_kw", 0),
            batterySize      = result.get("battery_size_kwh", 0),
            roi              = result.get("roi", 0),
            saving           = result.get("saving", 0),
            totalCost        = result.get("total_cost", 0),
            paybackPeriod    = result.get("payback_period", 0),
            graphData        = json.dumps(result.get("graph_data", {})),
            rawOutput        = json.dumps(result.get("raw_output", {}))
        )

        db.add(new_result)
        db.commit()

    # ============================================================
    # PREDICTION
    # ============================================================

    @staticmethod
    def get_prediction(plan_id: str, db: Session) -> dict:
        """
        Get current 15-min prediction for a plan.

        Called by: GET /prediction/{plan_id}
        """

        # Check pipeline exists
        status = get_pipeline_status(plan_id)
        if not status["has_plan"]:
            # Run planning first
            AlgorithmService.run_optimization(plan_id, db)

        # Get current hour
        now  = datetime.now()
        hour = now.hour + now.minute / 60.0

        # Get plan for grid price
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        grid_cost = getattr(plan, "grid_cost_per_kwh", 0.12) or 0.12

        # Build prediction input
        predict_input = {
            "plan_id"     : plan_id,
            "hour_of_day" : hour,
            "day_type"    : AlgorithmService._get_day_type(),
            "cloud_factor": 0.9,
            "grid_price"  : float(grid_cost)
        }

        # Run core prediction
        result = run_prediction(predict_input)

        # Save to database
        AlgorithmService._save_prediction(plan_id, result, db)

        return result

    @staticmethod
    def refresh_prediction(plan_id: str, db: Session) -> dict:
        """Force refresh prediction with latest data."""
        return AlgorithmService.get_prediction(plan_id, db)

    @staticmethod
    def _save_prediction(
        plan_id: str,
        result : dict,
        db     : Session
    ):
        """Save prediction to database."""
        pred = Prediction(
            planId     = plan_id,
            time       = datetime.now(),
            solar      = result.get("solar_kw", 0),
            batterySOC = result.get("battery_soc", 0),
            gridCost   = result.get("grid_cost", 0),
            gridImport = result.get("grid_import_kw", 0),
            gridExport = result.get("grid_export_kw", 0),
            consumption= result.get("consumption_kw", 0),
            action     = result.get("action", "grid_only")
        )
        db.add(pred)
        db.commit()

    @staticmethod
    def _get_day_type() -> str:
        """Get current day type."""
        day = datetime.now().weekday()
        if day == 5:   return "saturday"
        if day == 6:   return "sunday"
        return "weekday"

    # ============================================================
    # SCHEDULER FUNCTION
    # ============================================================

    @staticmethod
    def run_scheduled_update(db: Session):
        """
        Called every 15 minutes by scheduler.
        Updates predictions for all active plans.
        """
        # Get all completed plans
        from app.models.plan import Plan
        active_plans = db.query(Plan).filter(
            Plan.status == "completed"
        ).all()

        for plan in active_plans:
            try:
                AlgorithmService.refresh_prediction(
                    str(plan.planId), db)
                print(f"[Scheduler] Updated plan: {plan.planId}")
            except Exception as e:
                print(f"[Scheduler] Failed plan {plan.planId}: {e}")