"""
Authentication Service - Configuration Settings

Environment-based configuration following 12-factor principles.

Author: GDB Architecture Team
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Authentication Service Configuration
    """
    
    # ================================================================
    # ENVIRONMENT SETTINGS
    # ================================================================
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # ================================================================
    # APPLICATION SETTINGS
    # ================================================================
    APP_NAME: str = "GDB-Authentication-Service"
    TITLE: str = "GDB Authentication Service"
    DESCRIPTION: str = "Central authentication service for GDB microservices"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8004
    
    # ================================================================
    # DATABASE SETTINGS (gdb_auth_db - Auth-only data)
    # ================================================================
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "gdb_auth_db"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = ""
    
    # Connection pooling
    MIN_DB_POOL_SIZE: int = 5
    MAX_DB_POOL_SIZE: int = 20
    
    # ================================================================
    # JWT SECURITY SETTINGS (SHARED ACROSS ALL SERVICES)
    # ================================================================
    
    # Secret key for JWT signing and verification
    # ⚠️ MUST BE IDENTICAL in all microservices (Account, Transaction, User, Auth)
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    
    # JWT Algorithm (HS256 - HMAC SHA-256)
    JWT_ALGORITHM: str = "HS256"
    
    # JWT Token expiry in minutes (15-30 min recommended)
    JWT_EXPIRY_MINUTES: int = 30
    
    # ================================================================
    # INTER-SERVICE COMMUNICATION (StandardizedPlural and LegacySingular)
    # ================================================================
    ACCOUNTS_SERVICE_URL: str = "http://localhost:8001"
    ACCOUNT_SERVICE_URL: str = "http://localhost:8001"
    
    TRANSACTIONS_SERVICE_URL: str = "http://localhost:8002"
    TRANSACTION_SERVICE_URL: str = "http://localhost:8002"
    
    USERS_SERVICE_URL: str = "http://localhost:8003"
    USER_SERVICE_URL: str = "http://localhost:8003"
    
    AUTH_SERVICE_URL: str = "http://localhost:8004"
    AADHAR_SERVICE_URL: str = "http://localhost:8005"
    COMPANY_SERVICE_URL: str = "http://localhost:8006"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8007"
    PAYMENT_GATEWAY_SERVICE_URL: str = "http://localhost:8008"
    
    # Timeout for user service calls (seconds)
    USER_SERVICE_TIMEOUT: int = 10
    
    # ================================================================
    # LOGGING SETTINGS
    # ================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/auth_service.log"
    
    # ================================================================
    # CORS SETTINGS
    # ================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # ================================================================
    # API SETTINGS
    # ================================================================
    API_PREFIX: str = "/api/v1"
    
    # ================================================================
    # PYDANTIC CONFIGURATION
    # ================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


# Load settings from environment
settings = Settings()

# Schema configuration for multi-tenant database
SCHEMA_NAME = "auth_service"

# Update search_path for PostgreSQL
async def set_schema_search_path(connection):
    """Set the search path to use the correct schema."""
    await connection.execute(f"SET search_path TO auth_service, public")
