from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="John Doe")
    email: EmailStr = Field(..., example="john@example.com")
    password: str = Field(..., min_length=8, example="StrongPass123!")
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace(' ', '').isalpha():
            raise ValueError('Name must contain only letters and spaces')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "StrongPass123!"
            }
        }


class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="john@example.com")
    password: str = Field(..., example="StrongPass123!")


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool
    createdAt: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    userId: str
    name: str
    email: str
    expires_in: int  # minutes