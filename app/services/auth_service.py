"""
Authentication Service - Business Logic

Handles the complete login workflow:
1. Call User Service to verify credentials (login_id + password)
2. Check if user is active
3. Generate JWT token
4. Store token in auth_tokens table
5. Log audit event

Author: GDB Architecture Team
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from app.security.jwt_utils import JWTUtil
from app.integration.user_service_client import UserServiceClient
from app.repositories.auth_token_repo import AuthTokenRepository
from app.repositories.auth_audit_repo import AuthAuditRepository
from app.exceptions.auth_exceptions import (
    InvalidCredentialsException,
    UserInactiveException,
    UserNotFoundException,
    ServiceUnavailableException,
)


logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service business logic."""
    
    @staticmethod
    async def login(
        login_id: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user and generate JWT token.
        
        Process:
        1. Call User Service to verify credentials (login_id + password)
        2. Verify user is active
        3. Generate JWT token with claims (sub, login_id, role, iat, exp, jti)
        4. Store token record in auth_tokens table
        5. Log successful login
        
        Args:
            login_id: User login identifier
            password: User password
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit
        
        Returns:
            Dict with keys:
            {
                'access_token': str (JWT token),
                'token_type': 'Bearer',
                'expires_in': int (seconds),
                'user_id': str (UUID),
                'login_id': str,
                'role': str (ADMIN, TELLER, MANAGER)
            }
        
        Raises:
            UserNotFoundException: If user not found
            UserInactiveException: If user account is inactive
            InvalidCredentialsException: If password is wrong
            ServiceUnavailableException: If User Service is unreachable
        """
        
        # Step 1: Verify credentials with User Service
        try:
            user_data = await UserServiceClient.verify_user_credentials(
                login_id=login_id,
                password=password,
            )
        except ServiceUnavailableException:
            # Log failure before raising
            await AuthAuditRepository.log_login_failure(
                login_id=login_id,
                user_id=None,
                reason="User service unavailable",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise
        
        # Step 2: Check if credentials are valid
        if not user_data:
            logger.warning("Invalid credentals provided.")
            # Bug (M02-Bug-01): Faulty Object instantiation (AttributeError)
            # Setting an attribute on a basic object() instance is invalid in Python.
            # TODO: [M02-Bug-01] BUG: The application crashes with an error when invalid credentials are provided. Review the dummy event object creation.
            # audit_event = object()
            # audit_event.user_id = None  # Raises AttributeError: 'object' object has no attribute 'user_id'
            
            await AuthAuditRepository.log_login_failure(login_id=login_id, user_id=None, reason="user not found", ip_address=ip_address, user_agent=user_agent)
            raise InvalidCredentialsException("Invalid login credentials")
        
        user_id = user_data.get("user_id")
        is_active = user_data.get("is_active", False)
        role = user_data.get("role")
        
        # Step 3: Verify user is active
        if not is_active:
            logger.warning(f"Login attempt by inactive user: {login_id}")
            await AuthAuditRepository.log_login_failure(
                login_id=login_id,
                user_id=user_id,
                reason="User inactive",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise UserInactiveException("User account is inactive")
        
        # Step 4: Generate JWT token
        try:
            token = JWTUtil.generate_token(
                user_id=user_id,
                login_id=login_id,
                role=role,
            )
        except Exception as e:
            logger.error(f"Failed to generate token for {login_id}: {str(e)}")
            await AuthAuditRepository.log_login_failure(
                login_id=login_id,
                user_id=user_id,
                reason="Token generation failed",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise
        
        # Extract token claims for storage
        claims = JWTUtil.extract_claims(token)
        token_jti = claims.get("jti")
        iat = claims.get("iat")
        exp = claims.get("exp")
        
        # Step 5: Store token record
        try:
            issued_at = datetime.fromtimestamp(iat, tz=UTC)
            expires_at = datetime.fromtimestamp(exp, tz=UTC)
            
            await AuthTokenRepository.create_token(
                user_id=user_id,
                login_id=login_id,
                token_jti=token_jti,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        except Exception as e:
            logger.error(f"Failed to store token for {login_id}: {str(e)}")
            # Don't fail the login, but log it
        
        # Step 6: Log successful login
        try:
            await AuthAuditRepository.log_login_success(
                login_id=login_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"Failed to log login success for {login_id}: {str(e)}")
            # Don't fail the login due to audit logging failure
        
        logger.info(f"Successful login for user: {login_id}")
        
        # Return token response
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": exp - iat,  # seconds
            "user_id": user_id,
            "login_id": login_id,
            "role": role,
        }
    
    @staticmethod
    async def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify JWT token validity.
        
        Args:
            token: JWT token
        
        Returns:
            Token claims dict
        
        Raises:
            InvalidCredentialsException: If token is invalid or revoked
            TokenExpiredException: If token is expired
        """
        try:
            claims = JWTUtil.verify_token(token)
        except Exception as e:
            raise InvalidCredentialsException(f"Invalid token: {str(e)}")
        
        # Check if token is revoked
        token_jti = claims.get("jti")
        try:
            is_revoked = await AuthTokenRepository.is_token_revoked(token_jti)
            if is_revoked:
                raise InvalidCredentialsException("Token has been revoked")
        except InvalidCredentialsException:
            raise
        except Exception as e:
            logger.error(f"Failed to check token revocation: {str(e)}")
            # Don't fail verification due to DB error
        
        return claims

    @staticmethod
    async def logout(token: str) -> bool:
        """
        Logout user by revoking the token.
        
        Args:
            token: JWT token to revoke
        
        Returns:
            True if logout successful
        """
        try:
            claims = JWTUtil.extract_claims(token)
            token_jti = claims.get("jti")
            login_id = claims.get("login_id")
            
            # Revoke the token
            if token_jti:
                await AuthTokenRepository.revoke_token(token_jti)
                logger.info(f"Token revoked for user: {login_id}")
            
            return True
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return True  # Return success anyway - frontend will clear local storage
