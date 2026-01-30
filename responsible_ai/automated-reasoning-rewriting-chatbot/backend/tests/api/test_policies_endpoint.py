"""
Integration test for /api/config/policies endpoint.

This test verifies that the Flask API endpoint correctly delegates to
ConfigManager, which in turn delegates to PolicyService, and returns
the expected response structure.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.flask_app import create_app
from backend.services.policy_service import ARPolicy
from backend.exceptions import ConfigError


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_get_policies_success(client):
    """
    Test that /api/config/policies returns correct structure.
    
    Validates: Requirements 3.1
    """
    # Mock policies
    mock_policies = [
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy-1",
            name="Test Policy 1",
            description="First test policy"
        ),
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy-2",
            name="Test Policy 2",
            description="Second test policy"
        ),
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy-3",
            name="Test Policy 3",
            description=None  # Test with None description
        )
    ]
    
    # Patch ConfigManager.get_available_policies
    with patch('backend.flask_app.config_manager.get_available_policies', return_value=mock_policies):
        response = client.get('/api/config/policies')
    
    # Verify response
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify structure
    assert 'policies' in data
    assert isinstance(data['policies'], list)
    assert len(data['policies']) == 3
    
    # Verify first policy
    policy1 = data['policies'][0]
    assert policy1['arn'] == "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy-1"
    assert policy1['name'] == "Test Policy 1"
    assert policy1['description'] == "First test policy"
    
    # Verify second policy
    policy2 = data['policies'][1]
    assert policy2['arn'] == "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy-2"
    assert policy2['name'] == "Test Policy 2"
    assert policy2['description'] == "Second test policy"
    
    # Verify third policy with None description
    policy3 = data['policies'][2]
    assert policy3['arn'] == "arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test-policy-3"
    assert policy3['name'] == "Test Policy 3"
    assert policy3['description'] is None


def test_get_policies_empty_list(client):
    """
    Test that /api/config/policies handles empty policy list.
    
    Validates: Requirements 3.1
    """
    # Mock empty policy list
    with patch('backend.flask_app.config_manager.get_available_policies', return_value=[]):
        response = client.get('/api/config/policies')
    
    # Verify response
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify structure
    assert 'policies' in data
    assert isinstance(data['policies'], list)
    assert len(data['policies']) == 0


def test_get_policies_error_handling(client):
    """
    Test that /api/config/policies handles errors correctly.
    
    Validates: Requirements 3.1
    """
    # Mock exception from ConfigManager
    error_message = "Failed to connect to AWS Bedrock"
    with patch('backend.flask_app.config_manager.get_available_policies', side_effect=Exception(error_message)):
        response = client.get('/api/config/policies')
    
    # Verify error response (ConfigError returns 400)
    assert response.status_code == 400
    data = response.get_json()
    
    # Verify error structure
    assert 'error' in data
    assert data['error']['code'] == 'CONFIG_ERROR'
    assert 'Failed to retrieve available policies' in data['error']['message']
    assert error_message in data['error']['details']


def test_get_policies_response_format_matches_original(client):
    """
    Test that response format matches the original implementation.
    
    This ensures backward compatibility after refactoring.
    
    Validates: Requirements 3.1
    """
    # Mock a single policy
    mock_policies = [
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/my-policy",
            name="My Policy",
            description="A test policy"
        )
    ]
    
    with patch('backend.flask_app.config_manager.get_available_policies', return_value=mock_policies):
        response = client.get('/api/config/policies')
    
    # Verify response
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify exact structure expected by frontend
    assert 'policies' in data
    assert len(data['policies']) == 1
    
    policy = data['policies'][0]
    # These are the exact fields the frontend expects
    assert 'arn' in policy
    assert 'name' in policy
    assert 'description' in policy
    
    # Verify no extra fields
    assert set(policy.keys()) == {'arn', 'name', 'description'}


def test_get_policies_delegates_to_config_manager(client):
    """
    Test that the endpoint delegates to ConfigManager.
    
    Validates: Requirements 1.3, 4.1
    """
    mock_policies = [
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:automated-reasoning-policy/test",
            name="Test",
            description="Test"
        )
    ]
    
    # Use MagicMock to track calls
    with patch('backend.flask_app.config_manager.get_available_policies', return_value=mock_policies) as mock_method:
        response = client.get('/api/config/policies')
        
        # Verify ConfigManager method was called
        assert mock_method.called
        assert mock_method.call_count == 1
        
        # Verify response is successful
        assert response.status_code == 200
