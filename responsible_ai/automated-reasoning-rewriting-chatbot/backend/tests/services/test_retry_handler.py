"""
Tests for the retry handler utility.
"""
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from backend.services.retry_handler import (
    is_transient_error,
    with_retry,
    retry_api_call,
    TRANSIENT_ERROR_CODES
)


class TestIsTransientError:
    """Tests for is_transient_error function."""
    
    def test_throttling_is_transient(self):
        assert is_transient_error("ThrottlingException") is True
    
    def test_service_unavailable_is_transient(self):
        assert is_transient_error("ServiceUnavailableException") is True
    
    def test_internal_server_is_transient(self):
        assert is_transient_error("InternalServerException") is True
    
    def test_request_timeout_is_transient(self):
        assert is_transient_error("RequestTimeout") is True
    
    def test_too_many_requests_is_transient(self):
        assert is_transient_error("TooManyRequestsException") is True
    
    def test_access_denied_is_not_transient(self):
        assert is_transient_error("AccessDeniedException") is False
    
    def test_validation_error_is_not_transient(self):
        assert is_transient_error("ValidationException") is False
    
    def test_empty_string_is_not_transient(self):
        assert is_transient_error("") is False


class TestRetryApiCall:
    """Tests for retry_api_call function."""
    
    def test_success_on_first_attempt(self):
        """Function succeeds on first try."""
        mock_func = Mock(return_value="success")
        
        result = retry_api_call(mock_func, max_retries=3)
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_success_after_transient_failure(self):
        """Function succeeds after transient error."""
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_func = Mock(side_effect=[
            ClientError(error_response, 'test_op'),
            "success"
        ])
        
        with patch('backend.services.retry_handler.time.sleep'):
            result = retry_api_call(mock_func, max_retries=3, base_delay=0.1)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_fails_after_max_retries(self):
        """Function fails after exhausting retries."""
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_func = Mock(side_effect=ClientError(error_response, 'test_op'))
        
        with patch('backend.services.retry_handler.time.sleep'):
            with pytest.raises(Exception) as exc_info:
                retry_api_call(mock_func, max_retries=3, base_delay=0.1)
        
        assert "Failed to" in str(exc_info.value)
        assert mock_func.call_count == 3
    
    def test_non_transient_error_fails_immediately(self):
        """Non-transient errors don't trigger retries."""
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_func = Mock(side_effect=ClientError(error_response, 'test_op'))
        
        with pytest.raises(Exception) as exc_info:
            retry_api_call(mock_func, max_retries=3)
        
        assert "Failed to" in str(exc_info.value)
        assert mock_func.call_count == 1
    
    def test_generic_exception_fails_immediately(self):
        """Generic exceptions don't trigger retries."""
        mock_func = Mock(side_effect=ValueError("Something went wrong"))
        
        with pytest.raises(Exception) as exc_info:
            retry_api_call(mock_func, max_retries=3)
        
        assert "Failed to" in str(exc_info.value)
        assert mock_func.call_count == 1
    
    def test_operation_name_in_error_message(self):
        """Operation name appears in error message."""
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_func = Mock(side_effect=ClientError(error_response, 'test_op'))
        
        with pytest.raises(Exception) as exc_info:
            retry_api_call(mock_func, operation_name="invoke model")
        
        assert "invoke model" in str(exc_info.value)
    
    def test_passes_args_and_kwargs(self):
        """Arguments are passed to the function."""
        mock_func = Mock(return_value="success")
        
        retry_api_call(mock_func, "arg1", "arg2", kwarg1="value1")
        
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""
    
    def test_decorated_function_succeeds(self):
        """Decorated function works normally."""
        @with_retry(max_retries=3)
        def my_func():
            return "success"
        
        assert my_func() == "success"
    
    def test_decorated_function_retries_on_transient_error(self):
        """Decorated function retries on transient errors."""
        call_count = 0
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        
        @with_retry(max_retries=3, base_delay=0.01)
        def my_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ClientError(error_response, 'test_op')
            return "success"
        
        with patch('backend.services.retry_handler.time.sleep'):
            result = my_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_decorated_function_preserves_name(self):
        """Decorator preserves function metadata."""
        @with_retry()
        def my_named_function():
            """My docstring."""
            pass
        
        assert my_named_function.__name__ == "my_named_function"
        assert my_named_function.__doc__ == "My docstring."
