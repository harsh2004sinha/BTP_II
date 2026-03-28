from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.plan import Plan
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.utils.helpers import create_api_response
from app.services.weather_service import WeatherService
from app.services.tariff_service import TariffService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/weather",
    tags=["Weather & Irradiance"]
)


@router.get(
    "/irradiance/{plan_id}",
    summary="Get solar irradiance for plan location"
)
def get_irradiance(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate solar irradiance data for a plan's location.

    Returns:
    - Daily GHI (Global Horizontal Irradiance)
    - Peak sun hours
    - Hourly irradiance data
    - Sunrise and sunset times
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

    if not plan.latitude or not plan.longitude:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan has no location coordinates. Please update the plan location."
        )

    try:
        irradiance = WeatherService.calculate_solar_irradiance(
            lat=plan.latitude,
            lon=plan.longitude
        )

        return create_api_response(
            success=True,
            message="Solar irradiance calculated successfully",
            data={
                "planId":    plan_id,
                "location":  plan.location,
                "irradiance": irradiance
            }
        )

    except Exception as e:
        logger.error(f"Irradiance calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not calculate irradiance: {str(e)}"
        )


@router.get(
    "/current/{plan_id}",
    summary="Get current weather for plan location"
)
def get_current_weather(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current weather conditions at plan location."""
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
        weather = WeatherService.get_current_weather(
            lat=plan.latitude or 3.139,
            lon=plan.longitude or 101.687
        )

        return create_api_response(
            success=True,
            message="Weather data fetched",
            data={
                "planId":   plan_id,
                "location": plan.location,
                "weather":  weather
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch weather: {str(e)}"
        )


@router.get(
    "/annual/{plan_id}",
    summary="Get annual irradiance data"
)
def get_annual_irradiance(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monthly average irradiance for full year (used by optimizer)."""
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
        annual_data = WeatherService.get_annual_irradiance(
            lat=plan.latitude or 3.139,
            lon=plan.longitude or 101.687
        )

        return create_api_response(
            success=True,
            message="Annual irradiance data fetched",
            data={"planId": plan_id, "annual": annual_data}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch annual data: {str(e)}"
        )


@router.get(
    "/tariff",
    summary="Get electricity tariff rates"
)
def get_tariff(
    region: str = "default",
    current_user: User = Depends(get_current_user)
):
    """Get electricity tariff/pricing data for a region."""
    tariff      = TariffService.get_tariff(region)
    tou_schedule = TariffService.get_tou_schedule()

    return create_api_response(
        success=True,
        message="Tariff data fetched",
        data={
            "region":      region,
            "tariff":      tariff,
            "touSchedule": tou_schedule
        }
    )