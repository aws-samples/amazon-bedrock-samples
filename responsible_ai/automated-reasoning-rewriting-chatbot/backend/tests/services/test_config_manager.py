"""
Tests for ConfigManager class.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from backend.services.config_manager import ConfigManager, Config
from backend.services.policy_service import ARPolicy


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    return Mock()


@pytest.fixture
def mock_policy_service():
    """Create a mock PolicyService."""
    return Mock()


@pytest.fixture
def config_manager(mock_bedrock_client, mock_policy_service):
    """Create a ConfigManager with mocked Bedrock client and PolicyService."""
    # Patch boto3.client during ConfigManager initialization to avoid real AWS calls
    with patch('backend.services.config_manager.boto3.client', return_value=mock_bedrock_client):
        # Patch PolicyService to inject our mock
        with patch('backend.services.config_manager.PolicyService', return_value=mock_policy_service):
            manager = ConfigManager(region_name="us-west-2")
    # The manager now has the mock_bedrock_client as its bedrock_client
    # and mock_policy_service as its policy_service
    return manager


def test_update_config(config_manager, mock_policy_service):
    """Test updating configuration uses PolicyService for policy definition."""
    model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Mock PolicyService to raise exception (simulating policy definition not available)
    mock_policy_service.get_policy_definition.side_effect = Exception("Policy definition not available")
    
    config = config_manager.update_config(model_id, policy_arn)
    
    # Verify PolicyService was called to get policy definition
    mock_policy_service.get_policy_definition.assert_called_once_with(policy_arn)
    
    # Verify config was created correctly
    assert config is not None
    assert config.model_id == model_id
    assert config.policy_arn == policy_arn
    assert config.guardrail_id is None
    assert config.guardrail_version == "DRAFT"


def test_get_current_config(config_manager, mock_policy_service):
    """Test retrieving current configuration."""
    # Initially should be None
    assert config_manager.get_current_config() is None
    
    # Mock PolicyService to raise exception (simulating policy definition not available)
    mock_policy_service.get_policy_definition.side_effect = Exception("Policy definition not available")
    
    # After update, should return the config
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    config_manager.update_config(model_id, policy_arn)
    
    current_config = config_manager.get_current_config()
    assert current_config is not None
    assert current_config.model_id == model_id
    assert current_config.policy_arn == policy_arn


def test_update_config_with_max_iterations(config_manager, mock_policy_service):
    """Test updating configuration with custom max_iterations."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    max_iterations = 10
    
    # Mock PolicyService to raise exception (simulating policy definition not available)
    mock_policy_service.get_policy_definition.side_effect = Exception("Policy definition not available")
    
    config = config_manager.update_config(model_id, policy_arn, max_iterations=max_iterations)
    
    assert config is not None
    assert config.max_iterations == max_iterations


def test_update_config_default_max_iterations(config_manager, mock_policy_service):
    """Test that default max_iterations is 5."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    
    # Mock PolicyService to raise exception (simulating policy definition not available)
    mock_policy_service.get_policy_definition.side_effect = Exception("Policy definition not available")
    
    config = config_manager.update_config(model_id, policy_arn)
    
    assert config is not None
    assert config.max_iterations == 5


def test_update_config_with_mock_policy(config_manager, mock_policy_service):
    """Test updating configuration with mock policy uses PolicyService."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    
    # Mock PolicyService to return a mock policy definition
    mock_policy_def = {
        "version": "1.0",
        "rules": [{"id": "rule-1", "expression": "(test)", "alternateExpression": "test rule"}]
    }
    mock_policy_service.get_mock_policy_definition.return_value = mock_policy_def
    
    config = config_manager.update_config(model_id, policy_arn, use_mock_policy=True)
    
    # Verify PolicyService.get_mock_policy_definition was called
    mock_policy_service.get_mock_policy_definition.assert_called_once()
    
    # Verify PolicyService.get_policy_definition was NOT called
    mock_policy_service.get_policy_definition.assert_not_called()
    
    # Verify PolicyService.update_policy_definition was called with the mock policy
    mock_policy_service.update_policy_definition.assert_called_once_with(mock_policy_def)
    
    # Verify config was created correctly
    assert config is not None
    assert config.model_id == model_id
    assert config.policy_arn == policy_arn
    assert config.policy_definition == mock_policy_def


def test_update_config_with_policy_definition_success(config_manager, mock_policy_service):
    """Test updating configuration successfully loads policy definition from PolicyService."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    
    # Mock PolicyService to return a policy definition
    policy_def = {
        "version": "1.0",
        "rules": [
            {"id": "rule-1", "expression": "(test1)", "alternateExpression": "test rule 1"},
            {"id": "rule-2", "expression": "(test2)", "alternateExpression": "test rule 2"}
        ]
    }
    mock_policy_service.get_policy_definition.return_value = policy_def
    
    config = config_manager.update_config(model_id, policy_arn)
    
    # Verify PolicyService.get_policy_definition was called
    mock_policy_service.get_policy_definition.assert_called_once_with(policy_arn)
    
    # Verify PolicyService.update_policy_definition was called with the policy
    mock_policy_service.update_policy_definition.assert_called_once_with(policy_def)
    
    # Verify config was created correctly with policy definition
    assert config is not None
    assert config.model_id == model_id
    assert config.policy_arn == policy_arn
    assert config.policy_definition == policy_def


def test_update_config_invalid_max_iterations_zero(config_manager, mock_policy_service):
    """Test that max_iterations of 0 is rejected."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    
    with pytest.raises(ValueError) as exc_info:
        config_manager.update_config(model_id, policy_arn, max_iterations=0)
    
    assert "must be a positive integer" in str(exc_info.value)


def test_update_config_invalid_max_iterations_negative(config_manager, mock_policy_service):
    """Test that negative max_iterations is rejected."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    
    with pytest.raises(ValueError) as exc_info:
        config_manager.update_config(model_id, policy_arn, max_iterations=-5)
    
    assert "must be a positive integer" in str(exc_info.value)


def test_update_config_invalid_max_iterations_non_integer(config_manager, mock_policy_service):
    """Test that non-integer max_iterations is rejected."""
    model_id = "test-model"
    policy_arn = "test-policy-arn"
    
    with pytest.raises(ValueError) as exc_info:
        config_manager.update_config(model_id, policy_arn, max_iterations=5.5)
    
    assert "must be a positive integer" in str(exc_info.value)


def test_get_available_models(config_manager, mock_bedrock_client):
    """Test retrieving available models with ON_DEMAND support."""
    mock_bedrock_client.list_foundation_models.return_value = {
        "modelSummaries": [
            {
                "modelId": "anthropic.claude-3-5-haiku-20241022-v1:0",
                "inferenceTypesSupported": ["ON_DEMAND"]
            },
            {
                "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                "inferenceTypesSupported": ["ON_DEMAND", "PROVISIONED"]
            },
            {
                "modelId": "amazon.titan-text-express-v1",
                "inferenceTypesSupported": ["ON_DEMAND"]
            }
        ]
    }
    
    models = config_manager.get_available_models()
    
    assert len(models) == 3
    assert "anthropic.claude-3-5-haiku-20241022-v1:0" in models
    assert "anthropic.claude-3-sonnet-20240229-v1:0" in models
    assert "amazon.titan-text-express-v1" in models
    mock_bedrock_client.list_foundation_models.assert_called_once()


def test_get_available_models_error(config_manager, mock_bedrock_client):
    """Test error handling when retrieving models fails."""
    from botocore.exceptions import ClientError
    
    mock_bedrock_client.list_foundation_models.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "ListFoundationModels"
    )
    
    with pytest.raises(Exception) as exc_info:
        config_manager.get_available_models()
    
    assert "Failed to retrieve available models" in str(exc_info.value)


def test_get_available_policies(config_manager, mock_policy_service):
    """Test retrieving available policies delegates to PolicyService."""
    # Setup mock PolicyService to return test policies
    test_policies = [
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:policy/policy-1",
            name="Policy 1",
            description="Test policy 1"
        ),
        ARPolicy(
            arn="arn:aws:bedrock:us-west-2:123456789012:policy/policy-2",
            name="Policy 2",
            description="Test policy 2"
        )
    ]
    mock_policy_service.get_available_policies.return_value = test_policies
    
    # Call the method
    policies = config_manager.get_available_policies()
    
    # Verify delegation to PolicyService
    mock_policy_service.get_available_policies.assert_called_once()
    
    # Verify the returned policies
    assert len(policies) == 2
    assert all(isinstance(p, ARPolicy) for p in policies)
    assert all(p.arn and p.name for p in policies)
    assert policies[0].arn == "arn:aws:bedrock:us-west-2:123456789012:policy/policy-1"
    assert policies[0].name == "Policy 1"
    assert policies[1].arn == "arn:aws:bedrock:us-west-2:123456789012:policy/policy-2"


def test_ensure_guardrail_creates_new(config_manager, mock_bedrock_client):
    """Test creating a new guardrail when none exists."""
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Mock list_guardrails to return empty list
    mock_bedrock_client.list_guardrails.return_value = {
        "guardrails": []
    }
    
    # Mock create_guardrail
    mock_bedrock_client.create_guardrail.return_value = {
        "guardrailId": "new-guardrail-id",
        "version": "1"
    }
    
    guardrail_id, version = config_manager.ensure_guardrail(policy_arn)
    
    assert guardrail_id == "new-guardrail-id"
    assert version == "1"
    mock_bedrock_client.list_guardrails.assert_called_once()
    mock_bedrock_client.create_guardrail.assert_called_once()


def test_ensure_guardrail_updates_existing(config_manager, mock_bedrock_client):
    """Test updating an existing guardrail."""
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Mock list_guardrails to return existing guardrail
    mock_bedrock_client.list_guardrails.return_value = {
        "guardrails": [
            {
                "id": "existing-guardrail-id",
                "name": ConfigManager.GUARDRAIL_NAME
            }
        ]
    }
    
    # Mock update_guardrail
    mock_bedrock_client.update_guardrail.return_value = {
        "guardrailId": "existing-guardrail-id",
        "version": "2"
    }
    
    guardrail_id, version = config_manager.ensure_guardrail(policy_arn)
    
    assert guardrail_id == "existing-guardrail-id"
    assert version == "2"
    mock_bedrock_client.list_guardrails.assert_called_once()
    mock_bedrock_client.update_guardrail.assert_called_once()
    # Should not create a new guardrail
    mock_bedrock_client.create_guardrail.assert_not_called()


def test_ensure_guardrail_updates_config(config_manager, mock_bedrock_client, mock_policy_service):
    """Test that ensure_guardrail updates the current config."""
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Mock PolicyService to raise exception (simulating policy definition not available)
    mock_policy_service.get_policy_definition.side_effect = Exception("Policy definition not available")
    
    # Set up initial config
    config_manager.update_config("test-model", policy_arn)
    
    # Mock list_guardrails to return empty list
    mock_bedrock_client.list_guardrails.return_value = {
        "guardrails": []
    }
    
    # Mock create_guardrail
    mock_bedrock_client.create_guardrail.return_value = {
        "guardrailId": "new-guardrail-id",
        "version": "1"
    }
    
    config_manager.ensure_guardrail(policy_arn)
    
    # Check that config was updated
    current_config = config_manager.get_current_config()
    assert current_config.guardrail_id == "new-guardrail-id"
    assert current_config.guardrail_version == "1"


def test_ensure_guardrail_error(config_manager, mock_bedrock_client):
    """Test error handling when guardrail operations fail."""
    from botocore.exceptions import ClientError
    
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    mock_bedrock_client.list_guardrails.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "ListGuardrails"
    )
    
    with pytest.raises(Exception) as exc_info:
        config_manager.ensure_guardrail(policy_arn)
    
    assert "Failed to ensure guardrail" in str(exc_info.value)



# Property-Based Tests

# Feature: on-demand-model-filtering, Property 1: ON_DEMAND filtering completeness
@given(
    model_summaries=st.lists(
        st.fixed_dictionaries({
            "modelId": st.one_of(
                st.just("anthropic.claude-3-5-haiku-20241022-v1:0"),
                st.just("anthropic.claude-3-sonnet-20240229-v1:0"),
                st.just("amazon.titan-text-express-v1"),
                st.just("amazon.titan-embed-text-v1"),
                st.just("meta.llama3-8b-instruct-v1:0"),  # Non-anthropic/amazon
            ),
            "inferenceTypesSupported": st.one_of(
                st.just(["ON_DEMAND"]),
                st.just(["PROVISIONED"]),
                st.just(["ON_DEMAND", "PROVISIONED"]),
                st.just([]),
                st.none(),  # Missing field
            )
        }),
        min_size=0,
        max_size=20
    )
)
@settings(max_examples=100)
def test_property_on_demand_filtering_completeness(model_summaries):
    """
    Property 1: ON_DEMAND filtering completeness
    Validates: Requirements 1.1, 1.2, 1.3, 3.2
    
    For any list of model summaries, all models in the filtered result must have 
    "ON_DEMAND" in their inferenceTypesSupported list, and all models with 
    "ON_DEMAND" support must be included in the result.
    """
    # Setup - create fresh mock for each test
    mock_client = Mock()
    mock_client.list_foundation_models.return_value = {
        "modelSummaries": model_summaries
    }
    
    with patch('backend.services.config_manager.boto3.client', return_value=mock_client):
        manager = ConfigManager(region_name="us-west-2")
    
    # Execute
    result = manager.get_available_models()
    
    # Verify: All returned models have ON_DEMAND support
    for model_id in result:
        # Find the model in the input (there may be duplicates)
        matching_models = [m for m in model_summaries if m.get("modelId") == model_id]
        assert len(matching_models) >= 1, f"Model {model_id} should exist in input"
        
        # Check that at least one matching model has ON_DEMAND support
        has_on_demand = False
        for model in matching_models:
            inference_types = model.get("inferenceTypesSupported")
            if inference_types is not None and "ON_DEMAND" in inference_types:
                has_on_demand = True
                break
        
        assert has_on_demand, f"Model {model_id} in result should have ON_DEMAND support"
    
    # Verify: All models with ON_DEMAND support are included (and match provider filter)
    for model in model_summaries:
        model_id = model.get("modelId")
        inference_types = model.get("inferenceTypesSupported")
        
        # Check if model should be included
        has_on_demand = inference_types is not None and "ON_DEMAND" in inference_types
        matches_provider = model_id and (model_id.startswith("anthropic") or model_id.startswith("amazon"))
        
        if has_on_demand and matches_provider:
            assert model_id in result, f"Model {model_id} with ON_DEMAND support should be in result"



# Feature: on-demand-model-filtering, Property 2: Error propagation with context
@given(
    error_code=st.sampled_from(["AccessDenied", "ServiceUnavailable", "ThrottlingException", "InternalServerError"]),
    error_message=st.text(min_size=1, max_size=100)
)
@settings(max_examples=100)
def test_property_error_propagation_with_context(error_code, error_message):
    """
    Property 2: Error propagation with context
    Validates: Requirements 1.5, 3.3
    
    For any Bedrock API error, the system must propagate the error wrapped with 
    appropriate context messaging that indicates the failure occurred during 
    model retrieval.
    """
    from botocore.exceptions import ClientError
    
    # Setup - create fresh mock for each test
    mock_client = Mock()
    mock_client.list_foundation_models.side_effect = ClientError(
        {"Error": {"Code": error_code, "Message": error_message}},
        "ListFoundationModels"
    )
    
    with patch('backend.services.config_manager.boto3.client', return_value=mock_client):
        manager = ConfigManager(region_name="us-west-2")
    
    # Execute and verify
    with pytest.raises(Exception) as exc_info:
        manager.get_available_models()
    
    # Verify error message contains context
    error_str = str(exc_info.value)
    assert "Failed to retrieve available models" in error_str, \
        "Error message should contain context about model retrieval failure"
    
    # Verify original error information is preserved
    # The original error should be in the string representation
    assert error_code in error_str or error_message in error_str, \
        "Error message should contain original error information"


# Feature: iteration-display-restructure, Property 14: Configuration value used
@given(
    max_iterations=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=100)
def test_property_configuration_value_used(max_iterations):
    """
    Property 14: Configuration value used
    Validates: Requirements 7.2, 7.4
    
    For any configuration with a specified max_iterations value, the configuration
    should store and return that value correctly.
    """
    # Setup - create fresh mock for each test
    mock_client = Mock()
    
    with patch('backend.services.config_manager.boto3.client', return_value=mock_client):
        manager = ConfigManager(region_name="us-west-2")
    
    # Execute
    model_id = "test-model"
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    config = manager.update_config(model_id, policy_arn, max_iterations=max_iterations)
    
    # Verify: The returned config has the specified max_iterations value
    assert config.max_iterations == max_iterations, \
        f"Config should have max_iterations={max_iterations}, got {config.max_iterations}"
    
    # Verify: Getting the current config also returns the same value
    current_config = manager.get_current_config()
    assert current_config is not None, "Current config should not be None"
    assert current_config.max_iterations == max_iterations, \
        f"Current config should have max_iterations={max_iterations}, got {current_config.max_iterations}"
