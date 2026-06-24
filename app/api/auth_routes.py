"""
Authentication API Routes

Single public endpoint for user login.
All other services handle their own authorization using tokens.

Author: GDB Architecture Team
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from app.models.auth_models import LoginRequest, TokenResponse, ErrorResponse
from app.services.auth_service import AuthService
from app.dependencies.providers import get_auth_service
from app.exceptions.auth_exceptions import (
    AuthenticationException,
    InvalidCredentialsException,
    UserInactiveException,
    UserNotFoundException,
    ServiceUnavailableException,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> str:
    """Extract user agent from request."""
    return request.headers.get("user-agent", "")


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=200,
)
async def login(
    request: Request,
    login_request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    logger.info(f"Login attempt for {login_request.login_id} from {ip_address}")
    
    try:
        token_data = await auth_service.login(
            login_id=login_request.login_id,
            password=login_request.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user_id=token_data["user_id"],
            login_id=token_data["login_id"],
            role=token_data["role"],
        )
    
    except UserNotFoundException as e:
        logger.warning(f"Login failed - user not found: {login_request.login_id}")
        raise HTTPException(status_code=404, detail={"error": "user_not_found", "message": e.message})
    
    except UserInactiveException as e:
        logger.warning(f"Login failed - user inactive: {login_request.login_id}")
        raise HTTPException(status_code=401, detail={"error": "user_inactive", "message": e.message})
    
    except InvalidCredentialsException as e:
        logger.warning(f"Login failed - invalid credentials: {login_request.login_id}")
        raise HTTPException(status_code=401, detail={"error": "invalid_credentials", "message": e.message})
    
    except ServiceUnavailableException as e:
        logger.error(f"Login failed - user service unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail={"error": "service_unavailable", "message": "User service is unavailable"})
    
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": "internal_server_error", "message": "An unexpected error occurred"})


@router.get(
    "/health",
    status_code=200,
)
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "auth-service",
    }


# ============================================
# NEW ENDPOINTS - Added to match Frontend API
# ============================================

@router.get(
    "/verify",
    status_code=200,
)
async def verify_token(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Verify JWT token and return user information.
    Frontend uses this to validate session on page refresh.
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": "Missing or invalid token"})
        
        token = auth_header.replace("Bearer ", "")
        
        # Verify token and get claims
        claims = await auth_service.verify_token(token)
        
        return {
            "valid": True,
            "user_id": claims.get("user_id"),
            "login_id": claims.get("login_id"),
            "role": claims.get("role"),
        }
    
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": "Token verification failed"})


@router.post(
    "/logout",
    status_code=200,
)
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Logout user and invalidate token.
    Frontend calls this to clear server-side session.
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            # Optionally blacklist the token (if implemented)
            await auth_service.logout(token)
        
        logger.info("User logged out successfully")
        return {"status": "success", "message": "Logged out successfully"}
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Still return success - frontend will clear local storage anyway
        return {"status": "success", "message": "Logged out"}


@router.post(
    "/register",
    status_code=201,
)
async def register(
    request: Request,
    # Note: Registration is typically handled by Users Service
    # This endpoint redirects or provides info
) -> dict:
    """
    Register endpoint - redirects to Users Service.
    In GDB architecture, user creation is done via Users Service by ADMIN.
    """
    raise HTTPException(
        status_code=403, 
        detail={
            "error": "registration_not_allowed",
            "message": "User registration is managed by administrators. Please contact your admin to create an account."
        }
    )
