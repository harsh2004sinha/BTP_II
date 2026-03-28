from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PredictionResponse(BaseModel):
    id: str
    planId: str
    time: datetime
    solar: Optional[float] = None
    batterySOC: Optional[float] = None
    gridCost: Optional[float] = None
    gridImport: Optional[float] = None
    gridExport: Optional[float] = None
    consumption: Optional[float] = None
    action: Optional[str] = None
    
    class Config:
        from_attributes = True


class PredictionListResponse(BaseModel):
    planId: str
    predictions: List[PredictionResponse]
    total: int