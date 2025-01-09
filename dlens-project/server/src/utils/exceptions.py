from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Any, Dict, Optional

class DLensException(HTTPException):
    """Base exception for DLens application"""
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or str(status_code)

class LicenseException(DLensException):
    """Exception for license-related errors"""
    pass

class AuthenticationException(DLensException):
    """Exception for authentication-related errors"""
    pass

async def dlens_exception_handler(request: Request, exc: DLensException):
    """Handler for DLens custom exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url),
            "detail": exc.detail,
            "error_code": exc.error_code,
            "status_code": exc.status_code
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for standard HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url),
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

# Common exceptions
class InvalidLicenseException(LicenseException):
    def __init__(self, detail: str = "Invalid license"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="INVALID_LICENSE"
        )

class ExpiredLicenseException(LicenseException):
    def __init__(self, detail: str = "License has expired"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="LICENSE_EXPIRED"
        )

class InvalidCredentialsException(AuthenticationException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"}
        )

class RateLimitExceededException(DLensException):
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED"
        )