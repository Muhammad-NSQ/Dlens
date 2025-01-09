# server/src/scripts/test_users.py
import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

# Add base directory to Python path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))
os.environ['PYTHONPATH'] = str(base_dir)

# Now use absolute imports
from database import Base, engine, SessionLocal
from models.user import User
from models.license import License
from utils.security import get_password_hash, generate_license_key, create_hardware_id
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestUserType(Enum):
    FREE = "free"
    PRO = "pro"
    EXPIRED = "expired"
    GRACE = "grace"
    HARDWARE_CHANGED = "hardware_changed"

class TestUserData:
    def __init__(self, user_type: TestUserType):
        timestamp = datetime.now().timestamp()
        self.email = f"{user_type.value}_{int(timestamp)}@test.com"
        self.password = "Test123!"  # Standard test password
        self.subscription_tier = "pro" if user_type != TestUserType.FREE else "free"
        
        # Set expiry based on type
        if user_type == TestUserType.EXPIRED:
            self.expires_at = datetime.utcnow() - timedelta(days=1)
        elif user_type == TestUserType.GRACE:
            self.expires_at = datetime.utcnow() + timedelta(days=3)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=30)
            
        # Set hardware ID
        if user_type == TestUserType.HARDWARE_CHANGED:
            self.hardware_id = "different_" + create_hardware_id()
        else:
            self.hardware_id = create_hardware_id()

class TestEnvManager:
    def __init__(self, db_session: SessionLocal):
        self.db = db_session
        self.created_users: List[Dict] = []
        
    def create_test_user(self, user_type: TestUserType) -> Dict:
        """Create a test user with appropriate license"""
        test_data = TestUserData(user_type)
        
        try:
            # Create user
            user = User(
                email=test_data.email,
                hashed_password=get_password_hash(test_data.password),
                full_name=f"Test {user_type.value.title()} User",
                is_active=True,
                subscription_tier=test_data.subscription_tier
            )
            self.db.add(user)
            self.db.flush()
            
            # Create license
            license = License(
                user_id=user.id,
                license_key=generate_license_key(),
                tier=test_data.subscription_tier,
                is_active=True,
                hardware_id=test_data.hardware_id,
                expires_at=test_data.expires_at,
                last_validated=datetime.utcnow()
            )
            self.db.add(license)
            self.db.commit()
            
            # Store created user info
            user_info = {
                "type": user_type.value,
                "email": test_data.email,
                "password": test_data.password,
                "user_id": user.id,
                "license_key": license.license_key,
                "hardware_id": test_data.hardware_id,
                "expires_at": test_data.expires_at
            }
            self.created_users.append(user_info)
            
            logger.info(f"Created test user: {user_info['email']}")
            logger.info(f"License key: {user_info['license_key']}")
            
            return user_info
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating test user: {e}")
            raise
            
    def create_all_test_users(self):
        """Create all types of test users"""
        for user_type in TestUserType:
            self.create_test_user(user_type)
            
    def cleanup_test_users(self):
        """Remove all test users and their licenses"""
        try:
            for user_info in self.created_users:
                user = self.db.query(User).filter(User.id == user_info["user_id"]).first()
                if user:
                    # Delete licenses first
                    self.db.query(License).filter(License.user_id == user.id).delete()
                    # Delete user
                    self.db.delete(user)
                    logger.info(f"Deleted test user: {user.email}")
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up test users: {e}")
            raise
            
    def print_test_users(self):
        """Print information about created test users"""
        print("\nTest Users:")
        print("=" * 50)
        for user in self.created_users:
            print(f"\nType: {user['type']}")
            print(f"Email: {user['email']}")
            print(f"Password: {user['password']}")
            print(f"License Key: {user['license_key']}")
            print(f"Hardware ID: {user['hardware_id'][:8]}...")
            print(f"Expires: {user['expires_at']}")
            print("-" * 30)

def setup_test_environment():
    """Main function to set up test environment"""
    logger.info("Setting up test environment...")
    
    # Initialize database
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        manager = TestEnvManager(db)
        
        # Create all test users
        manager.create_all_test_users()
        
        # Print test user information
        manager.print_test_users()
        
        logger.info("Test environment setup completed successfully")
        
    except Exception as e:
        logger.error(f"Error setting up test environment: {e}")
        raise
    finally:
        db.close()

def cleanup_test_environment():
    """Clean up test environment"""
    logger.info("Cleaning up test environment...")
    
    db = SessionLocal()
    try:
        manager = TestEnvManager(db)
        manager.cleanup_test_users()
        logger.info("Test environment cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error cleaning up test environment: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test environment management")
    parser.add_argument('--cleanup', action='store_true', help='Clean up test environment')
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_environment()
    else:
        setup_test_environment()