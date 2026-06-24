from .authentication_exception import AuthenticationException

class UserNotFoundException(AuthenticationException):
    """Raised when user does not exist."""
    
    def __init__(self, message: str = "User not found"):
        super().__init__(message, status_code=404)
