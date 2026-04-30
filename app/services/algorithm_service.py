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
    Recursively converts numpy types and replaces inf/nan floats with None.
    """
    import math

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    else:
        # Handle numpy types
        module = getattr(type(obj), "__module__", "") or ""
        if "numpy" in module and hasattr(obj, "item"):
            val = obj.item()
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
            return val
        return obj



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
    def _grid_cost_for_plan(plan: Plan, monthly_kwh: float = None) -> float:
        try:
            from app.services.tariff_service import TariffService

            region = "default"
            if plan and getattr(plan, "location", None):
                region = str(plan.location).strip() or "default"

            tariff = TariffService.get_tariff(region)

            if monthly_kwh and monthly_kwh > 0:
                bill = TariffService.calculate_bill(monthly_kwh, region)
                return float(bill.get("average_rate", 0.12))

            if tariff.get("type") == "flat":
                return float(tariff.get("flat_rate", 0.12))

            if tariff.get("type") == "tiered":
                tiers = tariff.get("tiers") or []
                rates = [float(t.get("rate", 0.12)) for t in tiers if t.get("rate") is not None]
                if rates:
                    return float(sum(rates) / len(rates))
                return 0.12

            if tariff.get("type") == "tou":
                rates = [float(r.get("rate", 0.12)) for r in tariff.get("tou_rates", []) if r.get("rate") is not None]
                if rates:
                    return float(sum(rates) / len(rates))
                return 0.12

            return 0.12
        except Exception:
            return 0.12

    @staticmethod
    def _default_system_costs(plan: Plan) -> dict:
        """Return region-aware default solar/battery installed costs."""
        from app.services.tariff_service import TariffService

        region = "default"
        if plan and getattr(plan, "location", None):
            region = str(plan.location).strip() or "default"

        tariff = TariffService.get_tariff(region)
        currency = str(tariff.get("currency", "USD")).upper()

        if currency == "INR":
            return {
                "solar_price_per_kw": 45000.0,
                "battery_price_per_kwh": 12000.0
            }
        if currency == "MYR":
            return {
                "solar_price_per_kw": 3200.0,
                "battery_price_per_kwh": 1500.0
            }
        if currency == "AUD":
            return {
                "solar_price_per_kw": 1500.0,
                "battery_price_per_kwh": 450.0
            }
        if currency == "GBP":
            return {
                "solar_price_per_kw": 1200.0,
                "battery_price_per_kwh": 350.0
            }
        return {
            "solar_price_per_kw": 1000.0,
            "battery_price_per_kwh": 300.0
        }

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

        # Use actual bill consumption and total amount to estimate tariff
        total_units = 0.0
        total_amount = 0.0
        for record in consumption:
            if record.units is not None and record.units > 0:
                total_units += float(record.units)
            if record.totalAmount is not None and float(record.totalAmount) > 0:
                total_amount += float(record.totalAmount)

        if total_units > 0:
            if total_amount > 0:
                grid_cost = total_amount / total_units
            else:
                monthly_units = total_units / len(consumption)
                grid_cost = AlgorithmService._grid_cost_for_plan(plan, monthly_kwh=monthly_units)
        else:
            grid_cost = AlgorithmService._grid_cost_for_plan(plan)

        system_costs = AlgorithmService._default_system_costs(plan)

        return {
            "plan_id": plan_id,
            "budget": float(plan.budget),
            "roof_area_m2": float(plan.roofArea),
            "location": plan.location or "Unknown",
            "irradiance_wm2": AlgorithmService._irradiance_for_plan(plan),
            "grid_cost_per_kwh": float(grid_cost),
            "solar_price_per_kw": float(system_costs["solar_price_per_kw"]),
            "battery_price_per_kwh": float(system_costs["battery_price_per_kwh"]),
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

        def _safe_float(value, default=None):
            try:
                val = float(value)
            except Exception:
                return default
            return val if math.isfinite(val) else default

        new_result = Result(
            planId=plan_id,
            solarSize=_safe_float(result.get("solar_size_kw", 0), 0.0),
            batterySize=_safe_float(result.get("battery_size_kwh", 0), 0.0),
            roi=_safe_float(result.get("roi", None), None),
            saving=_safe_float(result.get("saving", None), None),
            totalCost=_safe_float(result.get("total_cost", None), None),
            paybackPeriod=_safe_float(result.get("payback_period", None), None),
            annualGeneration=_safe_float(annual_gen, None),
            co2Reduction=_safe_float(co2, None),
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

        # ── Sync SOC from stored schedule ─────────────────────────────
        # The stored schedule was built during planning and has the correct
        # SOC trajectory. Read the SOC for the current hour so the live
        # prediction starts from the right state instead of the reset twin.
        stored_soc = None
        res_row = db.query(Result).filter(Result.planId == plan_id).first()
        if res_row:
            from app.services.algorithm_service import AlgorithmService as _AS
            rows = _AS._hourly_rows_from_result(res_row, 24)
            for row in rows:
                try:
                    row_hour = datetime.fromisoformat(
                        row["time"].replace("Z", "")).hour
                    if row_hour == now.hour:
                        soc_pct = float(row.get("batterySOC", 50))
                        stored_soc = soc_pct / 100.0 if soc_pct > 1.0 else soc_pct
                        break
                except Exception:
                    pass

        predict_input = {
            "plan_id"    : plan_id,
            "hour_of_day": hour,
            "day_type"   : AlgorithmService._get_day_type(),
            "cloud_factor": 0.9,
            "grid_price" : float(grid_cost),
        }
        # Inject stored SOC so live twin matches the saved schedule
        if stored_soc is not None:
            predict_input["soc"] = stored_soc

        core_result = run_prediction(predict_input)
        AlgorithmService._save_prediction(plan_id, core_result, db)

        t = now.replace(minute=0, second=0, microsecond=0)
        solar_kw = float(core_result.get("pv_kw") or core_result.get("solar_kw") or 0)
        raw_action = core_result.get("action")
        return {
            "time"        : t.isoformat(),
            "solar_kW"    : solar_kw,
            "batterySOC"  : float(core_result.get("battery_soc") or 0),
            "gridImport"  : float(core_result.get("grid_import_kw") or 0),
            "gridExport"  : float(core_result.get("grid_export_kw") or 0),
            "consumption" : float(core_result.get("consumption_kw") or 0),
            "action"      : AlgorithmService._map_action_to_ui(raw_action, pv_kw=solar_kw),
            "batteryAction": (
                "charge"    if float(core_result.get("charge_kw")    or 0) > 0.05 else
                "discharge" if float(core_result.get("discharge_kw") or 0) > 0.05 else
                "idle"
            )
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
            cb = float(steps[-1].get("charge_kw", 0))
            db = float(steps[-1].get("discharge_kw", 0))
            bact = "charge" if cb > 0.05 else ("discharge" if db > 0.05 else "idle")
            cost = sum(float(s.get("cost", 0)) for s in steps)
            t = now.replace(hour=h, minute=0, second=0, microsecond=0)
            rows.append(
                {
                    "time": t.isoformat(),
                    "solar_kW": round(pv, 2),
                    "batterySOC": round(soc_pct, 1),
                    "gridImport": 0.0,
                    "gridExport": 0.0,
                    "consumption": round(ld, 2),
                    "action": act,
                    "batteryAction": bact,
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
