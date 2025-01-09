from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ...database import get_db
from ...models.user import User
from ...schemas.user import UserCreate, UserResponse
from ...schemas.token import TokenSchema
from ...utils.security import verify_password, get_password_hash
from ..deps import create_access_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    logger.info(f"Login attempt for user: {form_data.username}")
    
    # Find user
    user = db.query(User).filter(User.email == form_data.username).first()
    logger.info(f"User found: {user is not None}")
    
    if not user:
        logger.warning(f"No user found with email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    is_password_valid = verify_password(form_data.password, user.hashed_password)
    logger.info(f"Password verification result: {is_password_valid}")
    
    if not is_password_valid:
        logger.warning(f"Invalid password for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"Login successful for user: {form_data.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for email: {user_in.email}")
    
    # Check if user exists
    if db.query(User).filter(User.email == user_in.email).first():
        logger.warning(f"Email already registered: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        subscription_tier='free'  # Default tier
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User registered successfully: {user_in.email}")
    return user