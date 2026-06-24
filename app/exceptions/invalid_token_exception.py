from .authentication_exception import AuthenticationException

class InvalidTokenException(AuthenticationException):
    """Raised when JWT token is invalid."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, status_code=401)
