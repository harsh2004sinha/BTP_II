from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserRegister, UserLogin
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user
from app.utils.helpers import create_api_response
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    try:
        user = AuthService.register_user(db, user_data)
        return create_api_response(
            success=True,
            message="User registered successfully",
            data={
                "userId": user.id,
                "name":   user.name,
                "email":  user.email
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login")
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login and get JWT token."""
    try:
        result = AuthService.login_user(db, login_data)
        return create_api_response(
            success=True,
            message="Login successful",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user details."""
    return create_api_response(
        success=True,
        message="User details fetched",
        data={
            "userId":    current_user.id,
            "name":      current_user.name,
            "email":     current_user.email,
            "is_active": current_user.is_active,
            "createdAt": str(current_user.createdAt)
        }
    )