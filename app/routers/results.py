"""
app/routers/results.py
Updated to use AlgorithmService properly
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.utils.dependencies import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.models.result import Result
from app.services.algorithm_service import AlgorithmService
from app.utils.helpers import create_api_response
import json
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["Results"])


def _norm_graph_data(raw):
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


@router.post("/optimize/{plan_id}")
def optimize_plan(
    plan_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger optimization for a plan.
    Runs in background so frontend doesn't wait.
    """
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id,
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    from app.models.consumption import ConsumptionData

    has_data = (
        db.query(ConsumptionData)
        .filter(ConsumptionData.planId == plan_id)
        .first()
    )

    if not has_data:
        raise HTTPException(
            status_code=400,
            detail="No consumption data. Upload bill first.",
        )

    plan.status = "processing"
    db.commit()

    def run_bg(pid: str):
        bg_db = SessionLocal()
        try:
            logger.info(f"[Optimizer] Starting background optimization for plan {pid}")
            AlgorithmService.run_optimization(pid, bg_db)
            logger.info(f"[Optimizer] Successfully completed optimization for plan {pid}")
        except Exception as e:
            logger.error(f"[Optimizer] Failed for plan {pid}: {e}")
            logger.error(traceback.format_exc())
            # Always attempt to mark plan as failed so frontend stops polling
            try:
                bg_plan = bg_db.query(Plan).filter(Plan.planId == pid).first()
                if bg_plan:
                    bg_plan.status = "failed"
                    bg_db.commit()
                    logger.info(f"[Optimizer] Marked plan {pid} as failed")
                else:
                    logger.error(f"[Optimizer] Could not find plan {pid} to mark as failed")
            except Exception as db_err:
                logger.error(f"[Optimizer] DB error while marking plan {pid} as failed: {db_err}")
                try:
                    bg_db.rollback()
                except Exception:
                    pass
        finally:
            try:
                bg_db.close()
            except Exception:
                pass

    background_tasks.add_task(run_bg, plan_id)

    return create_api_response(
        success=True,
        message="Optimization started",
        data={"plan_id": plan_id, "status": "processing"},
    )


@router.get("/{plan_id}")
def get_result(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get optimization result for a plan (shape matches frontend)."""
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id,
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = db.query(Result).filter(Result.planId == plan_id).first()

    if not result:
        # If status is "failed", surface it clearly so frontend stops polling
        message = "Optimization in progress."
        if plan.status == "failed":
            message = "Optimization failed. Please try again."
        elif plan.status != "processing":
            message = "No result yet. Run optimization first."

        return create_api_response(
            success=True,
            message=message,
            data={
                "status": plan.status,
                "plan_id": plan_id,
            },
        )

    graph_data = _norm_graph_data(result.graphData)

    data = {
        "status": "completed",
        "plan_id": plan_id,
        "solar_size_kw": result.solarSize,
        "battery_size_kwh": result.batterySize,
        "roi_years": result.roi,
        "annual_savings": result.saving,
        "total_cost": result.totalCost,
        "payback_period": result.paybackPeriod,
        "graph_data": graph_data,
        # Frontend Result page field names
        "solarSize_kW": result.solarSize,
        "batterySize_kWh": result.batterySize,
        "annualSaving": result.saving,
        "totalCost": result.totalCost,
        "co2Reduction_kg": result.co2Reduction,
        "annualGeneration": result.annualGeneration,
        "graphData": graph_data,
        "createdAt": str(result.createdAt) if result.createdAt else None,
    }

    return create_api_response(
        success=True,
        message="Result retrieved",
        data=data,
    )


@router.post("/reset/{plan_id}")
def reset_stuck_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset a plan that is stuck in 'processing' back to 'bill_uploaded'
    so the user can re-trigger optimization.
    """
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id,
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.status not in ("processing", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Plan is not stuck. Current status: {plan.status}",
        )

    plan.status = "bill_uploaded"
    db.commit()
    logger.info(f"[Reset] Plan {plan_id} reset from '{plan.status}' to 'bill_uploaded'")

    return create_api_response(
        success=True,
        message="Plan reset. You can now re-run optimization.",
        data={"plan_id": plan_id, "status": "bill_uploaded"},
    )
