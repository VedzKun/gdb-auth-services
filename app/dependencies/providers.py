from fastapi import Depends
from app.services.auth_service import AuthService

def get_auth_service() -> AuthService:
    """Provider for AuthService."""
    return AuthService()
