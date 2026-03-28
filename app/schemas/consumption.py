from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConsumptionCreate(BaseModel):
    planId: str
    date: Optional[str] = None
    month: Optional[str] = None
    year: Optional[int] = None
    units: float = Field(..., gt=0)
    time: Optional[str] = None
    totalAmount: Optional[float] = None


class ConsumptionResponse(BaseModel):
    id: str
    planId: str
    date: Optional[str]
    month: Optional[str]
    year: Optional[int]
    units: float
    time: Optional[str]
    totalAmount: Optional[float]
    createdAt: datetime
    
    class Config:
        from_attributes = True