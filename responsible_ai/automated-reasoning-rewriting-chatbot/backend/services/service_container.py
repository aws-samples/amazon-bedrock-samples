"""
Service Container for managing service lifecycle and dependencies.

This module provides centralized service initialization and dependency management
for the AR Chatbot application.
"""
import logging
from typing import Optional

from backend.services.config_manager import ConfigManager
from backend.services.thread_manager import ThreadManager
from backend.services.audit_logger import AuditLogger
from backend.services.timeout_handler import TimeoutHandler
from backend.services.policy_service import PolicyService
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService
from backend.services.llm_response_parser import LLMResponseParser
from backend.services.prompt_template_manager import PromptTemplateManager
from backend.services.test_case_service import TestCaseService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Manages service lifecycle and dependencies.
    
    This class provides centralized initialization and access to all application
    services, with support for lazy initialization and dependency injection.
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the service container with configuration.
        
        Args:
            config: ConfigManager instance for accessing application configuration
        """
        self.config = config
        
        # Always-available services (initialized immediately)
        self.thread_manager = ThreadManager()
        self.audit_logger = AuditLogger()
        self.timeout_handler = TimeoutHandler(self.thread_manager)
        self.test_case_service = TestCaseService()
        
        # Lazy-initialized services (created on first access)
        self._policy_service: Optional[PolicyService] = None
        self._llm_service: Optional[LLMService] = None
        self._validation_service: Optional[ValidationService] = None
        self._parser: Optional[LLMResponseParser] = None
        self._template_manager: Optional[PromptTemplateManager] = None
        
        logger.info("ServiceContainer initialized with always-available services")
    
    def get_policy_service(self) -> Optional[PolicyService]:
        """
        Get or create PolicyService instance.
        
        Returns:
            PolicyService instance if policy definition is available, None otherwise
        """
        current_config = self.config.get_current_config()
        
        if not current_config or not current_config.policy_definition:
            logger.debug("No policy definition available - PolicyService not initialized")
            return None
        
        if self._policy_service is None:
            logger.info("Initializing PolicyService with policy definition")
            self._policy_service = PolicyService(current_config.policy_definition)
        
        return self._policy_service
    
    def get_llm_service(self) -> LLMService:
        """
        Get or create LLMService instance.
        
        Returns:
            LLMService instance
            
        Raises:
            ValueError: If no configuration is available
        """
        current_config = self.config.get_current_config()
        
        if not current_config:
            raise ValueError("Cannot create LLMService - no configuration available")
        
        if self._llm_service is None:
            # Get policy context from policy service if available
            policy_context = ""
            policy_service = self.get_policy_service()
            if policy_service:
                policy_context = policy_service.format_policy_context()
            
            logger.info(f"Initializing LLMService with model {current_config.model_id} (requires_inference_profile={current_config.requires_inference_profile})")
            self._llm_service = LLMService(
                current_config.model_id,
                policy_context=policy_context,
                requires_inference_profile=current_config.requires_inference_profile
            )
        
        return self._llm_service
    
    def get_validation_service(self) -> ValidationService:
        """
        Get or create ValidationService instance.
        
        Returns:
            ValidationService instance
            
        Raises:
            ValueError: If no configuration or guardrail is available
        """
        current_config = self.config.get_current_config()
        
        if not current_config:
            raise ValueError("Cannot create ValidationService - no configuration available")
        
        if not current_config.guardrail_id:
            raise ValueError("Cannot create ValidationService - no guardrail configured")
        
        if self._validation_service is None:
            logger.info(
                f"Initializing ValidationService with guardrail {current_config.guardrail_id} "
                f"(version: {current_config.guardrail_version})"
            )
            self._validation_service = ValidationService(
                current_config.guardrail_id,
                current_config.guardrail_version
            )
        
        return self._validation_service
    
    def get_parser(self) -> LLMResponseParser:
        """
        Get or create LLMResponseParser instance.
        
        Returns:
            LLMResponseParser instance
        """
        if self._parser is None:
            logger.info("Initializing LLMResponseParser")
            self._parser = LLMResponseParser()
        
        return self._parser
    
    def get_template_manager(self) -> PromptTemplateManager:
        """
        Get or create PromptTemplateManager instance.
        
        Returns:
            PromptTemplateManager instance
        """
        if self._template_manager is None:
            logger.info("Initializing PromptTemplateManager")
            self._template_manager = PromptTemplateManager()
        
        return self._template_manager
    
    def reset_services(self) -> None:
        """
        Reset lazy-initialized services.
        
        This is useful when configuration changes and services need to be
        recreated with new settings.
        """
        logger.info("Resetting lazy-initialized services")
        self._policy_service = None
        self._llm_service = None
        self._validation_service = None
        # Note: Parser and template manager don't depend on config, so we don't reset them
