from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from datetime import datetime

from .config.settings import settings
from .api.routes import auth, license
from .middleware.logging import log_requests
from .middleware.rate_limiter import rate_limiter
from .utils.exceptions import (
    dlens_exception_handler,
    http_exception_handler,
    DLensException
)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Add logging middleware
app.middleware("http")(log_requests)

# Add rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not settings.DISABLE_RATE_LIMIT:
        await rate_limiter.check_rate_limit(request)
    return await call_next(request)

# Exception handlers
app.add_exception_handler(DLensException, dlens_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"]
)

app.include_router(
    license.router,
    prefix=f"{settings.API_V1_STR}/license",
    tags=["license"]
)

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT
    }

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "db_status": "connected"  # You might want to add actual DB health check
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Initialize database if needed
    # Set up any background tasks
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Clean up any resources
    pass