#!/usr/bin/env python3
"""
Authentication Service - Comprehensive Test Suite

Tests for:
- Successful login flow
- Invalid credentials
- Inactive users
- User not found
- Token verification
- Audit logging
- Error handling

Run: pytest tests/test_auth.py -v

Author: GDB Architecture Team
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC
from app.services.auth_service import AuthService
from app.security.jwt_utils import JWTUtil
from app.security.password_utils import PasswordUtil
from app.exceptions.auth_exceptions import (
    InvalidCredentialsException,
    UserInactiveException,
    UserNotFoundException,
    ServiceUnavailableException,
)


class TestJWTUtil:
    """Test JWT token generation and verification."""
    
    def test_generate_token(self):
        """Test JWT token generation."""
        token = JWTUtil.generate_token(
            user_id="12345678-1234-1234-1234-123456789012",
            login_id="john_doe",
            role="CUSTOMER",
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token should have 3 parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3
    
    def test_verify_token_valid(self):
        """Test JWT token verification with valid token."""
        # Generate token
        token = JWTUtil.generate_token(
            user_id="12345678-1234-1234-1234-123456789012",
            login_id="john_doe",
            role="CUSTOMER",
        )
        
        # Verify token
        claims = JWTUtil.verify_token(token)
        
        assert claims["sub"] == "12345678-1234-1234-1234-123456789012"
        assert claims["login_id"] == "john_doe"
        assert claims["role"] == "CUSTOMER"
        assert "iat" in claims
        assert "exp" in claims
        assert "jti" in claims
    
    def test_extract_claims(self):
        """Test claim extraction from token."""
        token = JWTUtil.generate_token(
            user_id="user-123",
            login_id="alice",
            role="ADMIN",
        )
        
        claims = JWTUtil.extract_claims(token)
        
        assert claims["sub"] == "user-123"
        assert claims["login_id"] == "alice"
        assert claims["role"] == "ADMIN"
    
    def test_get_user_id_from_token(self):
        """Test extracting user ID from token."""
        token = JWTUtil.generate_token(
            user_id="user-456",
            login_id="bob",
            role="TELLER",
        )
        
        user_id = JWTUtil.get_user_id(token)
        assert user_id == "user-456"
    
    def test_get_role_from_token(self):
        """Test extracting role from token."""
        token = JWTUtil.generate_token(
            user_id="user-789",
            login_id="charlie",
            role="TELLER",
        )
        
        role = JWTUtil.get_role(token)
        assert role == "TELLER"


class TestPasswordUtil:
    """Test password verification utilities."""
    
    def test_verify_valid_password(self):
        """Test verification of valid password."""
        # Create a bcrypt hash
        import bcrypt
        password = "test_password_123"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        # Verify should succeed
        is_valid = PasswordUtil.verify_password(password, hashed)
        assert is_valid is True
    
    def test_verify_invalid_password(self):
        """Test verification of invalid password."""
        import bcrypt
        password = "correct_password"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        # Verify with wrong password should fail
        is_valid = PasswordUtil.verify_password("wrong_password", hashed)
        assert is_valid is False
    
    def test_verify_empty_password(self):
        """Test verification with empty password."""
        import bcrypt
        hashed = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode("utf-8")
        
        is_valid = PasswordUtil.verify_password("", hashed)
        assert is_valid is False


class TestAuthService:
    """Test authentication service business logic."""
    
    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login flow."""
        # Mock User Service response
        with patch(
            "app.integration.user_service_client.UserServiceClient.verify_user_credentials",
            new_callable=AsyncMock,
            return_value={
                "user_id": "user-123",
                "login_id": "john_doe",
                "role": "CUSTOMER",
                "is_active": True,
            },
        ):
            with patch(
                "app.repositories.auth_token_repo.AuthTokenRepository.create_token",
                new_callable=AsyncMock,
                return_value="token-id-123",
            ):
                with patch(
                    "app.repositories.auth_audit_repo.AuthAuditRepository.log_login_success",
                    new_callable=AsyncMock,
                    return_value="audit-log-id",
                ):
                    result = await AuthService.login(
                        login_id="john_doe",
                        password="password123",
                        ip_address="127.0.0.1",
                        user_agent="Mozilla/5.0",
                    )
                    
                    assert result is not None
                    assert result["access_token"] is not None
                    assert result["token_type"] == "Bearer"
                    assert result["user_id"] == "user-123"
                    assert result["login_id"] == "john_doe"
                    assert result["role"] == "CUSTOMER"
                    assert result["expires_in"] > 0
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid password."""
        # When user service returns None (invalid credentials)
        with patch(
            "app.integration.user_service_client.UserServiceClient.verify_user_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure",
                new_callable=AsyncMock,
                return_value="audit-log-id",
            ):
                with pytest.raises(InvalidCredentialsException):
                    await AuthService.login(
                        login_id="john_doe",
                        password="wrong_password",
                    )
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        """Test login with non-existent user."""
        with patch(
            "app.integration.user_service_client.UserServiceClient.verify_user_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure",
                new_callable=AsyncMock,
                return_value="audit-log-id",
            ):
                with pytest.raises(InvalidCredentialsException):
                    await AuthService.login(
                        login_id="nonexistent_user",
                        password="password123",
                    )
    
    @pytest.mark.asyncio
    async def test_login_user_inactive(self):
        """Test login with inactive user."""
        with patch(
            "app.integration.user_service_client.UserServiceClient.verify_user_credentials",
            new_callable=AsyncMock,
            return_value={
                "user_id": "user-123",
                "login_id": "john_doe",
                "role": "CUSTOMER",
                "is_active": False,  # User is inactive
            },
        ):
            with patch(
                "app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure",
                new_callable=AsyncMock,
                return_value="audit-log-id",
            ):
                with pytest.raises(UserInactiveException):
                    await AuthService.login(
                        login_id="john_doe",
                        password="password123",
                    )
    
    @pytest.mark.asyncio
    async def test_login_user_service_unavailable(self):
        """Test login when User Service is unavailable."""
        with patch(
            "app.integration.user_service_client.UserServiceClient.verify_user_credentials",
            new_callable=AsyncMock,
            side_effect=ServiceUnavailableException("User service unavailable"),
        ):
            with patch(
                "app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure",
                new_callable=AsyncMock,
                return_value="audit-log-id",
            ):
                with pytest.raises(ServiceUnavailableException):
                    await AuthService.login(
                        login_id="john_doe",
                        password="password123",
                    )
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        """Test successful token verification."""
        # Generate a valid token
        token = JWTUtil.generate_token(
            user_id="user-123",
            login_id="john_doe",
            role="CUSTOMER",
        )
        
        with patch(
            "app.repositories.auth_token_repo.AuthTokenRepository.is_token_revoked",
            new_callable=AsyncMock,
            return_value=False,
        ):
            claims = await AuthService.verify_token(token)
            
            assert claims["sub"] == "user-123"
            assert claims["login_id"] == "john_doe"
            assert claims["role"] == "CUSTOMER"
    
    @pytest.mark.asyncio
    async def test_verify_revoked_token(self):
        """Test verification of revoked token."""
        token = JWTUtil.generate_token(
            user_id="user-123",
            login_id="john_doe",
            role="CUSTOMER",
        )
        
        with patch(
            "app.repositories.auth_token_repo.AuthTokenRepository.is_token_revoked",
            new_callable=AsyncMock,
            return_value=True,  # Token is revoked
        ):
            with pytest.raises(InvalidCredentialsException):
                await AuthService.verify_token(token)
    
    # Helper method
    @staticmethod
    def _get_bcrypt_hash(password: str) -> str:
        """Generate bcrypt hash for password."""
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class TestAuthEndpoints:
    """Test HTTP endpoints."""
    
    def test_login_endpoint_swagger_docs(self):
        """Test that login endpoint is documented in OpenAPI schema."""
        from app.main import app
        
        # Get OpenAPI schema
        openapi_schema = app.openapi()
        
        # Check that login endpoint exists
        assert "/api/v1/auth/login" in openapi_schema["paths"]
        
        # Check that POST method is documented
        path_item = openapi_schema["paths"]["/api/v1/auth/login"]
        assert "post" in path_item
        
        # Check operation details
        post_op = path_item["post"]
        assert post_op["summary"] is not None or post_op["description"] is not None
        assert "requestBody" in post_op
        assert "responses" in post_op


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
