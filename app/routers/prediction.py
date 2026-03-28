from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models.plan import Plan
from app.models.prediction import Prediction
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.utils.helpers import create_api_response
from app.algorithm.optimizer import run_prediction
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/prediction",
    tags=["Predictions"]
)


@router.get(
    "/{plan_id}",
    summary="Get hourly prediction for a plan"
)
def get_prediction(
    plan_id: str,
    hours: Optional[int] = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get hourly energy predictions.

    Returns per-hour:
    - Solar generation (kW)
    - Battery state of charge (%)
    - Grid import/export (kW)
    - Recommended action
    """
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    # Get latest predictions from DB
    predictions = db.query(Prediction).filter(
        Prediction.planId == plan_id
    ).order_by(Prediction.time.asc()).limit(hours).all()

    # If no predictions exist, generate them
    if not predictions:
        try:
            predictions = _generate_predictions(plan_id, plan, db)
        except Exception as e:
            logger.error(f"Prediction generation error: {e}")
            # Return estimated data
            predictions = []

    pred_list = []
    for p in predictions:
        pred_list.append({
            "time":       str(p.time),
            "solar_kW":   p.solar,
            "batterySOC": p.batterySOC,
            "gridCost":   p.gridCost,
            "gridImport": p.gridImport,
            "gridExport": p.gridExport,
            "consumption":p.consumption,
            "action":     p.action
        })

    return create_api_response(
        success=True,
        message=f"Prediction data for {len(pred_list)} hours",
        data={
            "planId":      plan_id,
            "predictions": pred_list,
            "total_hours": len(pred_list),
            "generated":   str(datetime.utcnow())
        }
    )


@router.post(
    "/refresh/{plan_id}",
    summary="Refresh predictions with latest data"
)
def refresh_prediction(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Force refresh predictions using latest weather data."""
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    try:
        predictions = _generate_predictions(plan_id, plan, db)

        return create_api_response(
            success=True,
            message=f"Predictions refreshed: {len(predictions)} hours",
            data={
                "planId":     plan_id,
                "totalHours": len(predictions),
                "refreshedAt": str(datetime.utcnow())
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not refresh predictions: {str(e)}"
        )


def _generate_predictions(plan_id: str, plan, db: Session):
    """Generate and store hourly predictions."""
    from app.services.weather_service import WeatherService
    from app.services.tariff_service import TariffService

    irradiance = WeatherService.calculate_solar_irradiance(
        lat=plan.latitude or 3.139,
        lon=plan.longitude or 101.687
    )

    tou = TariffService.get_tou_schedule()

    prediction_input = {
        "plan_id":   plan_id,
        "irradiance": irradiance,
        "tou":        tou,
        "hours":      24
    }

    hourly_data = run_prediction(prediction_input)

    # Delete old predictions
    db.query(Prediction).filter(
        Prediction.planId == plan_id
    ).delete()

    saved = []
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    for i, hour_data in enumerate(hourly_data):
        pred = Prediction(
            planId      = plan_id,
            time        = now + timedelta(hours=i),
            solar       = hour_data.get("solar_kw", 0),
            batterySOC  = hour_data.get("battery_soc", 50),
            gridCost    = hour_data.get("grid_cost", 0),
            gridImport  = hour_data.get("grid_import", 0),
            gridExport  = hour_data.get("grid_export", 0),
            consumption = hour_data.get("consumption", 0),
            action      = hour_data.get("action", "idle")
        )
        db.add(pred)
        saved.append(pred)

    db.commit()
    return saved