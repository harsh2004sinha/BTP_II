from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.plan import Plan
from app.models.result import Result
from app.models.consumption import ConsumptionData
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.utils.helpers import create_api_response
from app.services.weather_service import WeatherService
from app.services.algorithm_service import AlgorithmService
from app.algorithm.optimizer import run_optimizer
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/results",
    tags=["Optimization Results"]
)


def run_optimization_task(plan_id: str, db: Session):
    """Background task to run optimization."""
    try:
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        if not plan:
            return

        # Update status
        plan.status = "processing"
        db.commit()

        # Get consumption data
        consumption_records = db.query(ConsumptionData).filter(
            ConsumptionData.planId == plan_id
        ).all()

        consumption_list = [
            {
                "month":  r.month,
                "year":   r.year,
                "units":  r.units,
                "date":   r.date
            }
            for r in consumption_records
        ]

        # Get weather and irradiance
        irradiance = WeatherService.calculate_solar_irradiance(
            lat=plan.latitude or 3.139,
            lon=plan.longitude or 101.687
        )
        weather = WeatherService.get_current_weather(
            lat=plan.latitude or 3.139,
            lon=plan.longitude or 101.687
        )

        # Prepare optimizer input
        optimizer_input = AlgorithmService.prepare_optimization_input(
            plan={
                "planId":    plan.planId,
                "budget":    plan.budget,
                "roofArea":  plan.roofArea,
                "location":  plan.location,
                "latitude":  plan.latitude,
                "longitude": plan.longitude
            },
            consumption_data=consumption_list,
            irradiance_data=irradiance,
            weather_data=weather
        )

        # Run optimizer
        result_data = run_optimizer(optimizer_input)

        # Save or update result
        existing = db.query(Result).filter(
            Result.planId == plan_id
        ).first()

        if existing:
            existing.solarSize        = result_data.get("solar_size_kw")
            existing.batterySize      = result_data.get("battery_size_kwh")
            existing.roi              = result_data.get("roi_years")
            existing.saving           = result_data.get("annual_saving")
            existing.totalCost        = result_data.get("total_cost")
            existing.paybackPeriod    = result_data.get("payback_period")
            existing.annualGeneration = result_data.get("annual_generation_kwh")
            existing.co2Reduction     = result_data.get("co2_reduction_kg")
            existing.graphData        = result_data.get("graph_data")
            existing.rawOutput        = result_data
        else:
            new_result = Result(
                planId            = plan_id,
                solarSize         = result_data.get("solar_size_kw"),
                batterySize       = result_data.get("battery_size_kwh"),
                roi               = result_data.get("roi_years"),
                saving            = result_data.get("annual_saving"),
                totalCost         = result_data.get("total_cost"),
                paybackPeriod     = result_data.get("payback_period"),
                annualGeneration  = result_data.get("annual_generation_kwh"),
                co2Reduction      = result_data.get("co2_reduction_kg"),
                graphData         = result_data.get("graph_data"),
                rawOutput         = result_data
            )
            db.add(new_result)

        plan.status = "completed"
        db.commit()
        logger.info(f"Optimization completed for plan: {plan_id}")

    except Exception as e:
        logger.error(f"Optimization task error: {e}")
        plan = db.query(Plan).filter(Plan.planId == plan_id).first()
        if plan:
            plan.status = "failed"
            db.commit()


@router.post(
    "/optimize/{plan_id}",
    summary="Run optimization for a plan"
)
def run_optimization(
    plan_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger optimization algorithm for a plan.

    Runs in background. Check status with GET /results/{plan_id}
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

    # Check consumption data exists
    consumption_count = db.query(ConsumptionData).filter(
        ConsumptionData.planId == plan_id
    ).count()

    if consumption_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No consumption data found. Please upload a bill first."
        )

    # Add background task
    background_tasks.add_task(run_optimization_task, plan_id, db)

    return create_api_response(
        success=True,
        message="Optimization started. Check results in a few seconds.",
        data={
            "planId": plan_id,
            "status": "processing"
        }
    )


@router.get(
    "/{plan_id}",
    summary="Get optimization result for a plan"
)
def get_result(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get optimization results including solar size, battery, ROI and savings."""
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    if plan.status == "processing":
        return create_api_response(
            success=True,
            message="Optimization still in progress. Please wait.",
            data={"planId": plan_id, "status": "processing"}
        )

    result = db.query(Result).filter(
        Result.planId == plan_id
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No result found. Run optimization first."
        )

    return create_api_response(
        success=True,
        message="Result fetched successfully",
        data={
            "planId":           plan_id,
            "status":           plan.status,
            "solarSize_kW":     result.solarSize,
            "batterySize_kWh":  result.batterySize,
            "roi_years":        result.roi,
            "annualSaving":     result.saving,
            "totalCost":        result.totalCost,
            "paybackPeriod":    result.paybackPeriod,
            "annualGeneration": result.annualGeneration,
            "co2Reduction_kg":  result.co2Reduction,
            "graphData":        result.graphData,
            "createdAt":        str(result.createdAt)
        }
    )