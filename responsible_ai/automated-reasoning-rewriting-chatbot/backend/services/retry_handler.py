"""
Retry handler for AWS API calls with exponential backoff.

This module provides a centralized retry mechanism for handling transient
AWS API failures across all services.
"""
import time
import logging
from typing import Callable, TypeVar, Set
from functools import wraps
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

T = TypeVar('T')

# AWS error codes that represent transient failures
TRANSIENT_ERROR_CODES: Set[str] = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
    "RequestTimeout",
    "TooManyRequestsException"
}


def is_transient_error(error_code: str) -> bool:
    """
    Determine if an error code represents a transient failure.
    
    Args:
        error_code: The AWS error code
        
    Returns:
        True if the error is transient and should be retried
    """
    return error_code in TRANSIENT_ERROR_CODES


def _execute_with_retry(
    func: Callable[..., T],
    args: tuple,
    kwargs: dict,
    max_retries: int,
    base_delay: float,
    operation_name: str
) -> T:
    """
    Core retry logic shared by decorator and standalone function.
    
    Args:
        func: The function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        max_retries: Maximum retry attempts
        base_delay: Base delay for exponential backoff
        operation_name: Name for logging
        
    Returns:
        The function's return value
        
    Raises:
        Exception: If all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            last_exception = e
            
            if is_transient_error(error_code) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Transient error on attempt {attempt + 1}/{max_retries}: {error_code}. "
                    f"Retrying {operation_name} in {delay}s..."
                )
                time.sleep(delay)
                continue
            
            raise Exception(f"Failed to {operation_name}: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to {operation_name}: {str(e)}")
    
    if last_exception:
        raise Exception(f"Failed to {operation_name} after {max_retries} retries")
    raise Exception(f"Failed to {operation_name} after all retries")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    operation_name: str = "API call"
) -> Callable:
    """
    Decorator for retrying AWS API calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        operation_name: Name of the operation for logging (default: "API call")
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @with_retry(max_retries=3, operation_name="generate response")
        def call_bedrock(self, prompt):
            return self.client.invoke_model(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return _execute_with_retry(func, args, kwargs, max_retries, base_delay, operation_name)
        return wrapper
    return decorator


def retry_api_call(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    operation_name: str = "API call",
    **kwargs
) -> T:
    """
    Execute a function with retry logic for AWS API calls.
    
    This is a functional alternative to the decorator for cases where
    decoration isn't practical.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        operation_name: Name of the operation for logging (default: "API call")
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The return value of the function
        
    Raises:
        Exception: If the function fails after all retries
    """
    return _execute_with_retry(func, args, kwargs, max_retries, base_delay, operation_name)
