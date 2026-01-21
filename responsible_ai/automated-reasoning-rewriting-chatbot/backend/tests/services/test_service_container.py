"""
Unit tests for ServiceContainer.
"""
import pytest
from unittest.mock import Mock, MagicMock

from backend.services.service_container import ServiceContainer
from backend.services.config_manager import ConfigManager, Config
from backend.services.thread_manager import ThreadManager
from backend.services.audit_logger import AuditLogger
from backend.services.timeout_handler import TimeoutHandler
from backend.services.policy_service import PolicyService
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService
from backend.services.llm_response_parser import LLMResponseParser
from backend.services.prompt_template_manager import PromptTemplateManager


class TestServiceContainerInitialization:
    """Test service container initialization."""
    
    def test_init_creates_always_available_services(self):
        """Test that initialization creates always-available services."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        # Verify always-available services are created
        assert container.thread_manager is not None
        assert isinstance(container.thread_manager, ThreadManager)
        assert container.audit_logger is not None
        assert isinstance(container.audit_logger, AuditLogger)
        assert container.timeout_handler is not None
        assert isinstance(container.timeout_handler, TimeoutHandler)
        assert container.test_case_service is not None
    
    def test_init_does_not_create_lazy_services(self):
        """Test that initialization does not create lazy-initialized services."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        # Verify lazy services are not created yet
        assert container._policy_service is None
        assert container._llm_service is None
        assert container._validation_service is None
        assert container._parser is None
        assert container._template_manager is None


class TestServiceContainerLazyLoading:
    """Test lazy loading behavior of services."""
    
    def test_get_policy_service_returns_none_without_policy(self):
        """Test that get_policy_service returns None when no policy is available."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_current_config.return_value = None
        
        container = ServiceContainer(config_manager)
        
        result = container.get_policy_service()
        
        assert result is None
        assert container._policy_service is None
    
    def test_get_policy_service_creates_service_with_policy(self):
        """Test that get_policy_service creates service when policy is available."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.policy_definition = {"rules": []}
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        result = container.get_policy_service()
        
        assert result is not None
        assert isinstance(result, PolicyService)
        assert container._policy_service is result
    
    def test_get_policy_service_returns_cached_instance(self):
        """Test that get_policy_service returns the same instance on subsequent calls."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.policy_definition = {"rules": []}
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        first_call = container.get_policy_service()
        second_call = container.get_policy_service()
        
        assert first_call is second_call
    
    def test_get_llm_service_raises_without_config(self):
        """Test that get_llm_service raises ValueError when no config is available."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_current_config.return_value = None
        
        container = ServiceContainer(config_manager)
        
        with pytest.raises(ValueError, match="no configuration available"):
            container.get_llm_service()
    
    def test_get_llm_service_creates_service_with_config(self):
        """Test that get_llm_service creates service when config is available."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.model_id = "test-model"
        mock_config.policy_definition = None
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        result = container.get_llm_service()
        
        assert result is not None
        assert isinstance(result, LLMService)
        assert container._llm_service is result
    
    def test_get_llm_service_includes_policy_context(self):
        """Test that get_llm_service includes policy context when available."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.model_id = "test-model"
        mock_config.policy_definition = {"rules": [{"identifier": "rule-1"}]}
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        result = container.get_llm_service()
        
        assert result is not None
        # Policy context should be set (non-empty if finding service is available)
        assert hasattr(result, 'policy_context')
    
    def test_get_validation_service_raises_without_config(self):
        """Test that get_validation_service raises ValueError when no config is available."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_current_config.return_value = None
        
        container = ServiceContainer(config_manager)
        
        with pytest.raises(ValueError, match="no configuration available"):
            container.get_validation_service()
    
    def test_get_validation_service_raises_without_guardrail(self):
        """Test that get_validation_service raises ValueError when no guardrail is configured."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.guardrail_id = None
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        with pytest.raises(ValueError, match="no guardrail configured"):
            container.get_validation_service()
    
    def test_get_validation_service_creates_service_with_guardrail(self):
        """Test that get_validation_service creates service when guardrail is configured."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.guardrail_id = "test-guardrail"
        mock_config.guardrail_version = "DRAFT"
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        result = container.get_validation_service()
        
        assert result is not None
        assert isinstance(result, ValidationService)
        assert container._validation_service is result
    
    def test_get_parser_creates_service(self):
        """Test that get_parser creates LLMResponseParser."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        result = container.get_parser()
        
        assert result is not None
        assert isinstance(result, LLMResponseParser)
        assert container._parser is result
    
    def test_get_parser_returns_cached_instance(self):
        """Test that get_parser returns the same instance on subsequent calls."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        first_call = container.get_parser()
        second_call = container.get_parser()
        
        assert first_call is second_call
    
    def test_get_template_manager_creates_service(self):
        """Test that get_template_manager creates PromptTemplateManager."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        result = container.get_template_manager()
        
        assert result is not None
        assert isinstance(result, PromptTemplateManager)
        assert container._template_manager is result
    
    def test_get_template_manager_returns_cached_instance(self):
        """Test that get_template_manager returns the same instance on subsequent calls."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        first_call = container.get_template_manager()
        second_call = container.get_template_manager()
        
        assert first_call is second_call


class TestServiceContainerDependencyResolution:
    """Test dependency resolution between services."""
    
    def test_llm_service_gets_policy_context_from_policy_service(self):
        """Test that LLMService receives policy context from PolicyService."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.model_id = "test-model"
        mock_config.policy_definition = {
            "rules": [
                {
                    "id": "rule-1",
                    "expression": "(test)",
                    "alternateExpression": "Test rule"
                }
            ]
        }
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        # Get finding service first to ensure it's initialized
        policy_service = container.get_policy_service()
        assert policy_service is not None
        
        # Get LLM service - should include policy context
        llm_service = container.get_llm_service()
        
        assert llm_service is not None
        assert llm_service.policy_context != ""
        # Policy context should contain rule information
        assert "rule-1" in llm_service.policy_context or "Test rule" in llm_service.policy_context


class TestServiceContainerReset:
    """Test service reset functionality."""
    
    def test_reset_services_clears_lazy_services(self):
        """Test that reset_services clears lazy-initialized services."""
        config_manager = Mock(spec=ConfigManager)
        mock_config = Mock(spec=Config)
        mock_config.model_id = "test-model"
        mock_config.guardrail_id = "test-guardrail"
        mock_config.guardrail_version = "DRAFT"
        mock_config.policy_definition = {"rules": []}
        config_manager.get_current_config.return_value = mock_config
        
        container = ServiceContainer(config_manager)
        
        # Initialize all lazy services
        container.get_policy_service()
        container.get_llm_service()
        container.get_validation_service()
        
        # Verify services are initialized
        assert container._policy_service is not None
        assert container._llm_service is not None
        assert container._validation_service is not None
        
        # Reset services
        container.reset_services()
        
        # Verify lazy services are cleared
        assert container._policy_service is None
        assert container._llm_service is None
        assert container._validation_service is None
    
    def test_reset_services_does_not_clear_parser_and_template_manager(self):
        """Test that reset_services does not clear parser and template manager."""
        config_manager = Mock(spec=ConfigManager)
        
        container = ServiceContainer(config_manager)
        
        # Initialize parser and template manager
        parser = container.get_parser()
        template_manager = container.get_template_manager()
        
        # Reset services
        container.reset_services()
        
        # Verify parser and template manager are not cleared
        assert container._parser is parser
        assert container._template_manager is template_manager
    
    def test_reset_services_allows_recreation_with_new_config(self):
        """Test that services can be recreated with new config after reset."""
        config_manager = Mock(spec=ConfigManager)
        
        # First config
        mock_config1 = Mock(spec=Config)
        mock_config1.model_id = "model-1"
        mock_config1.guardrail_id = "guardrail-1"
        mock_config1.guardrail_version = "DRAFT"
        mock_config1.policy_definition = {"rules": []}
        config_manager.get_current_config.return_value = mock_config1
        
        container = ServiceContainer(config_manager)
        
        # Get services with first config
        llm_service1 = container.get_llm_service()
        validation_service1 = container.get_validation_service()
        
        # Update config
        mock_config2 = Mock(spec=Config)
        mock_config2.model_id = "model-2"
        mock_config2.guardrail_id = "guardrail-2"
        mock_config2.guardrail_version = "1"
        mock_config2.policy_definition = {"rules": []}
        config_manager.get_current_config.return_value = mock_config2
        
        # Reset and get services with new config
        container.reset_services()
        llm_service2 = container.get_llm_service()
        validation_service2 = container.get_validation_service()
        
        # Verify new instances are created
        assert llm_service2 is not llm_service1
        assert validation_service2 is not validation_service1
        
        # Verify new services use new config
        assert llm_service2.model_id == "model-2"
        assert validation_service2.guardrail_id == "guardrail-2"
