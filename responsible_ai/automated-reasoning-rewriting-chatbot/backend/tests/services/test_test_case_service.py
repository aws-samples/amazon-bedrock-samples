"""
Unit tests for TestCaseService.
"""
import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

from backend.services.test_case_service import TestCaseService


class TestTestCaseService:
    """Test suite for TestCaseService."""
    
    def test_validate_policy_arn_valid(self):
        """Test that valid policy ARNs pass validation."""
        service = TestCaseService()
        
        # Should not raise any exception
        valid_arns = [
            "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/my-policy",
            "arn:aws:bedrock:us-east-1:999999999999:automated-reasoning-policy/test-policy-123",
        ]
        
        for arn in valid_arns:
            service._validate_policy_arn(arn)  # Should not raise
    
    def test_validate_policy_arn_empty(self):
        """Test that empty policy ARN raises ValueError."""
        service = TestCaseService()
        
        with pytest.raises(ValueError, match="policy_arn cannot be empty"):
            service._validate_policy_arn("")
    
    def test_validate_policy_arn_invalid_format(self):
        """Test that invalid policy ARN format raises ValueError."""
        service = TestCaseService()
        
        invalid_arns = [
            "not-an-arn",
            "arn:aws:s3:::bucket/key",
            "arn:aws:bedrock:us-west-2:123456789012:policy/my-policy",  # Wrong resource type
        ]
        
        for arn in invalid_arns:
            with pytest.raises(ValueError, match="Invalid policy ARN format"):
                service._validate_policy_arn(arn)
    
    def test_extract_query_content_success(self):
        """Test extracting query_content from test case."""
        service = TestCaseService()
        
        test_case = {
            "testCaseId": "test-123",
            "guardContent": "It is 2:30 PM on a clear day",
            "queryContent": "What is the weather?"
        }
        
        query_content = service._extract_query_content(test_case)
        assert query_content == "What is the weather?"
    
    def test_extract_query_content_missing(self):
        """Test extracting query_content when not present."""
        service = TestCaseService()
        
        test_case = {
            "testCaseId": "test-123",
            "guardContent": "It is 2:30 PM on a clear day"
        }
        
        query_content = service._extract_query_content(test_case)
        assert query_content == ""
    
    @patch('boto3.client')
    def test_list_test_cases_success(self, mock_boto_client):
        """Test successful test case fetching."""
        # Mock the boto3 client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock the API response (matching actual AWS response structure)
        mock_client.list_automated_reasoning_policy_test_cases.return_value = {
            "testCases": [
                {
                    "testCaseId": "test-1",
                    "guardContent": "Answer 1",
                    "queryContent": "Test query 1"
                },
                {
                    "testCaseId": "test-2",
                    "guardContent": "Answer 2",
                    "queryContent": "Test query 2"
                }
            ]
        }
        
        service = TestCaseService()
        result = service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
        
        assert len(result) == 2
        assert result[0]["test_case_id"] == "test-1"
        assert result[0]["guard_content"] == "Test query 1"  # Returns the query (prompt)
        assert result[1]["test_case_id"] == "test-2"
        assert result[1]["guard_content"] == "Test query 2"  # Returns the query (prompt)
    
    @patch('boto3.client')
    def test_list_test_cases_empty_response(self, mock_boto_client):
        """Test handling of empty test case list."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.list_automated_reasoning_policy_test_cases.return_value = {
            "testCases": []
        }
        
        service = TestCaseService()
        result = service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
        
        assert result == []
    
    @patch('boto3.client')
    def test_list_test_cases_client_error(self, mock_boto_client):
        """Test handling of AWS ClientError."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock a non-transient error
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_client.list_automated_reasoning_policy_test_cases.side_effect = ClientError(
            error_response, 'ListAutomatedReasoningPolicyTestCases'
        )
        
        service = TestCaseService()
        
        with pytest.raises(Exception, match="Failed to fetch test cases"):
            service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
    
    @patch('boto3.client')
    def test_list_test_cases_no_credentials_error(self, mock_boto_client):
        """Test handling of NoCredentialsError."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.list_automated_reasoning_policy_test_cases.side_effect = NoCredentialsError()
        
        service = TestCaseService()
        
        with pytest.raises(Exception, match="AWS credentials not configured"):
            service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
    
    @patch('boto3.client')
    def test_list_test_cases_endpoint_connection_error(self, mock_boto_client):
        """Test handling of EndpointConnectionError."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.list_automated_reasoning_policy_test_cases.side_effect = EndpointConnectionError(
            endpoint_url="https://bedrock.us-west-2.amazonaws.com"
        )
        
        service = TestCaseService()
        
        with pytest.raises(Exception, match="AWS Bedrock service is temporarily unavailable"):
            service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
    
    def test_is_transient_error(self):
        """Test transient error detection."""
        service = TestCaseService()
        
        # Transient errors
        assert service._is_transient_error("ThrottlingException") is True
        assert service._is_transient_error("ServiceUnavailableException") is True
        assert service._is_transient_error("TooManyRequestsException") is True
        
        # Non-transient errors
        assert service._is_transient_error("AccessDeniedException") is False
        assert service._is_transient_error("ValidationException") is False
    
    @patch('boto3.client')
    @patch('time.sleep')
    def test_retry_with_exponential_backoff(self, mock_sleep, mock_boto_client):
        """Test retry logic with exponential backoff for transient errors."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock transient error on first two attempts, then success
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_client.list_automated_reasoning_policy_test_cases.side_effect = [
            ClientError(error_response, 'ListAutomatedReasoningPolicyTestCases'),
            ClientError(error_response, 'ListAutomatedReasoningPolicyTestCases'),
            {
                "testCases": [
                    {
                        "testCaseId": "test-1",
                        "guardContent": "Test answer",
                        "queryContent": "Test query"
                    }
                ]
            }
        ]
        
        service = TestCaseService()
        result = service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
        
        # Verify the result
        assert len(result) == 1
        assert result[0]["test_case_id"] == "test-1"
        assert result[0]["guard_content"] == "Test query"  # Returns the query (prompt)
        
        # Verify retry attempts (3 calls total: 2 failures + 1 success)
        assert mock_client.list_automated_reasoning_policy_test_cases.call_count == 3
        
        # Verify exponential backoff delays (1s, 2s)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)  # First retry: base_delay * 2^0
        mock_sleep.assert_any_call(2.0)  # Second retry: base_delay * 2^1
    
    @patch('boto3.client')
    @patch('time.sleep')
    def test_retry_exhausted_raises_exception(self, mock_sleep, mock_boto_client):
        """Test that exception is raised after all retries are exhausted."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock transient error on all attempts
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_client.list_automated_reasoning_policy_test_cases.side_effect = ClientError(
            error_response, 'ListAutomatedReasoningPolicyTestCases'
        )
        
        service = TestCaseService()
        
        with pytest.raises(Exception, match="Failed to fetch test cases"):
            service.list_test_cases("arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test")
        
        # Verify all 3 retry attempts were made
        assert mock_client.list_automated_reasoning_policy_test_cases.call_count == 3
        
        # Verify exponential backoff delays (1s, 2s)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)
