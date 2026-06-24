"""
JWT Token Management Utilities

Handles token generation, validation, and claim extraction.
Uses HS256 (HMAC SHA-256) for signing and verification.

JWT Claims:
  - sub: User ID (subject)
  - login_id: Login identifier
  - role: User role (ADMIN, TELLER, MANAGER)
  - iat: Issued at timestamp
  - exp: Expiry timestamp
  - jti: JWT ID (unique token identifier)

Author: GDB Architecture Team
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, Any
import jwt
from app.config.settings import settings


class JWTUtil:
    """JWT token generation and validation utilities."""
    
    @staticmethod
    def generate_token(
        user_id: str,
        login_id: str,
        role: str,
    ) -> str:
        """
        Generate a new JWT token with standard claims.
        
        Args:
            user_id: Unique user identifier (UUID)
            login_id: User login identifier (e.g., "john_doe")
            role: User role (ADMIN, TELLER, MANAGER)
        
        Returns:
            Encoded JWT token as string
        
        Raises:
            Exception: If token generation fails
        """
        now = datetime.now(UTC)
        expiry = now + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
        
        # Build JWT claims
        claims = {
            "sub": str(user_id),  # User ID as subject
            "login_id": login_id,  # Login identifier
            "role": role,  # User role for authorization
            "iat": int(now.timestamp()),  # Issued at
            "exp": int(expiry.timestamp()),  # Expiry time
            "jti": str(uuid.uuid4()),  # Unique token ID
        }
        
        try:
            token = jwt.encode(
                claims,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
            )
            return token
        except Exception as e:
            raise Exception(f"Failed to generate JWT token: {str(e)}")
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify JWT token signature and expiry.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            Decoded claims dictionary
        
        Raises:
            jwt.InvalidTokenError: If signature is invalid
            jwt.ExpiredSignatureError: If token is expired
            jwt.DecodeError: If token format is invalid
        """
        try:
            claims = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return claims
        except jwt.ExpiredSignatureError as e:
            raise jwt.ExpiredSignatureError(f"Token has expired: {str(e)}")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise jwt.DecodeError(f"Failed to decode token: {str(e)}")
    
    @staticmethod
    def extract_claims(token: str) -> Optional[Dict[str, Any]]:
        """
        Extract and decode JWT claims without validation (for debugging).
        
        WARNING: This does NOT verify signature or expiry.
        Use only for logging/debugging purposes.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            Decoded claims or None if decode fails
        """
        try:
            claims = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_signature": False},
            )
            return claims
        except Exception:
            return None
    
    @staticmethod
    def get_expiry_datetime(token: str) -> Optional[datetime]:
        """
        Extract expiry datetime from JWT token.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            Expiry datetime or None if token is invalid
        """
        claims = JWTUtil.extract_claims(token)
        if claims and "exp" in claims:
            return datetime.fromtimestamp(claims["exp"], tz=UTC)
        return None
    
    @staticmethod
    def get_user_id(token: str) -> Optional[str]:
        """
        Extract user ID (sub) from JWT token.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            User ID or None if token is invalid
        """
        claims = JWTUtil.extract_claims(token)
        if claims:
            return claims.get("sub")
        return None
    
    @staticmethod
    def get_login_id(token: str) -> Optional[str]:
        """
        Extract login_id from JWT token.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            Login ID or None if token is invalid
        """
        claims = JWTUtil.extract_claims(token)
        if claims:
            return claims.get("login_id")
        return None
    
    @staticmethod
    def get_role(token: str) -> Optional[str]:
        """
        Extract role from JWT token.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            Role (ADMIN, TELLER, MANAGER) or None if token is invalid
        """
        claims = JWTUtil.extract_claims(token)
        if claims:
            return claims.get("role")
        return None
    
    @staticmethod
    def is_token_expired(token: str) -> bool:
        """
        Check if JWT token is expired.
        
        Args:
            token: Encoded JWT token
        
        Returns:
            True if token is expired, False otherwise
        """
        expiry = JWTUtil.get_expiry_datetime(token)
        if expiry:
            return datetime.now(UTC) > expiry
        return True  # Invalid token is considered expired
