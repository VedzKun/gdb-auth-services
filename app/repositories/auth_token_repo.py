"""
Authentication Token Repository

CRUD operations for auth_tokens table.
Handles token storage, retrieval, and revocation.

Author: GDB Architecture Team
"""

import uuid
import logging
from datetime import datetime, UTC
from typing import Optional
from app.database.db import db
from app.models.auth_models import AuthToken
from app.exceptions.auth_exceptions import DatabaseException


logger = logging.getLogger(__name__)


class AuthTokenRepository:
    """Repository for auth_tokens table operations."""
    
    @staticmethod
    async def create_token(
        user_id: str,
        login_id: str,
        token_jti: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> str:
        """
        Create new token record in database.
        
        Args:
            user_id: User ID (integer from User Service)
            login_id: User login identifier
            token_jti: JWT ID (unique identifier from JWT token)
            issued_at: Token issue timestamp
            expires_at: Token expiry timestamp
        
        Returns:
            Token ID (UUID)
        
        Raises:
            DatabaseException: If insertion fails
        """
        token_id = str(uuid.uuid4())
        
        # Convert user_id to integer for BIGINT storage
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            raise DatabaseException(f"Invalid user_id format: {user_id}")
        
        query = """
            INSERT INTO auth_tokens
            (id, user_id, login_id, token_jti, issued_at, expires_at, is_revoked)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        try:
            await db.execute(
                query,
                token_id,
                user_id_int,
                login_id,
                token_jti,
                issued_at,
                expires_at,
                False,  # is_revoked
            )
            logger.info(f"Created auth token {token_id} for user {user_id}")
            return token_id
        except Exception as e:
            logger.error(f"Failed to create token: {str(e)}")
            raise DatabaseException(f"Failed to create token: {str(e)}")
    
    @staticmethod
    async def get_token_by_jti(token_jti: str) -> Optional[AuthToken]:
        """
        Retrieve token by JWT ID.
        
        Args:
            token_jti: JWT ID
        
        Returns:
            AuthToken object or None if not found
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT id, user_id, login_id, token_jti, issued_at, expires_at, is_revoked
            FROM auth_tokens
            WHERE token_jti = $1
        """
        
        try:
            row = await db.fetchrow(query, token_jti)
            if row:
                return AuthToken(
                    id=row["id"],
                    user_id=row["user_id"],
                    login_id=row["login_id"],
                    token_jti=row["token_jti"],
                    issued_at=row["issued_at"],
                    expires_at=row["expires_at"],
                    is_revoked=row["is_revoked"],
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get token by JTI: {str(e)}")
            raise DatabaseException(f"Failed to get token: {str(e)}")
    
    @staticmethod
    async def get_token_by_id(token_id: str) -> Optional[AuthToken]:
        """
        Retrieve token by token ID.
        
        Args:
            token_id: Token UUID
        
        Returns:
            AuthToken object or None if not found
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT id, user_id, login_id, token_jti, issued_at, expires_at, is_revoked
            FROM auth_tokens
            WHERE id = $1
        """
        
        try:
            row = await db.fetchrow(query, token_id)
            if row:
                return AuthToken(
                    id=row["id"],
                    user_id=row["user_id"],
                    login_id=row["login_id"],
                    token_jti=row["token_jti"],
                    issued_at=row["issued_at"],
                    expires_at=row["expires_at"],
                    is_revoked=row["is_revoked"],
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get token by ID: {str(e)}")
            raise DatabaseException(f"Failed to get token: {str(e)}")
    
    @staticmethod
    async def revoke_token(token_jti: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token_jti: JWT ID
        
        Returns:
            True if token was revoked, False if token not found
        
        Raises:
            DatabaseException: If update fails
        """
        query = """
            UPDATE auth_tokens
            SET is_revoked = TRUE
            WHERE token_jti = $1
        """
        
        try:
            await db.execute(query, token_jti)
            logger.info(f"Revoked token {token_jti}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {str(e)}")
            raise DatabaseException(f"Failed to revoke token: {str(e)}")
    
    @staticmethod
    async def is_token_revoked(token_jti: str) -> bool:
        """
        Check if token is revoked.
        
        Args:
            token_jti: JWT ID
        
        Returns:
            True if token is revoked, False otherwise
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT is_revoked FROM auth_tokens WHERE token_jti = $1
        """
        
        try:
            is_revoked = await db.fetchval(query, token_jti)
            return is_revoked is True
        except Exception as e:
            logger.error(f"Failed to check if token is revoked: {str(e)}")
            raise DatabaseException(f"Failed to check token status: {str(e)}")
    
    @staticmethod
    async def get_user_tokens(user_id: str) -> list:
        """
        Get all tokens for a user.
        
        Args:
            user_id: User UUID
        
        Returns:
            List of AuthToken objects
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT id, user_id, login_id, token_jti, issued_at, expires_at, is_revoked
            FROM auth_tokens
            WHERE user_id = $1
            ORDER BY issued_at DESC
        """
        
        try:
            rows = await db.fetch(query, user_id)
            tokens = []
            for row in rows:
                tokens.append(
                    AuthToken(
                        id=row["id"],
                        user_id=row["user_id"],
                        login_id=row["login_id"],
                        token_jti=row["token_jti"],
                        issued_at=row["issued_at"],
                        expires_at=row["expires_at"],
                        is_revoked=row["is_revoked"],
                    )
                )
            return tokens
        except Exception as e:
            logger.error(f"Failed to get user tokens: {str(e)}")
            raise DatabaseException(f"Failed to get tokens: {str(e)}")
