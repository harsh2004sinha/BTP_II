"""
app/routers/prediction.py
Updated to use core prediction
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.services.algorithm_service import AlgorithmService
from app.utils.helpers import create_api_response

router = APIRouter(prefix="/prediction", tags=["Prediction"])


@router.get("/{plan_id}")
def get_prediction(
    plan_id: str,
    hours: int = Query(24, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Hourly prediction series for dashboards (built from core schedule + live step).
    """
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id,
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Plan not ready. Status: {plan.status}",
        )

    try:
        payload = AlgorithmService.get_predictions_dashboard(plan_id, db, hours=hours)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {e}",
        ) from e

    return create_api_response(
        success=True,
        message="Prediction retrieved",
        data=payload,
    )


@router.post("/refresh/{plan_id}")
def refresh_prediction(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Force refresh prediction with latest data."""
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id,
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Plan not ready. Status: {plan.status}",
        )

    payload = AlgorithmService.refresh_prediction(plan_id, db)

    return create_api_response(
        success=True,
        message="Prediction refreshed",
        data=payload,
    )
