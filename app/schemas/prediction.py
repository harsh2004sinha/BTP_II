"""
app/routers/prediction.py
Updated to use core prediction
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.models.prediction import Prediction
from app.services.algorithm_service import AlgorithmService
from app.utils.helpers import create_api_response

router = APIRouter(prefix="/prediction", tags=["Prediction"])


@router.get("/{plan_id}")
def get_prediction(
    plan_id     : str,
    db          : Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Get current 15-min prediction.
    Frontend calls this every 15 seconds to update dashboard.
    """
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Plan not ready. Status: {plan.status}"
        )

    result = AlgorithmService.get_prediction(plan_id, db)

    return create_api_response(
        success = True,
        message = "Prediction retrieved",
        data    = result
    )


@router.post("/refresh/{plan_id}")
def refresh_prediction(
    plan_id     : str,
    db          : Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """Force refresh prediction with latest data."""
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    result = AlgorithmService.refresh_prediction(plan_id, db)

    return create_api_response(
        success = True,
        message = "Prediction refreshed",
        data    = result
    )