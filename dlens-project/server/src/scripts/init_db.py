"""
Enhanced database initialization script for DLens
Creates test users with different license tiers and states
"""
import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add parent directory to Python path to allow imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import SessionLocal, engine, Base
from src.models.user import User
from src.models.license import License
from src.utils.security import get_password_hash, generate_license_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test users configuration
TEST_USERS = [
    {
        "email": "free@test.com",
        "password": "testpass123",
        "full_name": "Free User",
        "tier": "free"
    },
    {
        "email": "pro@test.com",
        "password": "testpass123",
        "full_name": "Pro User",
        "tier": "pro"
    },
    {
        "email": "team@test.com",
        "password": "testpass123",
        "full_name": "Team User",
        "tier": "team"
    },
    {
        "email": "enterprise@test.com",
        "password": "testpass123",
        "full_name": "Enterprise User",
        "tier": "enterprise"
    },
    # Users with special states
    {
        "email": "expired@test.com",
        "password": "testpass123",
        "full_name": "Expired License User",
        "tier": "pro",
        "license_expired": True
    },
    {
        "email": "grace@test.com",
        "password": "testpass123",
        "full_name": "Grace Period User",
        "tier": "team",
        "in_grace_period": True
    }
]

def create_test_user(db: Session, user_data: dict) -> User:
    """Create a test user with specified configuration"""
    # Create user
    user = User(
        email=user_data["email"],
        hashed_password=get_password_hash(user_data["password"]),
        full_name=user_data["full_name"],
        subscription_tier=user_data["tier"],
        is_active=True
    )
    db.add(user)
    db.flush()  # Flush to get user ID

    # Create license if not free tier
    if user_data["tier"] != "free":
        now = datetime.utcnow()
        
        # Calculate expiration based on state
        if user_data.get("license_expired"):
            expires_at = now - timedelta(days=1)
        elif user_data.get("in_grace_period"):
            expires_at = now + timedelta(days=3)  # 3 days until expiration
        else:
            expires_at = now + timedelta(days=365)  # 1 year license

        license = License(
            user_id=user.id,
            license_key=generate_license_key(),
            tier=user_data["tier"],
            is_active=True,
            created_at=now,
            expires_at=expires_at,
            last_validated=now - timedelta(days=3)  # Last validated 3 days ago
        )
        db.add(license)

    return user

def init_db(db: Session) -> None:
    """Initialize database with test data"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create test users
        created_users = []
        for user_data in TEST_USERS:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                logger.info(f"User {user_data['email']} already exists")
                continue

            user = create_test_user(db, user_data)
            created_users.append(user)
            logger.info(f"Created user: {user.email} with tier: {user.subscription_tier}")

        db.commit()
        logger.info(f"Successfully created {len(created_users)} test users")

        # Print test user credentials
        logger.info("\nTest Users Created:")
        logger.info("-" * 50)
        for user_data in TEST_USERS:
            logger.info(f"""
Email: {user_data['email']}
Password: {user_data['password']}
Tier: {user_data['tier']}
{"(Expired)" if user_data.get('license_expired') else ""}
{"(Grace Period)" if user_data.get('in_grace_period') else ""}
""")
        logger.info("-" * 50)

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def cleanup_test_data(db: Session) -> None:
    """Remove all test users and their licenses"""
    try:
        # Get emails of all test users
        test_emails = [user["email"] for user in TEST_USERS]
        
        # Delete licenses first
        test_users = db.query(User).filter(User.email.in_(test_emails)).all()
        user_ids = [user.id for user in test_users]
        
        deleted_licenses = db.query(License).filter(License.user_id.in_(user_ids)).delete()
        deleted_users = db.query(User).filter(User.email.in_(test_emails)).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_users} test users and {deleted_licenses} licenses")
        
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")
        raise
    
def check_password_hash():
    """Check a test user's password hash"""
    db = SessionLocal()
    try:
        # Get the test user
        user = db.query(User).filter(User.email == "free@test.com").first()
        if user:
            print("\nPassword Hash Check:")
            print(f"Email: {user.email}")
            print(f"Stored Hash: {user.hashed_password}")
            
            # Try verifying the password
            from src.utils.security import verify_password
            test_pass = "testpass123"
            is_valid = verify_password(test_pass, user.hashed_password)
            print(f"\nPassword verification test:")
            print(f"Test password: {test_pass}")
            print(f"Verification result: {is_valid}")
            
            # Create a new hash for comparison
            from src.utils.security import get_password_hash
            new_hash = get_password_hash(test_pass)
            print(f"\nNew hash generated: {new_hash}")
            
        else:
            print("Test user not found!")
            
    finally:
        db.close()

def main():
    """Main function to run database initialization"""
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize DLens test database')
    parser.add_argument('--clean', action='store_true', help='Clean up test data instead of creating it')
    parser.add_argument('--check-hash', action='store_true', help='Check password hash')
    
    args = parser.parse_args()
    
    if args.check_hash:
        check_password_hash()
    elif args.clean:
        cleanup_test_data(SessionLocal())
    else:
        init_db(SessionLocal())