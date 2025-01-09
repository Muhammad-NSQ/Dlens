import os
from typing import List
from pydantic_settings import BaseSettings
from datetime import timedelta
from pathlib import Path
SRC_DIR = Path(__file__).parent.parent.absolute()


class Settings(BaseSettings):
    # Basic API settings
    PROJECT_NAME: str = "DLens API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development-key-change-this-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Password policy
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_STRONG_PASSWORD: bool = True
    MAX_LOGIN_ATTEMPTS: int = 5
    PASSWORD_RESET_TIMEOUT: int = 30  # minutes
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    DISABLE_RATE_LIMIT: bool = False
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{SRC_DIR}/dlens.db"
    )
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    
    # License settings
    LICENSE_GRACE_PERIOD_DAYS: int = 7
    MAX_HARDWARE_IDS: int = 2
    TRIAL_PERIOD_DAYS: int = 14
    HARDWARE_CHANGE_LIMIT: int = 3
    OFFLINE_GRACE_PERIOD_DAYS: int = 7
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]  # Change in production
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]
    
    # Documentation
    ENABLE_DOCS: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "dlens.log"
    
    # Email settings (for future use)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    
    # Cache settings (for future use)
    CACHE_URL: str = os.getenv("CACHE_URL", "memory://")
    CACHE_TIMEOUT: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @property
    def ACCESS_TOKEN_EXPIRE_DELTA(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    @property
    def DATABASE_SETTINGS(self) -> dict:
        return {
            "pool_size": self.POOL_SIZE,
            "max_overflow": self.MAX_OVERFLOW,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }

# Create settings instance
settings = Settings()

# Validate critical settings
if settings.ENVIRONMENT == "production":
    assert not settings.SECRET_KEY.startswith("development-"), \
        "Production environment must use a secure SECRET_KEY"
    assert settings.ALLOWED_ORIGINS != ["*"], \
        "Production environment must specify explicit CORS origins"