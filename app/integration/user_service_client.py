"""
User Service Client

Makes HTTP calls to User Service internal APIs.
Auth Service uses User Service as the sole source of truth for user credentials.

One-way communication: Auth Service → User Service ONLY

User Service Internal APIs:
  - POST /internal/v1/users/verify - Verify user credentials
  - GET /internal/v1/users/{login_id}/status - Get user status
  - GET /internal/v1/users/{login_id}/role - Get user role

Author: GDB Architecture Team
"""

import httpx
import logging
from typing import Optional, Dict, Any
from app.config.settings import settings
from app.exceptions.auth_exceptions import ServiceUnavailableException


logger = logging.getLogger(__name__)


class UserServiceClient:
    """HTTP client for User Service communication."""
    
    @staticmethod
    async def verify_user_credentials(login_id: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verify user credentials by calling User Service.
        """
        url = f"{settings.USERS_SERVICE_URL}/internal/v1/users/verify"
        
        try:
            payload = {
                "login_id": login_id,
                "password": password,
            }
            async with httpx.AsyncClient(timeout=settings.USER_SERVICE_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Verified credentials for user {login_id}")
                    return data
                elif response.status_code == 401:
                    logger.warning(f"Invalid credentials for user {login_id}")
                    return None
                elif response.status_code == 404:
                    logger.warning(f"User {login_id} not found")
                    return None
                else:
                    logger.error(f"User Service error: HTTP {response.status_code}")
                    raise ServiceUnavailableException("User service returned error")

        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to User Service: {str(e)}")
            raise ServiceUnavailableException(f"User service unavailable")
    
    @staticmethod
    async def get_user_status(login_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user status from User Service.
        """
        url = f"{settings.USERS_SERVICE_URL}/internal/v1/users/{login_id}/status"
        
        try:
            async with httpx.AsyncClient(timeout=settings.USER_SERVICE_TIMEOUT) as client:
                response = await client.get(url)
                
                # Bug (M11-Bug-01): Unchecked API response status code in requests.
                # Direct JSON parsing without status code checking returns error payloads as valid data.
                # TODO: [M11-Bug-01] BUG: When a user doesn't exist, we return empty records instead of failing properly. Are we checking the HTTP result?
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return data
        except httpx.HTTPError:
            raise ServiceUnavailableException()
    
    @staticmethod
    async def get_user_role(login_id: str) -> Optional[str]:
        """
        Get user role from User Service.
        """
        url = f"{settings.USERS_SERVICE_URL}/internal/v1/users/{login_id}/role"
        
        try:
            async with httpx.AsyncClient(timeout=settings.USER_SERVICE_TIMEOUT) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    role = data.get("role")
                    logger.info(f"Retrieved role for user {login_id}: {role}")
                    return role
                elif response.status_code == 404:
                    logger.warning(f"User {login_id} not found")
                    return None
                else:
                    logger.error(f"User Service error: HTTP {response.status_code}")
                    raise ServiceUnavailableException()
        except httpx.HTTPError:
            raise ServiceUnavailableException()
