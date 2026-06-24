"""
Password Verification Utilities

Handles bcrypt password verification ONLY.
Password hashing is handled by User Service.

This service receives bcrypt-hashed passwords from User Service
and verifies login credentials against them.

Author: GDB Architecture Team
"""

import bcrypt
from typing import Optional


class PasswordUtil:
    """Password verification utilities using bcrypt."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify plain password against bcrypt hash.
        
        Args:
            plain_password: Plain text password entered by user
            hashed_password: Bcrypt hash from User Service database
        
        Returns:
            True if password matches hash, False otherwise
        
        Raises:
            ValueError: If password or hash is invalid
        """
        if not plain_password or not hashed_password:
            return False
        
        try:
            # bcrypt.checkpw expects bytes
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Password verification failed: {str(e)}")
    
    @staticmethod
    def is_valid_password_format(password: str) -> bool:
        """
        Check if password has minimum valid format.
        
        Args:
            password: Password to validate
        
        Returns:
            True if password is at least 1 character
        """
        return password is not None and len(password) >= 1
