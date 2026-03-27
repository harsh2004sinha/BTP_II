from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService
from app.utils.helpers import create_api_response

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    - **name**: Full name (letters only)
    - **email**: Valid email address
    - **password**: Min 8 chars, 1 uppercase, 1 number
    """
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


@router.post(
    "/login",
    summary="Login and get token"
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns JWT access token valid for 24 hours.
    Use token in Authorization header: **Bearer <token>**
    """
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


@router.get(
    "/me",
    summary="Get current user info"
)
def get_me(
    db: Session = Depends(get_db),
    current_user=Depends(__import__(
        'app.utils.dependencies',
        fromlist=['get_current_user']
    ).get_current_user)
):
    """Get currently authenticated user details."""
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