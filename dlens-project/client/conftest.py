# conftest.py

import pytest
from pathlib import Path
import tempfile
from unittest.mock import Mock
import asyncio

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']

def pytest_configure(config):
    """Configure pytest settings"""
    # Add asyncio marker
    config.addinivalue_line(
        'markers',
        'asyncio: mark test as async'
    )

@pytest.fixture
def event_loop_policy():
    """Provide event loop policy"""
    return asyncio.WindowsProactorEventLoopPolicy()

@pytest.fixture
def mock_auth_client():
    """Provide mock auth client"""
    auth_client = Mock()
    auth_client.get_auth_header.return_value = {"Authorization": "Bearer test-token"}
    return auth_client

@pytest.fixture
def temp_dir():
    """Provide temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)