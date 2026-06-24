from .authentication_exception import AuthenticationException

class UserInactiveException(AuthenticationException):
    """Raised when user account is inactive."""
    
    def __init__(self, message: str = "User account is inactive"):
        super().__init__(message, status_code=403)
