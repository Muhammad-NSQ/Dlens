from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LicenseBase(BaseModel):
    tier: str
    
class LicenseCreate(LicenseBase):
    user_id: int
    hardware_id: Optional[str] = None
    expires_at: datetime

class LicenseUpdate(LicenseBase):
    is_active: Optional[bool] = None
    hardware_id: Optional[str] = None
    expires_at: Optional[datetime] = None

class LicenseResponse(LicenseBase):
    id: int
    license_key: str
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_validated: Optional[datetime]
    
    class Config:
        from_attributes = True