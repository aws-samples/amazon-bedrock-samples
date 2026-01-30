"""
Custom exceptions for the Flask application.

These exceptions are caught by Flask error handlers and converted to
standardized JSON error responses.
"""


class APIException(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: str = None):
        """
        Initialize API exception.
        
        Args:
            message: Human-readable error message
            code: Error code for client identification
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or message


class BadRequestError(APIException):
    """Exception for 400 Bad Request errors."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=400,
            details=details
        )


class NotFoundError(APIException):
    """Exception for 404 Not Found errors."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details
        )


class ConflictError(APIException):
    """Exception for 409 Conflict errors."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(
            message=message,
            code="INVALID_STATE",
            status_code=409,
            details=details
        )


class ConfigError(APIException):
    """Exception for configuration-related errors."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            status_code=400,
            details=details
        )


class ServiceUnavailableError(APIException):
    """Exception for 503 Service Unavailable errors."""
    
    def __init__(self, message: str, details: str = None):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=503,
            details=details
        )
