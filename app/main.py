"""
Authentication Service - FastAPI Application

Central authentication service for GDB microservices.
Issues JWT tokens that other services verify independently.

Author: GDB Architecture Team
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.settings import settings
from app.database.db import db
from app.api.auth_routes import router as auth_router
from app.exceptions.auth_exceptions import AuthenticationException


# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    
    Startup: Initialize database connection pool
    Shutdown: Close database connection pool
    """
    # Startup
    logger.info("Starting Authentication Service...")
    try:
        await db.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Authentication Service...")
    await db.disconnect()
    logger.info("Database disconnected")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Central authentication service for GDB microservices",
    docs_url="/api/v1/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Exception handler for custom exceptions
@app.exception_handler(AuthenticationException)
async def auth_exception_handler(request, exc: AuthenticationException):
    """Handle custom authentication exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
        },
    )


# Include routers
app.include_router(auth_router)


# Root endpoint
@app.get("/", tags=["health"])
async def root():
    """Service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "auth-service",
    }


# Ready check endpoint
@app.get("/ready", tags=["health"])
async def ready():
    """Readiness check (database connectivity)."""
    try:
        # Test database connection
        await db.fetchval("SELECT 1")
        return {
            "status": "ready",
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e),
            },
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
