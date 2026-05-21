"""
Consolidated tests for LLM Service.

This module combines tests from:
- test_llm_service.py (property-based tests)
- test_llm_service_templates.py (template integration)
- test_llm_service_policy_context.py (policy context support)
"""
import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch
import json
from botocore.exceptions import ClientError

from backend.services.llm_service import LLMService
from backend.models.thread import Finding


class TestLLMServiceAWSErrors:
    """Tests for AWS error handling in LLM Service."""
    
    @given(
        error_code=st.sampled_from([
            "ThrottlingException",
            "ServiceUnavailableException",
            "InternalServerException",
            "RequestTimeout",
            "TooManyRequestsException"
        ]),
        prompt=st.text(min_size=1, max_size=100)
    )
    def test_aws_failures_raise_exceptions_with_context(self, error_code, prompt):
        """
        Property 40: AWS failures raise exceptions with context.
        For any AWS API call failure, the system should raise an exception
        with a descriptive message that can be handled by the caller.
        
        Note: Errors are not logged here because they are re-raised for the
        caller to handle. Logging should happen at the point where the error
        is actually handled (e.g., at the API boundary).
        """
        service = LLMService(model_id="anthropic.claude-3-5-haiku-20241022-v1:0")
        service.max_retries = 1
        
        error_response = {'Error': {'Code': error_code, 'Message': 'Test error'}}
        service.client.invoke_model = Mock(
            side_effect=ClientError(error_response, 'invoke_model')
        )
        
        with pytest.raises(Exception) as exc_info:
            service.generate_response(prompt)
        
        # The exception message should contain useful context
        assert "Failed to" in str(exc_info.value)


class TestLLMServiceTemplates:
    """Tests for LLM Service template integration."""
    
    def test_generate_rewriting_prompt_with_template(self, templates_dir):
        """Test generating rewriting prompt using templates."""
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir
        )
        
        findings = [Finding(validation_output="INVALID", details={"explanation": "Test"})]
        prompt = service.generate_rewriting_prompt(
            findings=findings,
            original_prompt="What is 2+2?",
            original_response="5"
        )
        
        assert "What is 2+2?" in prompt
        assert "INVALID" in prompt
        assert "{{original_prompt}}" not in prompt
    
    def test_generate_rewriting_prompt_multiple_findings(self, templates_dir):
        """Test generating prompt with multiple findings."""
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir
        )
        
        findings = [
            Finding(validation_output="TRANSLATION_AMBIGUOUS", details={}),
            Finding(validation_output="INVALID", details={})
        ]
        
        prompt = service.generate_rewriting_prompt(
            findings=findings,
            original_prompt="Test prompt",
            original_response="Test response"
        )
        
        assert "Test prompt" in prompt
        assert "TRANSLATION_AMBIGUOUS" in prompt
        assert "INVALID" in prompt
    
    def test_generate_rewriting_prompt_empty_findings(self, templates_dir):
        """Test generating prompt with empty findings list."""
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir
        )
        
        prompt = service.generate_rewriting_prompt(
            findings=[],
            original_prompt="Test prompt",
            original_response="Test response"
        )
        
        assert "Test prompt" in prompt
        assert "Test response" in prompt
    
    def test_generate_rewriting_prompt_unknown_validation_output(self, templates_dir):
        """Test generating prompt with unknown validation output type."""
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir
        )
        
        findings = [Finding(validation_output="UNKNOWN_TYPE", details={})]
        prompt = service.generate_rewriting_prompt(
            findings=findings,
            original_prompt="Test prompt",
            original_response="Test response"
        )
        
        assert "Test prompt" in prompt
        assert "UNKNOWN_TYPE" in prompt
    
    def test_generate_rewriting_prompt_all_template_types(self, templates_dir):
        """Test that all template types can be loaded and rendered."""
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir
        )
        
        for validation_output in ["INVALID", "SATISFIABLE", "IMPOSSIBLE", "TRANSLATION_AMBIGUOUS"]:
            findings = [Finding(validation_output=validation_output, details={})]
            prompt = service.generate_rewriting_prompt(
                findings=findings,
                original_prompt="Original question",
                original_response="Original answer"
            )
            
            assert len(prompt) > 0
            assert "Original question" in prompt
            assert validation_output in prompt
            assert "{{" not in prompt


class TestLLMServicePolicyContext:
    """Tests for policy context support in LLM Service."""
    
    def test_policy_context_stored_in_service(self, mock_bedrock_response):
        """Test that policy context is stored in the service."""
        policy_context = "## Policy Context\n\n### Rules\n- rule-1: Test rule"
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            policy_context=policy_context
        )
        
        assert service.policy_context == policy_context
        
        service.client.invoke_model = Mock(return_value=mock_bedrock_response())
        service.generate_response("Test prompt")
        
        # Verify prompt is unchanged (policy context NOT automatically prepended)
        call_args = service.client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        actual_prompt = request_body['messages'][0]['content']
        assert actual_prompt == "Test prompt"
    
    def test_empty_policy_context_does_not_modify_prompt(self, mock_bedrock_response):
        """Test that empty policy context does not modify the prompt."""
        service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            policy_context=""
        )
        
        service.client.invoke_model = Mock(return_value=mock_bedrock_response())
        service.generate_response("Test prompt")
        
        call_args = service.client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        assert request_body['messages'][0]['content'] == "Test prompt"
    
    def test_no_policy_context_parameter_defaults_to_empty(self, mock_bedrock_response):
        """Test that not providing policy_context defaults to empty string."""
        service = LLMService(model_id="anthropic.claude-3-5-haiku-20241022-v1:0")
        
        service.client.invoke_model = Mock(return_value=mock_bedrock_response())
        service.generate_response("Test prompt")
        
        call_args = service.client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        assert request_body['messages'][0]['content'] == "Test prompt"
