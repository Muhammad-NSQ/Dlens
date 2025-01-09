"""
Tests for LicenseStateManager with proper async handling
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import asyncio

from dlens.utils.license_state import LicenseStateManager, LicenseState
from dlens.utils.feature_definitions import LicenseTier

@pytest_asyncio.fixture
async def mock_license_client(temp_dir):
    """Create a mock license client with proper async mocking"""
    client = Mock()
    client._get_secure_key.return_value = "test-key"
    client.hardware_id = "test-hardware-id"
    client.config = {"offline_mode": False}
    client.feature_manager = Mock()
    client.feature_manager.get_feature_details.return_value = {}
    
    # Mock get_license_info as an AsyncMock
    client.get_license_info = AsyncMock()
    return client

@pytest_asyncio.fixture
async def state_manager(mock_license_client, temp_dir):
    """Create a LicenseStateManager instance with proper cleanup"""
    manager = LicenseStateManager(
        license_client=mock_license_client,
        cache_dir=temp_dir,
        sync_interval=1  # Fast sync for testing
    )
    yield manager
    await manager.stop()  # Ensure cleanup

@pytest_asyncio.fixture
async def cleanup_tasks():
    """Cleanup any stray tasks after each test"""
    yield
    tasks = [t for t in asyncio.all_tasks() 
             if not t.done() and t != asyncio.current_task()]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_initialization(state_manager):
    """Test initial state"""
    assert state_manager.current_state == LicenseState.UNACTIVATED
    assert isinstance(state_manager.get_status(), dict)

@pytest.mark.asyncio
async def test_state_transitions(state_manager):
    """Test state transition handling"""
    # Initialize with license info
    state_manager._state_data['license_info'] = {
        'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat()
    }
    
    # Test transition to ACTIVATING
    state_manager._transition_to(LicenseState.ACTIVATING)
    assert state_manager.current_state == LicenseState.ACTIVATING
    
    # Test transition to ACTIVE
    state_manager._transition_to(LicenseState.ACTIVE)
    assert state_manager.current_state == LicenseState.ACTIVE
    
    # Test transition to GRACE_PERIOD
    state_manager._transition_to(LicenseState.GRACE_PERIOD)
    assert state_manager.current_state == LicenseState.GRACE_PERIOD
    
    # Test transition to EXPIRED
    state_manager._transition_to(LicenseState.EXPIRED)
    assert state_manager.current_state == LicenseState.EXPIRED
    state_manager.client.feature_manager.set_tier.assert_called_with(LicenseTier.FREE)

@pytest.mark.asyncio
async def test_sync_state(state_manager, mock_license_client):
    """Test state synchronization"""
    # Mock successful license info
    future_date = datetime.utcnow() + timedelta(days=30)
    mock_info = {
        'expires_at': future_date.isoformat(),
        'tier': 'pro',
        'hardware_id': mock_license_client.hardware_id,
        'features': {}
    }
    mock_license_client.get_license_info.return_value = mock_info
    
    # Pre-activate the license
    state_manager._state_data['license_info'] = mock_info
    state_manager._transition_to(LicenseState.ACTIVATING)
    
    # Start sync
    await state_manager.start()
    await asyncio.sleep(2)  # Allow time for sync
    
    # Verify state
    assert state_manager.current_state == LicenseState.ACTIVE
    assert 'license_info' in state_manager._state_data
    
    # Cleanup
    await state_manager.stop()

@pytest.mark.asyncio
async def test_grace_period_transition(state_manager, mock_license_client):
    """Test grace period handling"""
    # Mock license info with near expiration
    near_expiry = datetime.utcnow() + timedelta(days=5)
    mock_info = {
        'expires_at': near_expiry.isoformat(),
        'tier': 'pro',
        'hardware_id': mock_license_client.hardware_id,
        'features': {}
    }
    mock_license_client.get_license_info.return_value = mock_info
    
    # Pre-activate the license
    state_manager._state_data['license_info'] = mock_info
    state_manager._transition_to(LicenseState.ACTIVE)
    
    # Start sync
    await state_manager.start()
    await asyncio.sleep(2)  # Allow time for sync
    
    # Verify grace period
    assert state_manager.current_state == LicenseState.GRACE_PERIOD
    status = state_manager.get_status()
    assert 0 <= status['days_remaining'] <= 5
    
    # Cleanup
    await state_manager.stop()

@pytest.mark.asyncio
async def test_offline_handling(state_manager, mock_license_client):
    """Test offline mode handling"""
    # Force offline mode and prepare state
    mock_license_client.config['offline_mode'] = True
    mock_license_client.config['license_key'] = 'test-key'  # Add license key to config
    
    # Mock offline validation
    mock_license_client._validate_offline_license = Mock(return_value=True)
    
    # Set up mock license info for offline mode
    mock_info = {
        'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
        'tier': 'pro',
        'hardware_id': mock_license_client.hardware_id,
        'offline_mode': True,
        'features': {},
        'license_key': 'test-key'
    }
    
    # Set up the license client cache
    mock_license_client._cache = {
        'license_key': 'test-key',
        'hardware_id': mock_license_client.hardware_id,
        'expires_at': mock_info['expires_at'],
        'tier': 'pro',
        'validation_token': 'test-token'
    }
    
    # Configure the mock get_license_info to return the offline info
    mock_license_client.get_license_info.return_value = mock_info
    
    # Pre-activate with offline data
    state_manager._state_data['license_info'] = mock_info
    
    # Start in ACTIVE state
    state_manager._transition_to(LicenseState.ACTIVE)
    
    # Simulate transition to ERROR which should trigger offline validation
    state_manager._transition_to(LicenseState.ERROR)
    
    # No need to wait since the validation happens synchronously in _transition_to
    
    # Should have transitioned back to ACTIVE due to successful offline validation
    assert state_manager.current_state == LicenseState.ACTIVE
    mock_license_client._validate_offline_license.assert_called_once_with('test-key')

@pytest.mark.asyncio
async def test_retry_mechanism(state_manager, mock_license_client):
    """Test sync retry mechanism"""
    # Pre-activate the license
    state_manager._state_data['license_info'] = {
        'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
        'tier': 'pro'
    }
    state_manager._transition_to(LicenseState.ACTIVE)
    
    # Mock failed license info
    mock_license_client.get_license_info.side_effect = Exception("Network error")
    
    # Start sync
    await state_manager.start()
    await asyncio.sleep(2)  # Allow time for sync
    
    # Verify retry count increased and state changed
    assert state_manager._retry_count > 0
    assert state_manager.current_state == LicenseState.ERROR
    
    # Cleanup
    await state_manager.stop()

@pytest.mark.asyncio
async def test_expiration_handling(state_manager, mock_license_client):
    """Test license expiration handling"""
    # Set expired license
    past_date = datetime.utcnow() - timedelta(days=1)
    mock_info = {
        'expires_at': past_date.isoformat(),
        'tier': 'pro',
        'hardware_id': mock_license_client.hardware_id,
        'features': {}
    }
    mock_license_client.get_license_info.return_value = mock_info
    
    # Pre-activate with expired license
    state_manager._state_data['license_info'] = mock_info
    state_manager._transition_to(LicenseState.ACTIVE)
    
    # Start sync
    await state_manager.start()
    await asyncio.sleep(2)  # Allow time for sync
    
    # Verify expiration handling
    assert state_manager.current_state == LicenseState.EXPIRED
    state_manager.client.feature_manager.set_tier.assert_called_with(LicenseTier.FREE)
    
    # Cleanup
    await state_manager.stop()

def test_state_persistence(state_manager, temp_dir):
    """Test state persistence"""
    # Set initial state with required data
    mock_info = {
        'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
        'hardware_id': state_manager.client.hardware_id,
        'tier': 'pro',
        'features': {}
    }
    state_manager._state_data['license_info'] = mock_info
    state_manager._transition_to(LicenseState.ACTIVE)
    state_manager._save_state()
    
    # Create new instance
    new_manager = LicenseStateManager(
        license_client=state_manager.client,
        cache_dir=temp_dir
    )
    
    # Verify state was loaded
    assert new_manager.current_state == LicenseState.ACTIVE
    assert 'license_info' in new_manager._state_data

if __name__ == '__main__':
    pytest.main(['-v', '--asyncio-mode=strict'])