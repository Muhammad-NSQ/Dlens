"""
Script to check database contents
"""
import sys
from pathlib import Path

# Add parent directory to Python path to allow imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import SessionLocal, Base, engine
from src.models.user import User
from src.models.license import License

def check_database():
    """Print all users and their licenses in the database"""
    # Create tables if they don't exist
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Get all users
        print("\nUsers in database:")
        print("-" * 50)
        users = db.query(User).all()
        if not users:
            print("No users found in database!")
        else:
            for user in users:
                print(f"\nUser Details:")
                print(f"Email: {user.email}")
                print(f"Tier: {user.subscription_tier}")
                print(f"Active: {user.is_active}")
                
                # Get user's license
                license = db.query(License).filter(
                    License.user_id == user.id,
                    License.is_active == True
                ).first()
                
                if license:
                    print(f"License Key: {license.license_key}")
                    print(f"License Tier: {license.tier}")
                    print(f"Expires At: {license.expires_at}")
                else:
                    print("No active license")
                print("-" * 50)
            
    finally:
        db.close()

if __name__ == "__main__":
    check_database()