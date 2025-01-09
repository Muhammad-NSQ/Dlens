# test_features.py

import pytest
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import json
from unittest.mock import Mock, patch

from dlens.core.license_client import LicenseClient
from dlens.utils.feature_definitions import LicenseTier
from dlens.utils.security import create_validation_token

@pytest.fixture
def temp_dir():
    """Fixture to provide temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_auth_client():
    """Fixture to provide mock auth client"""
    auth_client = Mock()
    auth_client.get_auth_header.return_value = {"Authorization": "Bearer test-token"}
    return auth_client

@pytest.fixture
def license_client(temp_dir, mock_auth_client):
    """Fixture to provide license client instance"""
    client = LicenseClient(
        auth_client=mock_auth_client,
        home_dir=temp_dir,
        cache_dir=temp_dir
    )
    return client

def test_initialization(license_client):
    """Test license client initialization"""
    assert license_client.hardware_id is not None
    assert len(license_client.hardware_id) == 64
    assert license_client.feature_manager is not None

def test_cache_management(license_client):
    """Test cache operations"""
    test_data = {
        "license_key": "test-key",
        "hardware_id": license_client.hardware_id,
        "tier": "pro"
    }
    license_client._cache = test_data.copy()
    license_client._save_cache()
    
    new_client = LicenseClient(
        auth_client=mock_auth_client,
        home_dir=license_client._home_dir,
        cache_dir=license_client._cache_dir
    )
    assert new_client._cache.get("license_key") == "test-key"
    assert new_client._cache.get("tier") == "pro"

@pytest.mark.asyncio
async def test_validate_license_online(license_client):
    """Test online license validation"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tier": "pro",
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        result = await license_client.validate_license("test-key")
        assert result is True
        assert license_client._cache.get("tier") == "pro"

@pytest.mark.asyncio
async def test_validate_license_offline(license_client):
    """Test offline license validation"""
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    validation_token = create_validation_token(
        "test-key",
        license_client.hardware_id,
        license_client._get_secure_key()
    )
    
    license_client._cache = {
        "license_key": "test-key",
        "hardware_id": license_client.hardware_id,
        "validation_token": validation_token,
        "last_validated": datetime.utcnow().isoformat(),
        "expires_at": expires_at.isoformat(),
        "tier": "pro"
    }
    license_client._save_cache()
    
    license_client.server_url = None
    result = await license_client.validate_license("test-key")
    assert result is True

def test_activation_status(license_client):
    """Test activation status checking"""
    status = license_client.check_activation_status()
    assert status["is_activated"] is False
    assert status["tier"] == "free"
    assert len(status["messages"]) > 0
    
    license_client._cache = {
        "license_key": "test-key",
        "hardware_id": license_client.hardware_id,
        "tier": "pro",
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "last_validated": datetime.utcnow().isoformat()
    }
    
    status = license_client.check_activation_status()
    assert status["is_activated"] is True
    assert status["tier"] == "pro"
    assert status["expires_in_days"] is not None

def test_deactivation(license_client):
    """Test license deactivation"""
    license_client._cache = {
        "license_key": "test-key",
        "hardware_id": license_client.hardware_id,
        "tier": "pro"
    }
    license_client._save_cache()
    
    result = license_client.deactivate()
    assert result is True
    assert not license_client._cache_path.exists()
    assert license_client.feature_manager._current_tier == LicenseTier.FREE

@pytest.mark.asyncio
async def test_refresh_license(license_client):
    """Test license refresh"""
    license_client.config = {"license_key": "test-key"}
    
    with patch.object(license_client, 'validate_license') as mock_validate:
        mock_validate.return_value = True
        result = await license_client.refresh_license()
        assert result is True
        mock_validate.assert_called_once_with("test-key")

if __name__ == '__main__':
    pytest.main(["-v", "--asyncio-mode=strict"])