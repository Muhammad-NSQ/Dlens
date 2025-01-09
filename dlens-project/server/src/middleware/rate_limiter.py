from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from typing import Dict, Tuple, List
import time
from ..config.settings import settings

class RateLimiter:
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        
    def _clean_old_requests(self, client_ip: str, now: float):
        """Remove requests older than 1 minute"""
        if client_ip in self._requests:
            self._requests[client_ip] = [
                req_time for req_time in self._requests[client_ip]
                if req_time > now - 60
            ]
    
    async def check_rate_limit(self, request: Request, key: str = None):
        """
        Check if request should be rate limited
        
        Args:
            request: FastAPI request object
            key: Optional custom key for rate limiting (defaults to IP address)
        
        Raises:
            HTTPException: If rate limit is exceeded
        """
        client_ip = key or request.client.host
        now = time.time()
        
        # Clean old requests
        self._clean_old_requests(client_ip, now)
        
        # Initialize if new client
        if client_ip not in self._requests:
            self._requests[client_ip] = []
            
        # Check rate limit
        if len(self._requests[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Too many requests",
                    "retry_after": "60 seconds"
                }
            )
        
        # Add current request
        self._requests[client_ip].append(now)

# Global rate limiter instance
rate_limiter = RateLimiter()