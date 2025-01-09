"""
Updated test script with proper license handling
Save as test_components.py
"""
import asyncio
from pathlib import Path
from rich.console import Console
import httpx

from dlens.core.auth_client import AuthClient
from dlens.core.license_client import LicenseClient
from dlens.core.server_connector import ServerConnector
from dlens.config.config_manager import ConfigManager

console = Console()

# Test credentials (matching setup_test_env.py)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

async def test_server_connection():
    """Test basic server connection"""
    server = ServerConnector("http://localhost:8000")
    is_connected = await server.test_connection()
    console.print(f"Server connection test: {'✓' if is_connected else '✗'}")
    return is_connected

async def test_auth():
    """Test authentication"""
    auth = AuthClient("http://localhost:8000")
    try:
        result = await auth.login(TEST_EMAIL, TEST_PASSWORD)
        if not result:
            console.print("[yellow]Login failed with test credentials[/yellow]")
        console.print(f"Authentication test: {'✓' if result else '✗'}")
        return result, auth  # Return auth client for use in license test
    except Exception as e:
        console.print(f"[red]Authentication error: {str(e)}[/red]")
        return False, None

async def test_license():
    """Test license validation"""
    auth_result, auth_client = await test_auth()
    if not auth_result or not auth_client:
        console.print("[red]License test skipped due to authentication failure[/red]")
        return False

    license_client = LicenseClient(auth_client)
    try:
        # Check license status first
        license_status = await license_client.get_license_info()
        if license_status:
            console.print("[green]Found active license:[/green]")
            console.print(f"Tier: {license_status.get('tier')}")
            console.print(f"License Key: {license_status.get('license_key')}")
            
            # Try validating the found license
            result = await license_client.validate_license(license_status.get('license_key'))
            console.print(f"License validation test: {'✓' if result else '✗'}")
            return result
        else:
            console.print("[yellow]No active license found[/yellow]")
            return False
            
    except Exception as e:
        console.print(f"[red]License validation error: {str(e)}[/red]")
        return False

async def test_config():
    """Test configuration management"""
    try:
        test_settings = {
            "test_key": "test_value",
            "server_url": "http://localhost:8000",
            "offline_mode": False
        }
        
        # Update config with test settings
        ConfigManager.update_config(test_settings)
        
        # Load and verify config
        config = ConfigManager.load_config()
        result = all(config.get(k) == v for k, v in test_settings.items())
        
        console.print(f"Configuration test: {'✓' if result else '✗'}")
        if result:
            console.print("Verified settings:")
            for k, v in test_settings.items():
                console.print(f"  {k}: {v}")
        return result
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        return False

async def test_offline_mode():
    """Test offline capabilities"""
    console.print("\n[cyan]Testing Offline Mode...[/cyan]")
    
    # First ensure we have valid credentials and license
    auth_result, auth_client = await test_auth()
    if not auth_result:
        console.print("[red]Offline test skipped: Need valid credentials first[/red]")
        return False
        
    try:
        # Cache current credentials
        config = ConfigManager.load_config()
        current_online_state = {
            "auth_token": auth_client.token,
            "license_key": config.get('license_key'),
            "offline_mode": False,
            "server_url": "http://localhost:8000"
        }
        
        # Store for offline use
        ConfigManager.update_config(current_online_state)
        console.print("[green]Cached credentials for offline use[/green]")
        
        # Create new server connector in offline mode
        offline_config = current_online_state.copy()
        offline_config["offline_mode"] = True
        offline_config["server_url"] = None
        
        ConfigManager.update_config(offline_config)
        console.print("[green]Switched to offline mode[/green]")
        
        # Test offline initialization
        offline_server = ServerConnector()
        result = await offline_server.initialize()
        
        console.print(f"Offline mode initialization: {'✓' if result else '✗'}")
        
        if result:
            console.print("[green]Successfully validated offline credentials and license[/green]")
            
            # Test offline license validation
            license_client = LicenseClient(offline_server.auth_client)
            license_info = await license_client.get_license_info()
            
            if license_info:
                console.print("\nOffline license information:")
                console.print(f"  Tier: {license_info.get('tier')}")
                console.print(f"  License Key: {license_info.get('license_key')}")
                console.print(f"  Offline Mode: {license_info.get('offline_mode', True)}")
            else:
                console.print("[yellow]Could not retrieve offline license information[/yellow]")
        else:
            console.print("[yellow]Offline validation failed[/yellow]")
            
        return result
        
    except Exception as e:
        console.print(f"[red]Offline mode error: {str(e)}[/red]")
        return False
    finally:
        # Restore online mode
        ConfigManager.update_config(current_online_state)
        console.print("[green]Restored online mode[/green]")

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
    auth_success, _ = await test_auth()
    
    # Test license
    console.print("\n[cyan]Testing License...[/cyan]")
    if auth_success:
        await test_license()
    
    # Test offline mode
    if auth_success:
        await test_offline_mode()

if __name__ == "__main__":
    asyncio.run(main())