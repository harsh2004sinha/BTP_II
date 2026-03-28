from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ResultResponse(BaseModel):
    id: str
    planId: str
    solarSize: Optional[float] = None
    batterySize: Optional[float] = None
    roi: Optional[float] = None
    saving: Optional[float] = None
    totalCost: Optional[float] = None
    paybackPeriod: Optional[float] = None
    annualGeneration: Optional[float] = None
    co2Reduction: Optional[float] = None
    graphData: Optional[Dict[str, Any]] = None
    createdAt: datetime
    
    class Config:
        from_attributes = True