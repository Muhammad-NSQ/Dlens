"""
Script to register a test user and create a test license
Save as setup_test_env.py
"""
import asyncio
import httpx
from rich.console import Console
from datetime import datetime, timedelta
import base64
import json

console = Console()

def decode_token_payload(token: str) -> dict:
    """Decode JWT token payload without verification"""
    try:
        # Split the token and get the payload part
        parts = token.split('.')
        if len(parts) != 3:
            return {}
            
        # Decode the payload part
        payload = parts[1]
        # Add padding if needed
        pad = len(payload) % 4
        if pad:
            payload += '=' * (4 - pad)
            
        # Convert URL-safe base64 to regular base64
        payload = payload.replace('-', '+').replace('_', '/')
        
        decoded = base64.b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        console.print(f"[red]Error decoding token: {str(e)}[/red]")
        return {}

async def setup_test_environment():
    server_url = "http://localhost:8000"
    
    # Test user details
    test_user = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    console.print("\n[bold cyan]Setting up Test Environment[/bold cyan]")
    
    async with httpx.AsyncClient() as client:
        # 1. Register test user
        console.print("\n[yellow]Registering test user...[/yellow]")
        try:
            response = await client.post(
                f"{server_url}/api/v1/auth/register",
                json=test_user
            )
            if response.status_code == 200:
                console.print("[green]Test user registered successfully![/green]")
                user_data = response.json()
                user_id = user_data.get('id')
                console.print(f"User ID: {user_id}")
            elif response.status_code == 400:
                console.print("[yellow]User already exists[/yellow]")
            else:
                console.print(f"[red]Registration failed: {response.text}[/red]")
                return
                
        except Exception as e:
            console.print(f"[red]Error during registration: {str(e)}[/red]")
            return
        
        # 2. Login to get token
        console.print("\n[yellow]Testing login...[/yellow]")
        try:
            response = await client.post(
                f"{server_url}/api/v1/auth/login",
                data={
                    "username": test_user["email"],
                    "password": test_user["password"]
                }
            )
            if response.status_code == 200:
                console.print("[green]Login successful![/green]")
                token_data = response.json()
                access_token = token_data.get("access_token")
                
                # Decode token to get user ID
                payload = decode_token_payload(access_token)
                user_id = payload.get('sub')
                
                # Store these credentials for testing
                console.print("\n[bold]Test Credentials:[/bold]")
                console.print(f"Email: {test_user['email']}")
                console.print(f"Password: {test_user['password']}")
                console.print(f"Token: {access_token[:20]}...")
                console.print(f"User ID from token: {user_id}")
                
            else:
                console.print(f"[red]Login failed: {response.text}[/red]")
                return
                
        except Exception as e:
            console.print(f"[red]Error during login: {str(e)}[/red]")
            return

        if not user_id:
            console.print("[red]Could not determine user ID. License generation skipped.[/red]")
            return

        # 3. Generate test license
        console.print("\n[yellow]Generating test license...[/yellow]")
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # First check if user already has a license
            license_check = await client.get(
                f"{server_url}/api/v1/license/status",
                headers=headers
            )
            
            if license_check.status_code == 200:
                console.print("[yellow]User already has an active license.[/yellow]")
                license_info = license_check.json()
                console.print(f"License Key: {license_info.get('license_key')}")
                
            elif license_check.status_code == 404:
                # No active license, generate new one
                license_data = {
                    "user_id": int(user_id),  # Convert to int since JWT payload might be string
                    "tier": "pro",
                    "hardware_id": None,
                    "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
                }
                
                response = await client.post(
                    f"{server_url}/api/v1/license/generate",
                    json=license_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    license_info = response.json()
                    console.print("[green]License generated successfully![/green]")
                    console.print(f"License Key: {license_info.get('license_key')}")
                else:
                    console.print(f"[red]License generation failed: {response.text}[/red]")
            else:
                console.print(f"[red]Error checking license status: {license_check.text}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error generating license: {str(e)}[/red]")

    console.print("\n[bold green]Test environment setup complete![/bold green]")

if __name__ == "__main__":
    asyncio.run(setup_test_environment())