"""
Tests for enhanced security utilities
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import os
import hmac
import platform
import logging
import sys
from dlens.core.license_client import LicenseClient
from dlens.utils.feature_definitions import LicenseTier
from dlens.utils.security import create_validation_token , decrypt_sensitive_data

# Setup logging for tests
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MockAuthClient:
    def __init__(self):
        self.token = "test_token"
    
    def get_auth_header(self):
        return {"Authorization": f"Bearer {self.token}"}

@pytest.fixture(autouse=True)
def setup_environment(monkeypatch):
    """Set up test environment"""
    if platform.system() == "Windows":
        monkeypatch.setenv("PATH", f"{os.environ['PATH']};C:\\Windows\\System32\\WindowsPowerShell\\v1.0")

@pytest.fixture
def test_home_dir():
    """Create a temporary home directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def license_client(test_home_dir, monkeypatch):
    """Create a LicenseClient instance"""
    # Set HOME for consistent paths
    monkeypatch.setenv("HOME", str(test_home_dir))
    
    # Create config directory
    config_dir = test_home_dir / '.config' / 'dlens'
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create initial config
    config_file = config_dir / 'config.json'
    with open(config_file, 'w') as f:
        json.dump({
            "license_tier": "free",
            "offline_mode": True
        }, f)
    
    # Create and initialize client
    auth_client = MockAuthClient()
    client = LicenseClient(auth_client)
    return client

@pytest.fixture
def mock_home_dir(test_home_dir):
    """Provide mocked home directory with proper path resolution"""
    home_path = test_home_dir.resolve()  # Get full path
    return home_path

def test_cache_encryption(license_client, mock_home_dir, monkeypatch):
    """Test cache encryption and decryption"""
    logger.info("\n=== Starting cache encryption test ===")
    
    # Set up home directory for Windows
    monkeypatch.setenv("HOME", str(mock_home_dir))
    monkeypatch.setenv("USERPROFILE", str(mock_home_dir))
    monkeypatch.setenv("APPDATA", str(mock_home_dir))
    
    # Ensure secure storage directory exists
    secure_dir = mock_home_dir / '.config' / 'dlens' / 'secure'
    secure_dir.mkdir(parents=True, exist_ok=True)
    
    # Create configuration directory
    config_dir = mock_home_dir / '.config' / 'dlens'
    config_dir.mkdir(parents=True, exist_ok=True)
    
    test_data = {
        "license_key": "TEST-KEY",
        "hardware_id": license_client.hardware_id,
        "tier": "pro"
    }
    
    # Log initial state
    logger.info("\n=== Initial Setup ===")
    logger.info(f"Mock home directory: {mock_home_dir}")
    logger.info(f"Config directory: {config_dir}")
    logger.info(f"Secure directory: {secure_dir}")
    logger.info(f"Test data: {test_data}")
    
    # Setup first client
    logger.info("\n=== First Client Setup ===")
    license_client._cache_path = config_dir / 'license_cache.json'
    license_client._secure_storage = secure_dir
    logger.info(f"Cache path: {license_client._cache_path}")
    logger.info(f"Secure storage: {license_client._secure_storage}")
    logger.info(f"Secure key: {license_client._get_secure_key()}")
    
    # Save data
    logger.info("\n=== Saving Cache ===")
    license_client._cache = test_data.copy()
    license_client._save_cache()
    
    # Verify saved data
    logger.info("\n=== Verifying Saved Data ===")
    assert license_client._cache_path.exists(), "Cache file not created"
    encrypted_content = license_client._cache_path.read_text()
    logger.info(f"Encrypted content: {encrypted_content}")
    
    # Try manual decryption
    decrypted = decrypt_sensitive_data(encrypted_content, license_client._get_secure_key())
    logger.info(f"Manual decryption result: {decrypted}")
    
    # Create and setup new client
    logger.info("\n=== Creating New Client ===")
    new_client = LicenseClient(MockAuthClient(), home_dir=mock_home_dir)
    logger.info(f"New client cache path: {new_client._cache_path}")
    logger.info(f"New client secure key: {new_client._get_secure_key()}")
    
    # Verify paths
    logger.info("\n=== Verifying Paths ===")
    assert new_client._cache_path.resolve() == license_client._cache_path.resolve(), \
        f"Path mismatch: {new_client._cache_path} != {license_client._cache_path}"
    assert new_client._secure_storage.resolve() == license_client._secure_storage.resolve(), \
        f"Storage mismatch: {new_client._secure_storage} != {license_client._secure_storage}"
    
    # Load and verify cache
    logger.info("\n=== Loading Cache ===")
    logger.info(f"Original cache: {license_client._cache}")
    logger.info(f"New client cache before load: {new_client._cache}")
    
    # Attempt to read file directly
    if new_client._cache_path.exists():
        content = new_client._cache_path.read_text()
        logger.info(f"Raw file content: {content}")
    else:
        logger.error("Cache file does not exist!")
    
    new_client._load_cache()
    logger.info(f"New client cache after load: {new_client._cache}")
    
    # Compare contents with detailed output
    logger.info("\n=== Comparing Contents ===")
    for key in test_data:
        if key not in new_client._cache:
            logger.error(f"Missing key: {key}")
        elif new_client._cache[key] != test_data[key]:
            logger.error(f"Value mismatch for {key}:")
            logger.error(f"  Expected: {test_data[key]}")
            logger.error(f"  Got: {new_client._cache[key]}")
    
    assert new_client._cache == test_data, \
        f"Cache mismatch.\nExpected: {test_data}\nGot: {new_client._cache}"

def test_secure_storage(license_client):
    """Test secure storage creation and key handling"""
    assert license_client._secure_storage.exists()
    key = license_client._get_secure_key()
    assert key and len(key) == 64
    assert license_client._get_secure_key() == key

def test_validation_token_security(license_client):
    """Test validation token security"""
    license_key = "TEST-KEY"
    token = create_validation_token(
        license_key,
        license_client.hardware_id,
        license_client._get_secure_key()
    )
    
    license_client._cache = {
        "license_key": license_key,
        "hardware_id": license_client.hardware_id,
        "validation_token": token,
        "last_validated": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "tier": "pro"
    }
    license_client._save_cache()
    
    assert license_client._validate_offline_license(license_key)
    assert license_client.feature_manager._current_tier == LicenseTier.PRO

def test_hardware_binding(license_client):
    """Test hardware binding security"""
    license_key = "TEST-KEY"
    wrong_hardware_id = "wrong-id"
    
    token = create_validation_token(
        license_key,
        wrong_hardware_id,
        license_client._get_secure_key()
    )
    
    license_client._cache = {
        "license_key": license_key,
        "hardware_id": wrong_hardware_id,
        "validation_token": token,
        "last_validated": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "tier": "pro"
    }
    license_client._save_cache()
    
    assert not license_client._validate_offline_license(license_key)
    assert license_client.feature_manager._current_tier == LicenseTier.FREE

def test_license_expiration(license_client):
    """Test license expiration handling"""
    license_key = "TEST-KEY"
    token = create_validation_token(
        license_key,
        license_client.hardware_id,
        license_client._get_secure_key()
    )
    
    license_client._cache = {
        "license_key": license_key,
        "hardware_id": license_client.hardware_id,
        "validation_token": token,
        "last_validated": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "tier": "pro"
    }
    license_client._save_cache()
    
    assert not license_client._validate_offline_license(license_key)
    assert license_client.feature_manager._current_tier == LicenseTier.FREE

def test_cache_tampering(license_client):
    """Test cache tampering detection"""
    license_key = "TEST-KEY"
    token = create_validation_token(
        license_key,
        license_client.hardware_id,
        license_client._get_secure_key()
    )
    
    license_client._cache = {
        "license_key": license_key,
        "hardware_id": license_client.hardware_id,
        "validation_token": token,
        "last_validated": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "tier": "pro"
    }
    license_client._save_cache()
    
    encrypted_content = license_client._cache_path.read_text()
    parts = encrypted_content.split(':')
    tampered_content = ':'.join([parts[0], parts[1], 'a' * 64, parts[3]])
    license_client._cache_path.write_text(tampered_content)
    
    new_client = LicenseClient(MockAuthClient())
    new_client._load_cache()
    
    assert not new_client._validate_offline_license(license_key)
    assert new_client.feature_manager._current_tier == LicenseTier.FREE

@pytest.mark.asyncio
async def test_license_info_security(license_client):
    """Test license info includes security information"""
    # Ensure directories exist
    license_client._secure_storage.mkdir(parents=True, exist_ok=True)
    
    # Create a proper validation token
    license_key = "TEST-KEY"
    token = create_validation_token(
        license_key,
        license_client.hardware_id,
        license_client._get_secure_key()
    )
    
    # Create test data
    test_data = {
        "license_key": license_key,
        "hardware_id": license_client.hardware_id,
        "validation_token": token,
        "last_validated": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "tier": "pro"
    }
    
    # Save to cache using the client's encryption
    license_client._cache = test_data.copy()
    license_client._save_cache()
    
    # Force offline mode to test cache reading
    license_client.server_url = None
    
    # Get license info
    info = await license_client.get_license_info()
    
    # Verify the results
    assert info is not None
    assert info["license_key"] == license_key
    assert info["hardware_id"] == license_client.hardware_id
    assert info["tier"] == "pro"
    
if __name__ == '__main__':
    pytest.main([__file__, "-v", "--capture=no"])