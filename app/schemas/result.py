"""
app/routers/results.py
Updated to use AlgorithmService properly
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.models.result import Result
from app.services.algorithm_service import AlgorithmService
from app.utils.helpers import create_api_response
import json

router = APIRouter(prefix="/results", tags=["Results"])


@router.post("/optimize/{plan_id}")
def optimize_plan(
    plan_id         : str,
    background_tasks: BackgroundTasks,
    db              : Session = Depends(get_db),
    current_user    : User    = Depends(get_current_user)
):
    """
    Trigger optimization for a plan.
    Runs in background so frontend doesn't wait.
    """

    # Verify plan belongs to user
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check consumption data exists
    from app.models.consumption import ConsumptionData
    has_data = db.query(ConsumptionData).filter(
        ConsumptionData.planId == plan_id
    ).first()

    if not has_data:
        raise HTTPException(
            status_code=400,
            detail="No consumption data. Upload bill first."
        )

    # Update status to processing
    plan.status = "processing"
    db.commit()

    # Run in background
    def run_bg(plan_id: str):
        bg_db = next(get_db())
        try:
            AlgorithmService.run_optimization(plan_id, bg_db)
        except Exception as e:
            bg_plan = bg_db.query(Plan).filter(
                Plan.planId == plan_id).first()
            if bg_plan:
                bg_plan.status = "failed"
                bg_db.commit()
            print(f"[Optimizer] Failed: {e}")
        finally:
            bg_db.close()

    background_tasks.add_task(run_bg, plan_id)

    return create_api_response(
        success = True,
        message = "Optimization started",
        data    = {"plan_id": plan_id, "status": "processing"}
    )


@router.get("/{plan_id}")
def get_result(
    plan_id     : str,
    db          : Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """Get optimization result for a plan."""

    # Verify ownership
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = db.query(Result).filter(
        Result.planId == plan_id
    ).first()

    if not result:
        return create_api_response(
            success = False,
            message = "No result yet. Run optimization first.",
            data    = {"status": plan.status}
        )

    # Parse graph data
    graph_data = {}
    if result.graphData:
        try:
            graph_data = json.loads(result.graphData)
        except Exception:
            graph_data = {}

    return create_api_response(
        success = True,
        message = "Result retrieved",
        data    = {
            "status"          : "completed",
            "plan_id"         : plan_id,
            "solar_size_kw"   : result.solarSize,
            "battery_size_kwh": result.batterySize,
            "roi_years"       : result.roi,
            "annual_savings"  : result.saving,
            "total_cost"      : result.totalCost,
            "payback_period"  : result.paybackPeriod,
            "graph_data"      : graph_data
        }
    )