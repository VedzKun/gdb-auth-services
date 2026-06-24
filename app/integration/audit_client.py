"""
Audit Service REST Client Wrapper
Module 11: JSON & REST API
"""

import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# CR (M11-CR-01): REST Client Audit Helper
# TODO: Implement an HTTP client call to post audit records.
# - Write a method `async def send_audit_event(action: str, details: Dict[str, Any]) -> bool`.
# - Use `httpx.AsyncClient()` to make a POST request with JSON payload.
# - The target URL should be from settings (e.g. users-service or notification-service audit endpoints).
# - Implement proper try-except block for httpx.HTTPError and verify status code == 200.

# TODO: [M11-CR-01] FEATURE: Implement a helper method to send an HTTP POST payload for audit events, handling HTTP errors.
class AuditClient:
    """
    HTTP client wrapper for transmitting audit events.
    """
    
    def __init__(self, service_url: str):
        self.service_url = service_url

    async def send_audit_event(self, action: str, details: Dict[str, Any]) -> bool:
        """
        Post an audit event to the notification/audit service URL.
        """
        payload = {
            "action": action,
            "details": details
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.service_url}/api/v1/audit", json=payload)
                if response.status_code == 200:
                    return True
                logger.warning(f"Audit event dispatch failed with status: {response.status_code}")
                return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending audit event: {e}")
            return False
