from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Plan(Base):
    __tablename__ = "plans"
    
    planId = Column(
        String, 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    userId = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    budget = Column(Float, nullable=False)
    roofArea = Column(Float, nullable=False)       # in square meters
    location = Column(String(255), nullable=False)  # city name or coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    billFile = Column(String(500), nullable=True)   # file path
    status = Column(String(50), default="pending")  # pending, processing, completed
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user = relationship("User", back_populates="plans")
    consumption_data = relationship(
        "ConsumptionData", 
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    result = relationship(
        "Result", 
        back_populates="plan", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    predictions = relationship(
        "Prediction",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Plan(planId={self.planId}, userId={self.userId})>"