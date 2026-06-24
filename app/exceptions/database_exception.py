from .authentication_exception import AuthenticationException

class DatabaseException(AuthenticationException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=500)
