"""
Shared pytest fixtures for backend tests.

This module provides common fixtures used across multiple test files,
reducing duplication and ensuring consistent test setup.
"""
import os
import pytest
from unittest.mock import Mock, MagicMock
import json

from backend.services.thread_manager import ThreadManager
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService, ValidationResult
from backend.services.audit_logger import AuditLogger
from backend.services.policy_service import PolicyService
from backend.services.config_manager import ConfigManager, Config
from backend.services.prompt_template_manager import PromptTemplateManager
from backend.services.llm_response_parser import LLMResponseParser
from backend.models.thread import Thread, ThreadStatus, Finding


# === Directory Fixtures ===

@pytest.fixture
def templates_dir():
    """Return the path to the prompts/templates directory."""
    return os.path.join(os.path.dirname(__file__), "..", "..", "prompts")


# === Service Fixtures ===

@pytest.fixture
def thread_manager():
    """Create a fresh ThreadManager instance."""
    return ThreadManager()


@pytest.fixture
def mock_llm_service():
    """Create a mock LLMService."""
    service = Mock(spec=LLMService)
    service.generate_response.return_value = "Test response"
    service.generate_rewriting_prompt.return_value = "Please fix your response"
    return service


@pytest.fixture
def mock_validation_service():
    """Create a mock ValidationService."""
    service = Mock(spec=ValidationService)
    service.validate.return_value = ValidationResult(output="VALID", findings=[])
    return service


@pytest.fixture
def mock_audit_logger():
    """Create a mock AuditLogger."""
    return Mock(spec=AuditLogger)


@pytest.fixture
def mock_policy_service():
    """Create a mock PolicyService."""
    service = Mock(spec=PolicyService)
    service.format_policy_context.return_value = ""
    service.enrich_findings.side_effect = lambda f: f
    service.sort_findings.side_effect = lambda f: f
    return service


@pytest.fixture
def llm_response_parser():
    """Create an LLMResponseParser instance."""
    return LLMResponseParser()


@pytest.fixture
def prompt_template_manager(templates_dir):
    """Create a PromptTemplateManager with the actual templates directory."""
    return PromptTemplateManager(templates_dir=templates_dir)


# === Sample Data Fixtures ===

@pytest.fixture
def sample_policy_definition():
    """Return a sample policy definition for testing."""
    return {
        "rules": [
            {
                "id": "rule-1",
                "expression": "(=> (employee x) (has_badge x))",
                "alternateExpression": "All employees must have a badge"
            },
            {
                "id": "rule-2",
                "expression": "(=> (visitor x) (has_escort x))",
                "alternateExpression": "All visitors must have an escort"
            }
        ],
        "variables": [
            {
                "name": "employee",
                "description": "A person employed by the organization"
            },
            {
                "name": "visitor",
                "description": "A person visiting the organization"
            }
        ]
    }


@pytest.fixture
def sample_policy_context():
    """Return a sample formatted policy context."""
    return """## Policy Context

### Rules
- rule-1: All employees must have a badge
- rule-2: All visitors must have an escort

### Variables
- employee: A person employed by the organization
- visitor: A person visiting the organization"""


@pytest.fixture
def sample_finding_invalid():
    """Return a sample INVALID finding."""
    return Finding(
        validation_output="INVALID",
        details={
            "property": "uniqueness",
            "explanation": "Values must be unique"
        }
    )


@pytest.fixture
def sample_finding_valid():
    """Return a sample VALID finding."""
    return Finding(validation_output="VALID", details={})


@pytest.fixture
def sample_finding_no_translations():
    """Return a sample NO_TRANSLATIONS finding."""
    return Finding(validation_output="NO_TRANSLATIONS", details={})


@pytest.fixture
def sample_finding_translation_ambiguous():
    """Return a sample TRANSLATION_AMBIGUOUS finding."""
    return Finding(
        validation_output="TRANSLATION_AMBIGUOUS",
        details={
            "property": "clarity",
            "explanation": "Statement is ambiguous"
        }
    )


# === Config Fixtures ===

@pytest.fixture
def sample_config():
    """Return a sample Config object."""
    return Config(
        model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
        policy_arn="arn:aws:bedrock:us-west-2:123456789:policy/test-policy",
        guardrail_id="test-guardrail-id",
        guardrail_version="DRAFT",
        max_iterations=5
    )


@pytest.fixture
def mock_config_manager(sample_config):
    """Create a mock ConfigManager with sample config."""
    manager = Mock(spec=ConfigManager)
    manager.get_current_config.return_value = sample_config
    manager.get_available_models.return_value = ["anthropic.claude-3-5-haiku-20241022-v1:0"]
    manager.get_available_policies.return_value = []
    return manager


# === Thread Fixtures ===

@pytest.fixture
def sample_thread(thread_manager):
    """Create a sample thread for testing."""
    return thread_manager.create_thread("Test prompt", "test-model")


# === Mock Response Helpers ===

@pytest.fixture
def mock_bedrock_response():
    """Return a factory for creating mock Bedrock responses."""
    def _create_response(text="Test response"):
        return {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': text}]
            }).encode())
        }
    return _create_response


@pytest.fixture
def mock_bedrock_client(mock_bedrock_response):
    """Create a mock Bedrock client."""
    client = Mock()
    client.invoke_model.return_value = mock_bedrock_response()
    return client


# === Flask App Fixtures ===

@pytest.fixture
def flask_app():
    """Create a test Flask application."""
    from backend.flask_app import create_app
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def flask_client(flask_app):
    """Create a test client for the Flask application."""
    return flask_app.test_client()
