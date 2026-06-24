from pydantic.dataclasses import dataclass
from pydantic import Field
from typing import Optional
from datetime import datetime


@dataclass
class LoginRequest:
    """Request model for user login."""
    login_id: str = Field(..., min_length=1, max_length=255, description="User login identifier")
    password: str = Field(..., min_length=1, max_length=1000, description="User password")


@dataclass
class TokenResponse:
    """Response model for successful login (JWT token)."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")
    user_id: int = Field(..., description="User ID")
    login_id: str = Field(..., description="User login identifier")
    role: str = Field(..., description="User role")


@dataclass
class ErrorResponse:
    """Response model for error responses."""
    error: str = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


@dataclass
class AuthToken:
    """Internal model for auth token data in database."""
    id: str  # UUID
    user_id: int  # BIGINT
    login_id: str
    token_jti: str  # JWT ID
    issued_at: datetime
    expires_at: datetime
    is_revoked: bool = False


@dataclass
class AuthAuditLog:
    """Internal model for audit log entries."""
    id: str  # UUID
    login_id: str
    action: str  # LOGIN_SUCCESS, LOGIN_FAILURE, TOKEN_REVOKED
    created_at: datetime
    user_id: Optional[int] = None  # BIGINT
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
