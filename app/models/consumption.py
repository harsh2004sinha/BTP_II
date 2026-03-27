from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class ConsumptionData(Base):
    __tablename__ = "consumption_data"
    
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    planId = Column(String, ForeignKey("plans.planId"), nullable=False, index=True)
    date = Column(String(50), nullable=True)        # e.g., "2024-01"
    month = Column(String(20), nullable=True)        # e.g., "January"
    year = Column(Integer, nullable=True)
    units = Column(Float, nullable=False)            # kWh consumed
    time = Column(String(50), nullable=True)         # time period
    totalAmount = Column(Float, nullable=True)       # total bill amount
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    plan = relationship("Plan", back_populates="consumption_data")
    
    def __repr__(self):
        return f"<ConsumptionData(planId={self.planId}, date={self.date}, units={self.units})>"