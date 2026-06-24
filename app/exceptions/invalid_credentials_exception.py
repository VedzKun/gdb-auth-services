from .authentication_exception import AuthenticationException

class InvalidCredentialsException(AuthenticationException):
    """Raised when login credentials are invalid."""
    
    def __init__(self, message: str = "Invalid login credentials"):
        super().__init__(message, status_code=401)
