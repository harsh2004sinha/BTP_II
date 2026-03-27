from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Energy Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/energy_db"
    
    # Weather APIs
    OPENWEATHER_API_KEY: str = ""
    NASA_API_KEY: str = ""
    
    # File Upload
    UPLOAD_DIR: str = "uploads/bills"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # Scheduler
    UPDATE_INTERVAL_MINUTES: int = 15
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Create upload directory if not exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)