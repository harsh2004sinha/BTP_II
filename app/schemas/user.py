from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re

class UserRegister(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        example="John Doe"
    )
    email: EmailStr = Field(
        ...,
        example="john@example.com"
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=64,       # Keep under 72 byte bcrypt limit
        example="Pass123!"
    )

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        # Check byte length for bcrypt
        if len(v.encode('utf-8')) > 72:
            raise ValueError(
                'Password too long. Maximum 72 characters allowed.'
            )
        # At least one uppercase
        if not re.search(r'[A-Z]', v):
            raise ValueError(
                'Password must contain at least one uppercase letter'
            )
        # At least one digit
        if not re.search(r'[0-9]', v):
            raise ValueError(
                'Password must contain at least one number'
            )
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        cleaned = v.strip()
        if not cleaned.replace(' ', '').isalpha():
            raise ValueError(
                'Name must contain only letters and spaces'
            )
        return cleaned

    class Config:
        json_schema_extra = {
            "example": {
                "name":     "John Doe",
                "email":    "john@example.com",
                "password": "Pass123!"
            }
        }


class UserLogin(BaseModel):
    email: EmailStr = Field(
        ...,
        example="john@example.com"
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=64,
        example="Pass123!"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email":    "john@example.com",
                "password": "Pass123!"
            }
        }


class UserResponse(BaseModel):
    id:        str
    name:      str
    email:     str
    is_active: bool
    createdAt: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    userId:       str
    name:         str
    email:        str
    expires_in:   int