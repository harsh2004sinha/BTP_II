from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class PlanCreate(BaseModel):
    budget: float = Field(..., gt=0, example=10000.0, description="Budget in currency")
    roofArea: float = Field(..., gt=0, example=50.0, description="Roof area in sq meters")
    location: str = Field(..., min_length=2, example="Kuala Lumpur")
    
    @validator('budget')
    def validate_budget(cls, v):
        if v < 100:
            raise ValueError('Budget must be at least 100')
        if v > 10000000:
            raise ValueError('Budget seems too large, please verify')
        return v
    
    @validator('roofArea')
    def validate_roof_area(cls, v):
        if v < 1:
            raise ValueError('Roof area must be at least 1 sq meter')
        if v > 10000:
            raise ValueError('Roof area seems too large, please verify')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "budget": 15000.0,
                "roofArea": 50.0,
                "location": "Kuala Lumpur"
            }
        }


class PlanResponse(BaseModel):
    planId: str
    userId: str
    budget: float
    roofArea: float
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    billFile: Optional[str] = None
    status: str
    createdAt: datetime
    
    class Config:
        from_attributes = True


class PlanUpdate(BaseModel):
    budget: Optional[float] = Field(None, gt=0)
    roofArea: Optional[float] = Field(None, gt=0)
    location: Optional[str] = Field(None, min_length=2)