from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin
from app.utils.security import hash_password, verify_password, create_access_token
from app.config import settings


class AuthService:
    
    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> User:
        """
        Register a new user.
        
        Raises:
            HTTPException 400 if email already exists
        """
        # Check if email already registered
        existing_user = db.query(User).filter(
            User.email == user_data.email
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' is already registered"
            )
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create new user
        new_user = User(
            name=user_data.name,
            email=user_data.email.lower(),
            password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> dict:
        """
        Authenticate user and return JWT token.
        
        Raises:
            HTTPException 401 if credentials invalid
        """
        # Find user by email
        user = db.query(User).filter(
            User.email == login_data.email.lower()
        ).first()
        
        # Validate credentials
        if not user or not verify_password(login_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support."
            )
        
        # Create access token
        token_data = {
            "sub": user.id,
            "email": user.email,
            "name": user.name
        }
        
        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "userId": user.id,
            "name": user.name,
            "email": user.email,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        }