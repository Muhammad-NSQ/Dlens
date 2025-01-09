from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from ...database import get_db
from ...models.user import User
from ...models.license import License
from ...schemas.license import LicenseCreate, LicenseResponse, LicenseUpdate
from ...utils.security import generate_license_key, create_hardware_id
from ..deps import get_current_user
from ...config.settings import settings

router = APIRouter()

@router.post("/generate", response_model=LicenseResponse)
async def generate_license(
    license_in: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a new license for a user"""
    # Check if user already has an active license
    existing_license = db.query(License).filter(
        License.user_id == license_in.user_id,
        License.is_active == True
    ).first()
    
    if existing_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active license"
        )
    
    # Create new license
    license_key = generate_license_key()
    new_license = License(
        user_id=license_in.user_id,
        license_key=license_key,
        tier=license_in.tier,
        hardware_id=license_in.hardware_id,
        expires_at=license_in.expires_at
    )
    
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    
    return new_license

@router.post("/validate", response_model=LicenseResponse)
async def validate_license(
    license_key: str = Query(...),
    hardware_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get license with user check
    license = db.query(License).filter(
        License.license_key == license_key,
        License.user_id == current_user.id,  # Add this check
        License.is_active == True
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or inactive license key"
        )
    
    # Validate expiration
    if license.expires_at and license.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License has expired"
        )
    
    # Handle hardware binding with grace period
    if hardware_id:
        if not license.hardware_id:
            license.hardware_id = hardware_id
        elif license.hardware_id != hardware_id:
            # Check if within hardware change grace period
            if (datetime.utcnow() - license.last_validated).days <= settings.LICENSE_GRACE_PERIOD_DAYS:
                license.hardware_id = hardware_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="License is bound to different hardware"
                )
    
    license.last_validated = datetime.utcnow()
    db.commit()
    db.refresh(license)
    
    return license
@router.get("/status", response_model=LicenseResponse)
async def get_license_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's license status"""
    license = db.query(License).filter(
        License.user_id == current_user.id,
        License.is_active == True
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active license found"
        )
    
    return license