"""
Tests for the test cases API endpoint.
"""
import pytest
from unittest.mock import Mock, patch
import json

from backend.flask_app import create_app


@pytest.fixture
def test_app():
    """Create a test Flask application."""
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the Flask application."""
    return test_app.test_client()


# ============================================================================
# Unit Tests for Test Cases Endpoint
# ============================================================================

def test_get_test_cases_success(client):
    """
    Test successful retrieval of test cases.
    
    Validates: Requirements 4.1, 4.2, 4.3
    """
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy"
    
    # Mock test cases response
    mock_test_cases = [
        {
            "test_case_id": "test-case-1",
            "guard_content": "It is 2:30 PM on a clear day"
        },
        {
            "test_case_id": "test-case-2",
            "guard_content": "The temperature is 75 degrees"
        }
    ]
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.return_value = mock_test_cases
        
        response = client.get(f'/api/policy/{policy_arn}/test-cases')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert 'test_cases' in data
        assert isinstance(data['test_cases'], list)
        assert len(data['test_cases']) == 2
        
        # Verify test case structure
        for test_case in data['test_cases']:
            assert 'test_case_id' in test_case
            assert 'guard_content' in test_case
            assert isinstance(test_case['test_case_id'], str)
            assert isinstance(test_case['guard_content'], str)


def test_get_test_cases_empty_policy_arn(client):
    """
    Test error handling when policy ARN is empty.
    
    Validates: Requirements 4.5
    """
    # Empty policy ARN should still reach the endpoint but fail validation
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.side_effect = ValueError("policy_arn cannot be empty")
        
        response = client.get('/api/policy//test-cases')
        
        # Flask will handle empty path parameter differently, so we test with a space
        response = client.get('/api/policy/ /test-cases')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'BAD_REQUEST'


def test_get_test_cases_invalid_arn_format(client):
    """
    Test error handling when policy ARN format is invalid.
    
    Validates: Requirements 4.5
    """
    invalid_arn = "not-a-valid-arn"
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.side_effect = ValueError(
            "Invalid policy ARN format. Expected format: "
            "arn:aws:bedrock:{region}:{account-id}:automated-reasoning-policy/{policy-id}"
        )
        
        response = client.get(f'/api/policy/{invalid_arn}/test-cases')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'BAD_REQUEST'
        assert 'Invalid policy ARN' in data['error']['message']


def test_get_test_cases_aws_api_error(client):
    """
    Test error handling when AWS API call fails.
    
    Validates: Requirements 4.4
    """
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy"
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.side_effect = Exception("Failed to fetch test cases: AWS API error")
        
        response = client.get(f'/api/policy/{policy_arn}/test-cases')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'INTERNAL_ERROR'
        assert 'Failed to fetch test cases' in data['error']['message']


def test_get_test_cases_authentication_error(client):
    """
    Test error handling when AWS credentials are missing.
    
    Validates: Requirements 7.2
    """
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy"
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.side_effect = Exception(
            "AWS credentials not configured. Please configure your AWS credentials."
        )
        
        response = client.get(f'/api/policy/{policy_arn}/test-cases')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'AUTHENTICATION_ERROR'
        assert 'credentials' in data['error']['details'].lower()


def test_get_test_cases_service_unavailable(client):
    """
    Test error handling when AWS Bedrock service is unavailable.
    
    Validates: Requirements 7.3
    """
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy"
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.side_effect = Exception(
            "AWS Bedrock service is temporarily unavailable. Please try again later."
        )
        
        response = client.get(f'/api/policy/{policy_arn}/test-cases')
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error']['code'] == 'SERVICE_UNAVAILABLE'
        assert 'unavailable' in data['error']['details'].lower()


def test_get_test_cases_empty_result(client):
    """
    Test handling when policy has no test cases.
    
    Validates: Requirements 1.5
    """
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/empty-policy"
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.return_value = []
        
        response = client.get(f'/api/policy/{policy_arn}/test-cases')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'test_cases' in data
        assert isinstance(data['test_cases'], list)
        assert len(data['test_cases']) == 0


def test_get_test_cases_url_encoded_arn(client):
    """
    Test that URL-encoded policy ARNs are handled correctly.
    
    Validates: Requirements 4.1
    """
    # ARN with special characters that need URL encoding
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy"
    url_encoded_arn = "arn%3Aaws%3Abedrock%3Aus-west-2%3A123456789012%3Aautomated-reasoning-policy%2Ftest-policy"
    
    mock_test_cases = [
        {
            "test_case_id": "test-case-1",
            "guard_content": "Test content"
        }
    ]
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.return_value = mock_test_cases
        
        response = client.get(f'/api/policy/{url_encoded_arn}/test-cases')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'test_cases' in data
        
        # Verify the service was called with the decoded ARN
        mock_service.list_test_cases.assert_called_once()
        # Flask automatically decodes URL parameters
        called_arn = mock_service.list_test_cases.call_args[0][0]
        assert called_arn == policy_arn


def test_get_test_cases_returns_json(client):
    """
    Test that the endpoint always returns JSON format.
    
    Validates: Requirements 4.3
    """
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy"
    
    with patch('backend.flask_app.service_container.test_case_service') as mock_service:
        mock_service.list_test_cases.return_value = []
        
        response = client.get(f'/api/policy/{policy_arn}/test-cases')
        
        # Verify content type is JSON
        assert response.content_type == 'application/json'
        
        # Verify response can be parsed as JSON
        try:
            data = json.loads(response.data)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
