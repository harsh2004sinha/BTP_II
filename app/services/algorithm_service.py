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
    clear_pipeline,
)
import json
import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _sanitize_for_json(obj):
    """
    Sanitize a dict/list for PostgreSQL JSON storage.
    Uses a round-trip through json.dumps/loads with a custom encoder
    that handles numpy scalars, Python booleans, and inf/nan values.
    """
    import json
    import math

    class _Encoder(json.JSONEncoder):
        def default(self, o):
            # numpy scalar types
            type_name = type(o).__name__
            module = getattr(type(o), "__module__", "") or ""
            if "numpy" in module:
                if hasattr(o, "item"):       # covers float64, int64, bool_, etc.
                    val = o.item()
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        return None
                    return val
            if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
                return None
            return super().default(o)

    try:
        json_str = json.dumps(obj, cls=_Encoder)
        return json.loads(json_str)
    except Exception:
        # last resort: convert to string representation
        return {}



class AlgorithmService:

    # ============================================================
    # PLAN INPUTS (shared by optimize + warm pipeline)
    # ============================================================

    @staticmethod
    def _as_dict(val):
        if val is None:
            return {}
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return {}

    @staticmethod
    def _irradiance_for_plan(plan: Plan) -> float:
        try:
            from app.services.weather_service import WeatherService

            lat, lon = plan.latitude, plan.longitude
            if lat is None or lon is None:
                lat, lon = WeatherService.get_coordinates(plan.location or "")
            wx = WeatherService.calculate_solar_irradiance(float(lat), float(lon))
            mx = float(wx.get("max_ghi") or 500.0)
            return min(920.0, max(380.0, mx * 0.62))
        except Exception:
            return 500.0

    @staticmethod
    def _grid_cost_for_plan(plan: Plan) -> float:
        try:
            from app.services.tariff_service import TariffService

            r = TariffService.get_tariff("default")
            if r.get("type") == "flat":
                return float(r.get("flat_rate", 0.12))
            tiers = r.get("tiers") or []
            if tiers:
                mid = tiers[len(tiers) // 2]
                return float(mid.get("rate", 0.12))
            return 0.12
        except Exception:
            return 0.12

    @staticmethod
    def _collect_plan_inputs(plan_id: str, db: Session) -> dict:
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        consumption = (
            db.query(ConsumptionData).filter(ConsumptionData.planId == plan_id).all()
        )
        if not consumption:
            raise ValueError("No consumption data. Upload bill first.")

        monthly_data = [
            {"month": record.month, "kwh": float(record.units)} for record in consumption
        ]

        return {
            "plan_id": plan_id,
            "budget": float(plan.budget),
            "roof_area_m2": float(plan.roofArea),
            "location": plan.location or "Unknown",
            "irradiance_wm2": AlgorithmService._irradiance_for_plan(plan),
            "grid_cost_per_kwh": AlgorithmService._grid_cost_for_plan(plan),
            "solar_price_per_kw": 1000.0,
            "battery_price_per_kwh": 300.0,
            "battery_option": "auto",
            "solar_option": "yes",
            "day_type": "weekday",
            "monthly_data": monthly_data,
        }

    @staticmethod
    def warm_pipeline(plan_id: str, db: Session) -> None:
        """Re-create in-memory core pipeline after restart (no DB write)."""
        if get_pipeline_status(plan_id)["has_plan"]:
            return
        plan_data = AlgorithmService._collect_plan_inputs(plan_id, db)
        run_planning(plan_data)

    # ============================================================
    # PLANNING
    # ============================================================

    @staticmethod
    def run_optimization(plan_id: str, db: Session) -> dict:
        """
        Collect all data for a plan, run optimization, save result.

        Called by: POST /results/optimize/{plan_id}
        """
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        try:
            plan_data = AlgorithmService._collect_plan_inputs(plan_id, db)
            logger.info(f"[AlgorithmService] Running core planning for plan {plan_id}")
            result = run_planning(plan_data)
            logger.info(f"[AlgorithmService] Core planning done for plan {plan_id}, saving result")
            AlgorithmService._save_result(plan_id, result, db)

            plan.status = "completed"
            db.commit()
            logger.info(f"[AlgorithmService] Plan {plan_id} marked as completed")
            return result

        except Exception as e:
            logger.error(f"[AlgorithmService] Optimization error for plan {plan_id}: {e}")
            # Mark plan as failed so frontend stops polling
            try:
                plan.status = "failed"
                db.commit()
            except Exception as commit_err:
                logger.error(f"[AlgorithmService] Could not commit failed status: {commit_err}")
                db.rollback()
            raise  # Re-raise so the background task handler also sees the error

    @staticmethod
    def _save_result(plan_id: str, result: dict, db: Session):
        """Save optimization result to database."""
        db.query(Result).filter(Result.planId == plan_id).delete()

        raw = result.get("raw_output") or {}
        solar_kw = float(result.get("solar_size_kw", 0) or 0)
        annual_gen = solar_kw * 4.5 * 365.0
        if isinstance(raw, dict):
            sd = raw.get("solar_details") or {}
            if isinstance(sd, dict) and sd.get("daily_energy_kwh"):
                annual_gen = float(sd["daily_energy_kwh"]) * 365.0
        co2 = annual_gen * 0.42

        graph_payload = result.get("graph_data") or {}
        if not isinstance(graph_payload, dict):
            graph_payload = {}

        # Sanitize JSON payloads — convert numpy types, bools, inf/nan to plain Python
        raw_sanitized   = _sanitize_for_json(raw if isinstance(raw, dict) else AlgorithmService._as_dict(raw))
        graph_sanitized = _sanitize_for_json(graph_payload)

        new_result = Result(
            planId=plan_id,
            solarSize=float(result.get("solar_size_kw", 0) or 0),
            batterySize=float(result.get("battery_size_kwh", 0) or 0),
            roi=float(result.get("roi", 0) or 0),
            saving=float(result.get("saving", 0) or 0),
            totalCost=float(result.get("total_cost", 0) or 0),
            paybackPeriod=float(result.get("payback_period", 0) or 0),
            annualGeneration=float(annual_gen),
            co2Reduction=float(co2),
            graphData=graph_sanitized,
            rawOutput=raw_sanitized,
        )

        db.add(new_result)
        db.commit()

    # ============================================================
    # PREDICTION — core ↔ frontend shape
    # ============================================================

    @staticmethod
    def _map_action_to_ui(name: str, pv_kw: float = None) -> str:
        """
        Maps internal solver action names to frontend UI action keys.
        Optional pv_kw overrides action when there is no meaningful solar.
        """
        _PV_MIN = 0.05  # kW — below this solar is considered zero

        n = (name or "").lower()

        # If pv is explicitly provided and negligible, solar-based actions
        # become grid or battery actions regardless of the stored action name
        if pv_kw is not None and pv_kw < _PV_MIN:
            if "direct" in n or ("solar" in n and "charge" not in n and "export" not in n):
                return "use_grid"

        if "export" in n or "sell" in n:
            return "sell_power"
        if "solar_charge" in n:
            return "charge_battery"
        if "grid_charge" in n:
            return "charge_battery"
        if "discharge" in n or "shav" in n or "peak" in n:
            return "use_battery"          # was wrongly "use_solar" — fixed!
        if "direct" in n or ("solar" in n and "charge" not in n):
            return "use_solar"
        if "grid_only" in n or "grid" in n:
            return "use_grid"
        return "idle"

    @staticmethod
    def _run_live_prediction(plan_id: str, db: Session) -> dict:
        now = datetime.now()
        hour = now.hour + now.minute / 60.0
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        grid_cost = (
            AlgorithmService._grid_cost_for_plan(plan)
            if plan
            else 0.12
        )

        predict_input = {
            "plan_id": plan_id,
            "hour_of_day": hour,
            "day_type": AlgorithmService._get_day_type(),
            "cloud_factor": 0.9,
            "grid_price": float(grid_cost),
        }
        core_result = run_prediction(predict_input)
        AlgorithmService._save_prediction(plan_id, core_result, db)

        t = now.replace(minute=0, second=0, microsecond=0)
        solar_kw = float(core_result.get("pv_kw") or core_result.get("solar_kw") or 0)
        raw_action = core_result.get("action")
        return {
            "time": t.isoformat(),
            "solar_kW": solar_kw,
            "batterySOC": float(core_result.get("battery_soc") or 0),
            "gridCost": float(core_result.get("grid_cost") or 0),
            "gridImport": float(core_result.get("grid_import_kw") or 0),
            "gridExport": float(core_result.get("grid_export_kw") or 0),
            "consumption": float(core_result.get("consumption_kw") or 0),
            # Pass solar_kw so mapper can override solar actions when PV=0
            "action": AlgorithmService._map_action_to_ui(raw_action, pv_kw=solar_kw),
        }

    @staticmethod
    def _hourly_rows_from_result(result: Result, hours: int) -> list:
        if not result:
            return []
        gd = AlgorithmService._as_dict(result.graphData)
        raw = AlgorithmService._as_dict(result.rawOutput)
        sample = gd.get("sample_schedule") or raw.get("sample_24h_schedule") or []
        if not sample:
            return []

        now = datetime.now()
        rows = []
        cap = min(int(hours), 24)
        for h in range(cap):
            steps = [
                s
                for s in sample
                if int(float(s.get("hour", -1))) % 24 == h
            ]
            if not steps:
                steps = [
                    s
                    for s in sample
                    if h <= float(s.get("hour", -1)) < h + 1
                ]
            if not steps:
                continue

            pv = sum(float(s.get("pv_kw", 0)) for s in steps) / len(steps)
            ld = sum(float(s.get("load_kw", 0)) for s in steps) / len(steps)
            soc = float(steps[-1].get("soc", 0.5))
            soc_pct = soc * 100.0 if soc <= 1.01 else soc
            # Pass pv to mapper so it can override solar labels when PV is 0
            act = AlgorithmService._map_action_to_ui(steps[-1].get("action"), pv_kw=pv)
            cost = sum(float(s.get("cost", 0)) for s in steps)
            t = now.replace(hour=h, minute=0, second=0, microsecond=0)
            rows.append(
                {
                    "time": t.isoformat(),
                    "solar_kW": round(pv, 2),
                    "batterySOC": round(soc_pct, 1),
                    "gridCost": round(cost, 5),
                    "gridImport": 0.0,
                    "gridExport": 0.0,
                    "consumption": round(ld, 2),
                    "action": act,
                }
            )
        return rows

    @staticmethod
    def get_predictions_dashboard(
        plan_id: str, db: Session, hours: int = 24
    ) -> dict:
        """Bundle used by GET /prediction — matches frontend `predictions` array."""
        AlgorithmService.warm_pipeline(plan_id, db)

        res_row = db.query(Result).filter(Result.planId == plan_id).first()
        predictions = AlgorithmService._hourly_rows_from_result(res_row, hours)
        live = AlgorithmService._run_live_prediction(plan_id, db)

        if not predictions:
            now = datetime.now()
            for h in range(min(24, int(hours))):
                t = now.replace(hour=h, minute=0, second=0, microsecond=0)
                predictions.append({**live, "time": t.isoformat()})

        chour = datetime.now().hour

        def _hour_from_iso(pt: str) -> int:
            try:
                return datetime.fromisoformat(pt.replace("Z", "")).hour
            except Exception:
                return -1

        merged = False
        for i, p in enumerate(predictions):
            pt = p.get("time") or ""
            if pt and _hour_from_iso(pt) == chour:
                predictions[i] = {**live, "time": pt}
                merged = True
                break
        if not merged and predictions:
            idx = min(chour, len(predictions) - 1)
            predictions[idx] = {**live, "time": predictions[idx]["time"]}

        return {"predictions": predictions, "latest": live}

    @staticmethod
    def get_prediction(plan_id: str, db: Session) -> dict:
        """Backward-compatible alias: full dashboard payload."""
        return AlgorithmService.get_predictions_dashboard(plan_id, db, hours=24)

    @staticmethod
    def refresh_prediction(plan_id: str, db: Session) -> dict:
        return AlgorithmService.get_predictions_dashboard(plan_id, db, hours=24)

    @staticmethod
    def _save_prediction(plan_id: str, result: dict, db: Session):
        pred = Prediction(
            planId=plan_id,
            time=datetime.now(),
            solar=float(result.get("solar_kw", 0) or 0),
            batterySOC=float(result.get("battery_soc", 0) or 0),
            gridCost=float(result.get("grid_cost", 0) or 0),
            gridImport=float(result.get("grid_import_kw", 0) or 0),
            gridExport=float(result.get("grid_export_kw", 0) or 0),
            consumption=float(result.get("consumption_kw", 0) or 0),
            action=str(result.get("action", "grid_only"))[:50],
        )
        db.add(pred)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _get_day_type() -> str:
        day = datetime.now().weekday()
        if day == 5:
            return "saturday"
        if day == 6:
            return "sunday"
        return "weekday"

    # ============================================================
    # SCHEDULER
    # ============================================================

    @staticmethod
    def run_scheduled_update(db: Session):
        active_plans = db.query(Plan).filter(Plan.status == "completed").all()

        for plan in active_plans:
            try:
                AlgorithmService.refresh_prediction(str(plan.planId), db)
            except Exception as e:
                print(f"[Scheduler] Failed plan {plan.planId}: {e}")
