from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from ..database import Base

class License(Base):
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    license_key = Column(String, unique=True, index=True)
    tier = Column(String)  # 'pro', 'team', 'enterprise'
    is_active = Column(Boolean, default=True)
    hardware_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    last_validated = Column(DateTime(timezone=True), nullable=True)