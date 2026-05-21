"""
Consolidated tests for policy context functionality.

This module combines tests from:
- test_policy_context_integration.py
- test_policy_context_auto_append.py
- test_initial_response_policy_context.py
"""
import pytest
from unittest.mock import Mock
import json

from backend.services.policy_service import PolicyService
from backend.services.llm_service import LLMService
from backend.services.prompt_template_manager import PromptTemplateManager
from backend.models.thread import Finding


class TestPolicyContextFormatting:
    """Tests for PolicyService policy context formatting."""
    
    def test_format_policy_context_with_rules_and_variables(self, sample_policy_definition):
        """Test formatting policy context with rules and variables."""
        policy_service = PolicyService(sample_policy_definition)
        policy_context = policy_service.format_policy_context()
        
        assert "## Policy Context" in policy_context
        assert "### Rules" in policy_context
        assert "rule-1: All employees must have a badge" in policy_context
        assert "rule-2: All visitors must have an escort" in policy_context
        assert "### Variables" in policy_context
        assert "employee: A person employed by the organization" in policy_context
    
    def test_format_policy_context_empty_policy(self):
        """Test formatting with no policy definition."""
        policy_service = PolicyService(None)
        policy_context = policy_service.format_policy_context()
        assert policy_context == ""
    
    def test_format_policy_context_rules_only(self):
        """Test formatting with rules but no variables."""
        policy_def = {
            "rules": [{"id": "rule-1", "alternateExpression": "Test rule"}]
        }
        policy_service = PolicyService(policy_def)
        policy_context = policy_service.format_policy_context()
        
        assert "### Rules" in policy_context
        assert "Test rule" in policy_context
        assert "### Variables" not in policy_context


class TestPolicyContextAutoAppend:
    """Tests for automatic policy context appending in templates."""
    
    def test_policy_context_auto_appended_to_template(self, sample_policy_context):
        """Test that policy context is automatically appended when not in template."""
        manager = PromptTemplateManager()
        
        template = """Original prompt: {{original_prompt}}
Please fix the issues."""
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            policy_context=sample_policy_context
        )
        
        assert "Test prompt" in rendered
        assert "## Policy Context" in rendered
        assert "All employees must have a badge" in rendered
        
        # Policy context should appear after template content
        template_index = rendered.index("Please fix the issues.")
        policy_index = rendered.index("## Policy Context")
        assert policy_index > template_index
    
    def test_policy_context_not_duplicated_when_in_template(self, sample_policy_context):
        """Test that policy context is not duplicated when template includes it."""
        manager = PromptTemplateManager()
        
        template = """{{policy_context}}

Original prompt: {{original_prompt}}"""
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            policy_context=sample_policy_context
        )
        
        policy_count = rendered.count("## Policy Context")
        assert policy_count == 1
        assert rendered.strip().startswith("## Policy Context")
    
    def test_empty_policy_context_not_appended(self):
        """Test that empty policy context is not appended."""
        manager = PromptTemplateManager()
        template = "Original: {{original_prompt}}"
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            policy_context=""
        )
        
        assert "Original: Test prompt" in rendered
        assert "## Policy Context" not in rendered
    
    def test_whitespace_only_policy_context_not_appended(self):
        """Test that whitespace-only policy context is not appended."""
        manager = PromptTemplateManager()
        template = "Original: {{original_prompt}}"
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            policy_context="   \n  "
        )
        
        assert "## Policy Context" not in rendered


class TestPolicyContextIntegration:
    """Integration tests for policy context flow through the system."""
    
    def test_policy_context_end_to_end_flow(
        self, sample_policy_definition, templates_dir, mock_bedrock_response
    ):
        """Test that policy context flows through the entire system."""
        # Format policy context
        policy_service = PolicyService(sample_policy_definition)
        policy_context = policy_service.format_policy_context()
        
        assert "## Policy Context" in policy_context
        assert "rule-1: All employees must have a badge" in policy_context
        
        # Create LLMService with policy context
        llm_service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir,
            policy_context=policy_context
        )
        
        assert llm_service.policy_context == policy_context
        
        # Test that policy context is included in rewriting prompts
        findings = [Finding(validation_output="INVALID", details={})]
        rewriting_prompt = llm_service.generate_rewriting_prompt(
            findings=findings,
            original_prompt="Do employees need badges?",
            original_response="No, badges are optional."
        )
        
        assert "rule-1: All employees must have a badge" in rewriting_prompt
    
    def test_policy_context_integration_without_policy(
        self, templates_dir, mock_bedrock_response
    ):
        """Test that the system works correctly when no policy is provided."""
        policy_service = PolicyService(None)
        policy_context = policy_service.format_policy_context()
        
        assert policy_context == ""
        
        llm_service = LLMService(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            templates_dir=templates_dir,
            policy_context=policy_context
        )
        
        llm_service.client.invoke_model = Mock(return_value=mock_bedrock_response())
        llm_service.generate_response("Test prompt")
        
        call_args = llm_service.client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        assert request_body['messages'][0]['content'] == "Test prompt"


class TestInitialResponsePolicyContext:
    """Tests for policy context in initial response generation."""
    
    def test_initial_response_template_includes_policy_context(
        self, prompt_template_manager, sample_policy_context
    ):
        """Test that initial response template can include policy context."""
        template = prompt_template_manager.load_template_by_name("initial_response")
        
        rendered = prompt_template_manager.render_template(
            template,
            user_prompt="What are the security requirements?",
            policy_context=sample_policy_context
        )
        
        # Verify user prompt is included
        assert "What are the security requirements?" in rendered
        
        # Verify policy context is included (either via placeholder or auto-append)
        assert "## Policy Context" in rendered or sample_policy_context in rendered
