from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
import string
import hashlib
import platform
import uuid
import json
from typing import Optional
from fastapi import HTTPException, status
from ..config.settings import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def generate_license_key(length: int = 29) -> str:
    """Generate a license key in format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"""
    alphabet = string.ascii_uppercase + string.digits
    segments = [
        ''.join(secrets.choice(alphabet) for _ in range(5))
        for _ in range(5)
    ]
    return '-'.join(segments)

def create_hardware_id() -> str:
    """Create a unique hardware identifier"""
    system_info = {
        'platform': platform.system(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'node': platform.node(),
        'mac_address': hex(uuid.getnode())
    }
    
    # Create a stable hash of system information
    hardware_id = hashlib.sha256(
        json.dumps(system_info, sort_keys=True).encode()
    ).hexdigest()
    
    return hardware_id

def validate_hardware_id(stored_id: Optional[str], current_id: str) -> bool:
    """Validate hardware ID against stored value"""
    if not stored_id:
        return True
    return stored_id == current_id

def create_validation_token(license_key: str, hardware_id: str) -> str:
    """Create a validation token for offline use"""
    validation_data = f"{license_key}:{hardware_id}:{datetime.utcnow().date()}"
    return hashlib.sha256(validation_data.encode()).hexdigest()

def verify_validation_token(token: str, license_key: str, hardware_id: str) -> bool:
    """Verify an offline validation token"""
    expected_token = create_validation_token(license_key, hardware_id)
    return secrets.compare_digest(token, expected_token)

def verify_grace_period(last_validation: datetime) -> bool:
    """Check if within grace period for offline use"""
    if not last_validation:
        return False
        
    grace_period = timedelta(days=settings.LICENSE_GRACE_PERIOD_DAYS)
    return datetime.utcnow() - last_validation <= grace_period