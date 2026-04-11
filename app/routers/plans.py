from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.plan import PlanCreate, PlanUpdate
from app.models.plan import Plan
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.utils.helpers import create_api_response
from app.services.weather_service import WeatherService
from app.algorithm.core_bridge import clear_pipeline
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/plans",
    tags=["Plans"]
)


@router.post("/createPlan", status_code=status.HTTP_201_CREATED)
def create_plan(
    plan_data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new energy optimization plan."""
    try:
        lat, lon = WeatherService.get_coordinates(plan_data.location)

        new_plan = Plan(
            userId    = current_user.id,
            budget    = plan_data.budget,
            roofArea  = plan_data.roofArea,
            location  = plan_data.location,
            latitude  = lat,
            longitude = lon,
            status    = "pending"
        )

        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

        return create_api_response(
            success=True,
            message="Plan created successfully",
            data={
                "planId":    new_plan.planId,
                "userId":    new_plan.userId,
                "budget":    new_plan.budget,
                "roofArea":  new_plan.roofArea,
                "location":  new_plan.location,
                "latitude":  new_plan.latitude,
                "longitude": new_plan.longitude,
                "status":    new_plan.status,
                "createdAt": str(new_plan.createdAt)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create plan: {str(e)}"
        )


@router.get("/all")
def get_all_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all plans for current user."""
    try:
        plans = db.query(Plan).filter(
            Plan.userId == current_user.id
        ).order_by(Plan.createdAt.desc()).all()

        plans_list = [
            {
                "planId":    p.planId,
                "budget":    p.budget,
                "roofArea":  p.roofArea,
                "location":  p.location,
                "latitude":  p.latitude,
                "longitude": p.longitude,
                "status":    p.status,
                "billFile":  p.billFile,
                "createdAt": str(p.createdAt)
            }
            for p in plans
        ]

        return create_api_response(
            success=True,
            message=f"Found {len(plans_list)} plan(s)",
            data={
                "plans": plans_list,
                "total": len(plans_list)
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch plans: {str(e)}"
        )


@router.get("/{plan_id}")
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific plan by ID."""
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    return create_api_response(
        success=True,
        message="Plan fetched successfully",
        data={
            "planId":    plan.planId,
            "userId":    plan.userId,
            "budget":    plan.budget,
            "roofArea":  plan.roofArea,
            "location":  plan.location,
            "latitude":  plan.latitude,
            "longitude": plan.longitude,
            "status":    plan.status,
            "billFile":  plan.billFile,
            "createdAt": str(plan.createdAt),
            "updatedAt": str(plan.updatedAt)
        }
    )


@router.put("/{plan_id}")
def update_plan(
    plan_id: str,
    plan_data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing plan."""
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
        if plan_data.budget is not None:
            plan.budget = plan_data.budget
        if plan_data.roofArea is not None:
            plan.roofArea = plan_data.roofArea
        if plan_data.location is not None:
            plan.location  = plan_data.location
            lat, lon       = WeatherService.get_coordinates(plan_data.location)
            plan.latitude  = lat
            plan.longitude = lon

        plan.status = "pending"
        db.commit()
        db.refresh(plan)

        return create_api_response(
            success=True,
            message="Plan updated successfully",
            data={
                "planId": plan.planId,
                "status": plan.status
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update plan: {str(e)}"
        )


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a plan permanently."""
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
        db.delete(plan)
        db.commit()
        clear_pipeline(plan_id)

        return create_api_response(
            success=True,
            message=f"Plan deleted successfully"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete plan: {str(e)}"
        )