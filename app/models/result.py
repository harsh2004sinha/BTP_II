from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Result(Base):
    __tablename__ = "results"
    
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    planId = Column(
        String, 
        ForeignKey("plans.planId"), 
        nullable=False, 
        unique=True,
        index=True
    )
    solarSize = Column(Float, nullable=True)         # kW
    batterySize = Column(Float, nullable=True)       # kWh
    roi = Column(Float, nullable=True)               # Return on investment in years
    saving = Column(Float, nullable=True)            # Annual saving in currency
    totalCost = Column(Float, nullable=True)         # Total installation cost
    paybackPeriod = Column(Float, nullable=True)     # Years to payback
    annualGeneration = Column(Float, nullable=True)  # kWh per year
    co2Reduction = Column(Float, nullable=True)      # kg CO2 per year
    graphData = Column(JSON, nullable=True)          # For chart data
    rawOutput = Column(JSON, nullable=True)          # Full algorithm output
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    plan = relationship("Plan", back_populates="result")
    
    def __repr__(self):
        return f"<Result(planId={self.planId}, solarSize={self.solarSize})>"