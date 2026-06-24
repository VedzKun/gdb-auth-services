from .authentication_exception import AuthenticationException

class InternalServerException(AuthenticationException):
    """Raised for unexpected internal errors."""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)
