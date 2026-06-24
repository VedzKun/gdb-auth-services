"""
Authentication Service - Pytest Configuration

Fixtures and configuration for test suite.

Author: GDB Architecture Team
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """Configure async backend."""
    return "asyncio"


@pytest.fixture
def mock_user_data():
    """Mock user data from User Service."""
    import bcrypt
    password = "test_password_123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    return {
        "user_id": "12345678-1234-1234-1234-123456789012",
        "login_id": "john_doe",
        "password": hashed,
        "role": "CUSTOMER",
        "is_active": True,
    }


@pytest.fixture
def mock_inactive_user():
    """Mock inactive user data."""
    import bcrypt
    password = "test_password_123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    return {
        "user_id": "87654321-4321-4321-4321-210987654321",
        "login_id": "inactive_user",
        "password": hashed,
        "role": "CUSTOMER",
        "is_active": False,
    }


@pytest.fixture
def mock_admin_user():
    """Mock admin user data."""
    import bcrypt
    password = "admin_password_123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    return {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "login_id": "admin_user",
        "password": hashed,
        "role": "ADMIN",
        "is_active": True,
    }
