from .authentication_exception import AuthenticationException

class TokenExpiredException(AuthenticationException):
    """Raised when JWT token is expired."""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, status_code=401)
