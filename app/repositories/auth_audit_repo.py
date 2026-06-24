"""
Authentication Audit Log Repository

Operations for auth_audit_logs table.
Records all authentication attempts for security auditing.

Author: GDB Architecture Team
"""

import uuid
import logging
from datetime import datetime, UTC
from typing import Optional, List
from app.database.db import db
from app.models.auth_models import AuthAuditLog
from app.exceptions.auth_exceptions import DatabaseException


logger = logging.getLogger(__name__)


class AuthAuditRepository:
    """Repository for auth_audit_logs table operations."""
    
    @staticmethod
    async def log_login_attempt(
        login_id: str,
        user_id: Optional[str],
        action: str,  # LOGIN_SUCCESS, LOGIN_FAILURE
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """
        Log a login attempt.
        
        Args:
            login_id: User login identifier (always available)
            user_id: User ID (integer from User Service; None if user not found)
            action: LOGIN_SUCCESS or LOGIN_FAILURE
            reason: Failure reason (e.g., "Invalid password", "User inactive")
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Audit log ID
        
        Raises:
            DatabaseException: If insertion fails
        """
        log_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        
        # Convert user_id to integer if provided
        user_id_int = None
        if user_id:
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id format for audit: {user_id}")
                user_id_int = None
        
        query = """
            INSERT INTO auth_audit_logs
            (id, login_id, user_id, action, reason, ip_address, user_agent, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        try:
            await db.execute(
                query,
                log_id,
                login_id,
                user_id_int,
                action,
                reason,
                ip_address,
                user_agent,
                now,
            )
            logger.info(
                f"Audit: {action} for {login_id} "
                f"(user_id: {user_id}) from {ip_address}"
            )
            return log_id
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            raise DatabaseException(f"Failed to create audit log: {str(e)}")
    
    @staticmethod
    async def log_login_success(
        login_id: str,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """
        Log successful login.
        
        Args:
            login_id: User login identifier
            user_id: User UUID
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Audit log ID
        
        Raises:
            DatabaseException: If insertion fails
        """
        return await AuthAuditRepository.log_login_attempt(
            login_id=login_id,
            user_id=user_id,
            action="LOGIN_SUCCESS",
            reason=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    @staticmethod
    async def log_login_failure(
        login_id: str,
        user_id: Optional[str],
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """
        Log failed login attempt.
        
        Args:
            login_id: User login identifier
            user_id: User UUID (None if user not found)
            reason: Failure reason (Invalid password, User inactive, etc)
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Audit log ID
        
        Raises:
            DatabaseException: If insertion fails
        """
        return await AuthAuditRepository.log_login_attempt(
            login_id=login_id,
            user_id=user_id,
            action="LOGIN_FAILURE",
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    @staticmethod
    async def get_audit_log(log_id: str) -> Optional[AuthAuditLog]:
        """
        Retrieve audit log entry by ID.
        
        Args:
            log_id: Audit log UUID
        
        Returns:
            AuthAuditLog object or None if not found
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT id, login_id, user_id, action, reason, ip_address, user_agent, created_at
            FROM auth_audit_logs
            WHERE id = $1
        """
        
        try:
            row = await db.fetchrow(query, log_id)
            if row:
                return AuthAuditLog(
                    id=row["id"],
                    login_id=row["login_id"],
                    user_id=row["user_id"],
                    action=row["action"],
                    reason=row["reason"],
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    created_at=row["created_at"],
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get audit log: {str(e)}")
            raise DatabaseException(f"Failed to get audit log: {str(e)}")
    
    @staticmethod
    async def get_user_audit_logs(
        user_id: str,
        limit: int = 100,
    ) -> List[AuthAuditLog]:
        """
        Get recent audit logs for a user.
        
        Args:
            user_id: User UUID
            limit: Maximum number of logs to return
        
        Returns:
            List of AuthAuditLog objects
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT id, login_id, user_id, action, reason, ip_address, user_agent, created_at
            FROM auth_audit_logs
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        try:
            rows = await db.fetch(query, user_id, limit)
            logs = []
            for row in rows:
                logs.append(
                    AuthAuditLog(
                        id=row["id"],
                        login_id=row["login_id"],
                        user_id=row["user_id"],
                        action=row["action"],
                        reason=row["reason"],
                        ip_address=row["ip_address"],
                        user_agent=row["user_agent"],
                        created_at=row["created_at"],
                    )
                )
            return logs
        except Exception as e:
            logger.error(f"Failed to get user audit logs: {str(e)}")
            raise DatabaseException(f"Failed to get audit logs: {str(e)}")
    
    @staticmethod
    async def get_login_id_audit_logs(
        login_id: str,
        limit: int = 100,
    ) -> List[AuthAuditLog]:
        """
        Get recent audit logs for a login ID (includes failed attempts before user lookup).
        
        Args:
            login_id: User login identifier
            limit: Maximum number of logs to return
        
        Returns:
            List of AuthAuditLog objects
        
        Raises:
            DatabaseException: If query fails
        """
        query = """
            SELECT id, login_id, user_id, action, reason, ip_address, user_agent, created_at
            FROM auth_audit_logs
            WHERE login_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        try:
            rows = await db.fetch(query, login_id, limit)
            logs = []
            for row in rows:
                logs.append(
                    AuthAuditLog(
                        id=row["id"],
                        login_id=row["login_id"],
                        user_id=row["user_id"],
                        action=row["action"],
                        reason=row["reason"],
                        ip_address=row["ip_address"],
                        user_agent=row["user_agent"],
                        created_at=row["created_at"],
                    )
                )
            return logs
        except Exception as e:
            logger.error(f"Failed to get login_id audit logs: {str(e)}")
            raise DatabaseException(f"Failed to get audit logs: {str(e)}")
