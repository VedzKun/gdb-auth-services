"""
Audit Record Model
Module 2: Thinking in Objects
"""

# CR (M02-CR-01): Object-Oriented Audit Record Model
# TODO: Define a class `AuditRecord` that represents an audit entry.
# The class should:
# - Have attributes: `event_id` (str), `user_id` (str), `action` (str), `timestamp` (datetime), `status` (str).
# - Implement a constructor (`__init__`) initializing these attributes.
# - Provide a method `to_dict(self) -> dict` returning a dictionary representation of the object.
# - Provide a method `format_summary(self) -> str` returning a formatted log string.

# TODO: [M02-CR-01] FEATURE: Design this model class to represent an audit record with an appropriate constructor and methods.
from datetime import datetime
from typing import Dict, Any

class AuditRecord:
    """
    Class representing a single audit log event.
    """
    def __init__(self, event_id: str, user_id: str, action: str, status: str, timestamp: datetime = None):
        self.event_id = event_id
        self.user_id = user_id
        self.action = action
        self.status = status
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the audit record."""
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "action": self.action,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def format_summary(self) -> str:
        """Return a formatted log summary string."""
        ts_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "N/A"
        return f"[{ts_str}] Event: {self.event_id} | User: {self.user_id} | Action: {self.action} | Status: {self.status}"
