from .authentication_exception import AuthenticationException

class ServiceUnavailableException(AuthenticationException):
    """Raised when dependent service (User Service) is unavailable."""
    
    def __init__(self, message: str = "User service is unavailable"):
        super().__init__(message, status_code=503)
