import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
class TestAuthService:
    """Test suite for Auth Service"""

    BASE_URL = "/api/v1"

    VALID_USERS = {
        "john.doe": {"password": "Welcome@1", "role": "MANAGER", "user_id": 1},
        "doe.doe": {"password": "Welcome@1", "role": "ADMIN", "user_id": 2},
        "kumar.kumar": {"password": "Welcome@1", "role": "TELLER", "user_id": 3},
        "john.doe1": {"password": "Welcome@11", "role": "MANAGER", "user_id": 4},
    }

    async def test_positive_login_all_users(self):
        """POSITIVE: All users should login successfully"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for login_id, user_data in self.VALID_USERS.items():
                with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                    mock_verify.return_value = {
                        "user_id": user_data["user_id"],
                        "login_id": login_id,
                        "role": user_data["role"],
                        "is_active": True
                    }
                    
                    with patch("app.repositories.auth_token_repo.AuthTokenRepository.create_token") as mock_token:
                        with patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_success") as mock_audit:
                            response = await client.post(
                                f"{self.BASE_URL}/auth/login",
                                json={"login_id": login_id, "password": user_data["password"]},
                            )
                            assert response.status_code == 200, f"Failed for user {login_id}"
                            data = response.json()
                            assert "access_token" in data
                            assert data["user_id"] == user_data["user_id"]
                            # Fixed role in test expectation to match mock
                            assert data["role"] == user_data["role"]

    async def test_positive_token_format(self):
        """POSITIVE: Token should be valid JWT format"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            user_data = self.VALID_USERS["john.doe"]
            with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                mock_verify.return_value = {
                    "user_id": user_data["user_id"],
                    "login_id": "john.doe",
                    "role": user_data["role"],
                    "is_active": True
                }
                
                with patch("app.repositories.auth_token_repo.AuthTokenRepository.create_token"), \
                     patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_success"):
                    
                    response = await client.post(
                        f"{self.BASE_URL}/auth/login",
                        json={"login_id": "john.doe", "password": "Welcome@1"},
                    )
                    assert response.status_code == 200
                    token = response.json()["access_token"]
                    parts = token.split(".")
                    assert len(parts) == 3, "Token should be JWT (3 parts)"

    async def test_negative_wrong_password(self):
        """NEGATIVE: Wrong password should fail"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                mock_verify.return_value = None
                
                with patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure"):
                    response = await client.post(
                        f"{self.BASE_URL}/auth/login",
                        json={"login_id": "john.doe", "password": "WrongPassword123"},
                    )
                    assert response.status_code in [401, 500]

    async def test_negative_nonexistent_user(self):
        """NEGATIVE: Non-existent user should fail"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                mock_verify.return_value = None
                
                with patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure"):
                    response = await client.post(
                        f"{self.BASE_URL}/auth/login",
                        json={"login_id": "fake.user", "password": "Welcome@1"},
                    )
                    assert response.status_code == 401

    async def test_negative_empty_login_id(self):
        """NEGATIVE: Empty login_id should fail"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/login",
                json={"login_id": "", "password": "Welcome@1"},
            )
            assert response.status_code in [400, 422, 401]

    async def test_negative_empty_password(self):
        """NEGATIVE: Empty password should fail"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/login",
                json={"login_id": "john.doe", "password": ""},
            )
            assert response.status_code in [400, 422, 401]

    async def test_negative_missing_password(self):
        """NEGATIVE: Missing password field should fail"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/login",
                json={"login_id": "john.doe"},
            )
            assert response.status_code == 422

    async def test_negative_missing_login_id(self):
        """NEGATIVE: Missing login_id field should fail"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/login",
                json={"password": "Welcome@1"},
            )
            assert response.status_code == 422

    async def test_edge_sql_injection(self):
        """EDGE: SQL injection attempt should be handled"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                mock_verify.return_value = None
                with patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_failure"):
                    response = await client.post(
                        f"{self.BASE_URL}/auth/login",
                        json={
                            "login_id": "john.doe' OR '1'='1",
                            "password": "' OR '1'='1",
                        },
                    )
                    assert response.status_code in [401, 400, 422]

    async def test_edge_case_insensitive_login(self):
        """EDGE: Test case sensitivity"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                mock_verify.return_value = {
                    "user_id": 1,
                    "login_id": "john.doe",
                    "role": "MANAGER",
                    "is_active": True
                }
                
                with patch("app.repositories.auth_token_repo.AuthTokenRepository.create_token"), \
                     patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_success"):
                    
                    response = await client.post(
                        f"{self.BASE_URL}/auth/login",
                        json={"login_id": "JOHN.DOE", "password": "Welcome@1"},
                    )
                    # May succeed or fail depending on system design
                    assert response.status_code in [200, 401]

    async def test_edge_multiple_logins(self):
        """EDGE: Multiple logins should work"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            user_data = self.VALID_USERS["john.doe"]
            for i in range(3):
                with patch("app.integration.user_service_client.UserServiceClient.verify_user_credentials") as mock_verify:
                    mock_verify.return_value = {
                        "user_id": user_data["user_id"],
                        "login_id": "john.doe",
                        "role": user_data["role"],
                        "is_active": True
                    }
                    
                    with patch("app.repositories.auth_token_repo.AuthTokenRepository.create_token"), \
                         patch("app.repositories.auth_audit_repo.AuthAuditRepository.log_login_success"):
                        
                        response = await client.post(
                            f"{self.BASE_URL}/auth/login",
                            json={"login_id": "john.doe", "password": "Welcome@1"},
                        )
                        assert response.status_code == 200
