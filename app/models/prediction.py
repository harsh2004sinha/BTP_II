from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    planId = Column(String, ForeignKey("plans.planId"), nullable=False, index=True)
    time = Column(DateTime(timezone=True), nullable=False)
    solar = Column(Float, nullable=True)             # Solar generation kW
    batterySOC = Column(Float, nullable=True)        # Battery state of charge %
    gridCost = Column(Float, nullable=True)          # Grid cost at this time
    gridImport = Column(Float, nullable=True)        # Power from grid kW
    gridExport = Column(Float, nullable=True)        # Power to grid kW
    consumption = Column(Float, nullable=True)       # Load consumption kW
    action = Column(String(50), nullable=True)       # charge/discharge/idle
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    plan = relationship("Plan", back_populates="predictions")
    
    def __repr__(self):
        return f"<Prediction(planId={self.planId}, time={self.time})>"