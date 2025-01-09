from fastapi import Request
from datetime import datetime
import logging
import json
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class RequestLogMiddleware:
    async def __call__(self, request: Request, call_next):
        """Log request details and timing"""
        # Start timing
        start_time = datetime.utcnow()
        
        # Get request details
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else None
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_detail = None
        except Exception as e:
            status_code = 500
            error_detail = str(e)
            raise e 
        
        finally:
            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Log request
            log_data = {
                "timestamp": start_time.isoformat(),
                "path": path,
                "method": method,
                "status_code": status_code,
                "duration": f"{duration:.3f}s",
                "client_ip": client_ip
            }
            
            if error_detail:
                log_data["error"] = error_detail
                
            logging.info(json.dumps(log_data))
            
        return response

async def log_requests(request: Request, call_next):
    """Middleware function for request logging"""
    middleware = RequestLogMiddleware()
    return await middleware(request, call_next)