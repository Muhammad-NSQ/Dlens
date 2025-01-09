"""
Simple test script to verify components
Save this in dlens-project/client/test_components.py
"""
import asyncio
from pathlib import Path
from rich.console import Console

# Import components directly using relative imports
from dlens.core.auth_client import AuthClient
from dlens.core.license_client import LicenseClient
from dlens.core.server_connector import ServerConnector
from dlens.config.config_manager import ConfigManager

console = Console()

async def test_server_connection():
    """Test basic server connection"""
    server = ServerConnector("http://localhost:8000")  # Use your server URL
    is_connected = await server.test_connection()
    console.print(f"Server connection test: {'✓' if is_connected else '✗'}")
    return is_connected

async def test_auth():
    """Test authentication"""
    auth = AuthClient("http://localhost:8000")  # Use your server URL
    try:
        # Try login with test credentials
        result = await auth.login("test@example.com", "testpassword")
        console.print(f"Authentication test: {'✓' if result else '✗'}")
        return result
    except Exception as e:
        console.print(f"Authentication error: {str(e)}")
        return False

async def test_license():
    """Test license validation"""
    auth = AuthClient("http://localhost:8000")
    license_client = LicenseClient(auth)
    try:
        # Try license validation with a test key
        result = await license_client.validate_license("TEST-LICENSE-KEY")
        console.print(f"License validation test: {'✓' if result else '✗'}")
        return result
    except Exception as e:
        console.print(f"License validation error: {str(e)}")
        return False

async def test_config():
    """Test configuration management"""
    try:
        # Test basic config operations
        ConfigManager.update_config({"test_key": "test_value"})
        config = ConfigManager.load_config()
        result = config.get("test_key") == "test_value"
        console.print(f"Configuration test: {'✓' if result else '✗'}")
        return result
    except Exception as e:
        console.print(f"Configuration error: {str(e)}")
        return False

async def main():
    console.print("\n=== Testing DLens Components ===\n")
    
    # Test server connection
    console.print("\n[cyan]Testing Server Connection...[/cyan]")
    if not await test_server_connection():
        console.print("[red]Server connection failed. Make sure the server is running.[/red]")
        return
    
    # Test configuration
    console.print("\n[cyan]Testing Configuration...[/cyan]")
    await test_config()
    
    # Test authentication
    console.print("\n[cyan]Testing Authentication...[/cyan]")
    if not await test_auth():
        console.print("[yellow]Authentication test failed.[/yellow]")
    
    # Test license
    console.print("\n[cyan]Testing License...[/cyan]")
    await test_license()

if __name__ == "__main__":
    # Run all tests
    asyncio.run(main())