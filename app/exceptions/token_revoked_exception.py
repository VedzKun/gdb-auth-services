from .authentication_exception import AuthenticationException

class TokenRevokedException(AuthenticationException):
    """Raised when JWT token has been revoked."""
    
    def __init__(self, message: str = "Token has been revoked"):
        super().__init__(message, status_code=401)
