"""
Configuration Manager for the AR Chatbot.

Manages application configuration including LLM model selection,
AR policy selection, and Guardrail lifecycle management.
"""
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError
from backend.services.policy_service import ARPolicy, PolicyService

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """
    Application configuration.
    
    Attributes:
        model_id: The Bedrock model ID to use for LLM inference
        policy_arn: The ARN of the AR policy to use for validation
        guardrail_id: The ID of the Bedrock Guardrail (set after ensure_guardrail)
        guardrail_version: The version of the Guardrail (default: DRAFT)
        policy_definition: The policy definition containing rules (loaded from AWS)
        max_iterations: Maximum number of rewriting iterations allowed (default: 5)
        requires_inference_profile: Whether the model requires an inference profile (default: False)
    """
    model_id: str
    policy_arn: str
    guardrail_id: Optional[str] = None
    guardrail_version: str = "DRAFT"
    policy_definition: Optional[Dict] = None
    max_iterations: int = 5
    requires_inference_profile: bool = False


class ConfigManager:
    """
    Manages application configuration and Guardrail lifecycle.
    
    This class provides methods for:
    - Retrieving available Bedrock models
    - Retrieving available AR policies
    - Updating application configuration
    - Managing Guardrail lifecycle (create/update)
    """
    
    # Application-specific guardrail identifier
    GUARDRAIL_NAME = "ar-chatbot-guardrail"
    
    def __init__(self, region_name: str = "us-west-2"):
        """
        Initialize the configuration manager.
        
        Args:
            region_name: AWS region name (default: us-west-2)
        """
        self.region_name = region_name
        self.bedrock_client = boto3.client(
            service_name="bedrock",
            region_name=region_name
        )
        self._current_config: Optional[Config] = None
        self.policy_service = PolicyService(region_name=region_name)
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Bedrock models with ON_DEMAND or INFERENCE_PROFILE support.
        
        Returns:
            List of model IDs available in Bedrock that support ON_DEMAND or INFERENCE_PROFILE inference
            
        Raises:
            Exception: If the API call fails
        """
        models_with_metadata = self.get_available_models_with_metadata()
        return [model["model_id"] for model in models_with_metadata]
    
    def get_available_models_with_metadata(self) -> List[Dict[str, any]]:
        """
        Get list of available Bedrock models with metadata including inference type requirements.
        
        Returns:
            List of dicts with keys:
                - model_id: The Bedrock model ID
                - requires_inference_profile: Boolean indicating if model requires inference profile
                - inference_types: List of supported inference types
            
        Raises:
            Exception: If the API call fails
        """
        try:
            response = self.bedrock_client.list_foundation_models()
            models = response.get("modelSummaries", [])
            
            logger.info(f"Retrieved {len(models)} total models from Bedrock API")
            
            # Filter models by provider prefix and inference support
            # Include models with ON_DEMAND or INFERENCE_PROFILE support
            filtered_models = []
            missing_inference_types_count = 0
            
            for model in models:
                model_id = model.get("modelId")
                
                # Skip models without model ID
                if not model_id:
                    continue
                
                # Check provider prefix (anthropic or amazon)
                if not (model_id.startswith("anthropic") or model_id.startswith("amazon")):
                    continue
                
                # Check for inferenceTypesSupported field
                inference_types = model.get("inferenceTypesSupported")
                
                if inference_types is None:
                    # Handle missing inferenceTypesSupported field
                    logger.warning(f"Model {model_id} missing inferenceTypesSupported field, excluding from results")
                    missing_inference_types_count += 1
                    continue
                
                # Include models with ON_DEMAND or INFERENCE_PROFILE support
                # ON_DEMAND: Traditional pay-per-use models (e.g., Claude 3.5 Sonnet v2)
                # INFERENCE_PROFILE: Newer inference profile models (e.g., Claude Sonnet 4)
                if "ON_DEMAND" in inference_types or "INFERENCE_PROFILE" in inference_types:
                    # Determine if model requires inference profile
                    # Models that ONLY support INFERENCE_PROFILE need to use inference profile
                    requires_inference_profile = (
                        "INFERENCE_PROFILE" in inference_types and 
                        "ON_DEMAND" not in inference_types
                    )
                    
                    filtered_models.append({
                        "model_id": model_id,
                        "requires_inference_profile": requires_inference_profile,
                        "inference_types": inference_types
                    })
            
            logger.info(f"Filtered to {len(filtered_models)} models with ON_DEMAND or INFERENCE_PROFILE support (excluded {missing_inference_types_count} models with missing inferenceTypesSupported)")
            return filtered_models
            
        except ClientError as e:
            logger.error(f"Failed to retrieve available models: {str(e)}")
            raise Exception(f"Failed to retrieve available models: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving models: {str(e)}")
            raise Exception(f"Failed to retrieve available models: {str(e)}")
    
    def get_available_policies(self) -> List[ARPolicy]:
        """
        Get list of available AR policies from Bedrock.
        
        Delegates to PolicyService.
        
        Returns:
            List of ARPolicy objects
            
        Raises:
            Exception: If the API call fails
        """
        return self.policy_service.get_available_policies()
    

    
    def update_config(self, model_id: str, policy_arn: str, use_mock_policy: bool = False, max_iterations: int = 5) -> Config:
        """
        Update the application configuration.
        
        This method updates the stored configuration with the new model ID and policy ARN,
        and attempts to load the policy definition from AWS.
        Note: This does not automatically create/update the guardrail. Call ensure_guardrail
        separately to manage the guardrail lifecycle.
        
        Args:
            model_id: The Bedrock model ID to use
            policy_arn: The ARN of the AR policy to use
            use_mock_policy: If True, use a mock policy definition for testing (default: False)
            max_iterations: Maximum number of rewriting iterations allowed (default: 5)
            
        Returns:
            The updated Config object
            
        Raises:
            ValueError: If max_iterations is not a positive integer
        """
        # Validate max_iterations
        if not isinstance(max_iterations, int) or max_iterations <= 0:
            raise ValueError(f"max_iterations must be a positive integer, got: {max_iterations}")
        
        # Determine if model requires inference profile
        requires_inference_profile = self._check_requires_inference_profile(model_id)
        
        # Try to load the policy definition (optional feature)
        policy_definition = None
        
        if use_mock_policy:
            # Use mock policy for testing
            logger.info("Using mock policy definition for testing")
            policy_definition = self.policy_service.get_mock_policy_definition()
        else:
            try:
                policy_definition = self.policy_service.get_policy_definition(policy_arn)
                logger.info("Successfully loaded policy definition from AWS")
            except Exception as e:
                logger.warning(f"Could not load policy definition (feature may not be available): {e}")
                logger.info("Continuing without policy definition - rule enrichment will be disabled")
                logger.info("TIP: Set USE_MOCK_POLICY=true environment variable to test with mock data")
        
        # Update PolicyService with new definition
        if policy_definition:
            self.policy_service.update_policy_definition(policy_definition)
        
        self._current_config = Config(
            model_id=model_id,
            policy_arn=policy_arn,
            policy_definition=policy_definition,
            max_iterations=max_iterations,
            requires_inference_profile=requires_inference_profile
        )
        
        logger.info(f"Configuration updated: model_id={model_id}, policy_arn={policy_arn}, max_iterations={max_iterations}, requires_inference_profile={requires_inference_profile}")
        if policy_definition:
            rules_count = len(policy_definition.get("rules", []))
            logger.info(f"Policy definition loaded with {rules_count} rules - enrichment ENABLED")
        else:
            logger.info("No policy definition - enrichment DISABLED (rules will show IDs only)")
        
        return self._current_config
    
    def _check_requires_inference_profile(self, model_id: str) -> bool:
        """
        Check if a model requires an inference profile.
        
        This method queries the Bedrock API to determine if the model only supports
        INFERENCE_PROFILE and not ON_DEMAND invocation.
        
        Args:
            model_id: The Bedrock model ID
            
        Returns:
            True if the model requires an inference profile, False otherwise
        """
        try:
            models_with_metadata = self.get_available_models_with_metadata()
            
            for model in models_with_metadata:
                if model["model_id"] == model_id:
                    return model["requires_inference_profile"]
            
            # If model not found in list, assume it doesn't require inference profile
            logger.warning(f"Model {model_id} not found in available models list, assuming no inference profile required")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to check inference profile requirement for {model_id}: {e}")
            logger.info("Assuming model does not require inference profile")
            return False
    

    def get_current_config(self) -> Optional[Config]:
        """
        Get the current configuration.
        
        Returns:
            The current Config object, or None if not set
        """
        return self._current_config
    
    def ensure_guardrail(self, policy_arn: str) -> Tuple[str, str]:
        """
        Ensure a Guardrail exists for the given policy.
        
        This method checks if a guardrail with the application name exists.
        If it exists, it updates the guardrail with the new policy.
        If it doesn't exist, it creates a new guardrail.
        
        Args:
            policy_arn: The ARN of the AR policy to configure
            
        Returns:
            Tuple of (guardrail_id, guardrail_version)
            
        Raises:
            Exception: If guardrail creation or update fails
        """
        try:
            # Check if guardrail already exists
            existing_guardrail = self._find_existing_guardrail()
            
            if existing_guardrail:
                # Update existing guardrail
                guardrail_id = existing_guardrail["id"]
                logger.info(f"Updating existing guardrail: {guardrail_id}")
                return self._update_guardrail(guardrail_id, policy_arn)
            else:
                # Create new guardrail
                logger.info("Creating new guardrail")
                return self._create_guardrail(policy_arn)
                
        except Exception as e:
            logger.error(f"Failed to ensure guardrail: {str(e)}")
            raise Exception(f"Failed to ensure guardrail: {str(e)}")
    
    def _find_existing_guardrail(self) -> Optional[Dict]:
        """
        Find an existing guardrail with the application name.
        
        Returns:
            Guardrail summary dict if found, None otherwise
        """
        try:
            response = self.bedrock_client.list_guardrails()
            guardrails = response.get("guardrails", [])
            
            # Look for a guardrail with our application name
            for guardrail in guardrails:
                if guardrail.get("name") == self.GUARDRAIL_NAME:
                    logger.info(f"Found existing guardrail: {guardrail.get('id')}")
                    return guardrail
            
            return None
            
        except ClientError as e:
            logger.error(f"Failed to list guardrails: {str(e)}")
            raise
    
    def _create_guardrail(self, policy_arn: str) -> Tuple[str, str]:
        """
        Create a new guardrail with the given policy.
        
        Args:
            policy_arn: The ARN of the AR policy
            
        Returns:
            Tuple of (guardrail_id, guardrail_version)
        """
        try:
            policy_arn_parts = policy_arn.split(':')
            if len(policy_arn_parts) < 6:
                raise ValueError(f"Invalid Policy ARN format: {arn}")
    
            response = self.bedrock_client.create_guardrail(
                name=self.GUARDRAIL_NAME,
                description="Guardrail for AR Chatbot with automated reasoning validation",
                automatedReasoningPolicyConfig={
                    "policies": [ policy_arn ],
                    "confidenceThreshold": 1.0
                },
                blockedInputMessaging="This input cannot be processed.",
                blockedOutputsMessaging="This output cannot be provided.",
                crossRegionConfig={ "guardrailProfileIdentifier": f"arn:aws:bedrock:{policy_arn_parts[3]}:{policy_arn_parts[4]}:guardrail-profile/us.guardrail.v1:0" },
            )
            
            guardrail_id = response.get("guardrailId")
            guardrail_version = response.get("version", "DRAFT")
            
            logger.info(f"Created guardrail: {guardrail_id} (version: {guardrail_version})")
            
            # Update current config if it exists
            if self._current_config:
                self._current_config.guardrail_id = guardrail_id
                self._current_config.guardrail_version = guardrail_version
            
            return guardrail_id, guardrail_version
            
        except ClientError as e:
            logger.error(f"Failed to create guardrail: {str(e)}")
            raise
    
    def _update_guardrail(self, guardrail_id: str, policy_arn: str) -> Tuple[str, str]:
        """
        Update an existing guardrail with a new policy.
        
        Args:
            guardrail_id: The ID of the guardrail to update
            policy_arn: The ARN of the new AR policy
            
        Returns:
            Tuple of (guardrail_id, guardrail_version)
        """
        try:
            policy_arn_parts = policy_arn.split(':')
            if len(policy_arn_parts) < 6:
                raise ValueError(f"Invalid Policy ARN format: {arn}")
            
            response = self.bedrock_client.update_guardrail(
                guardrailIdentifier=guardrail_id,
                name=self.GUARDRAIL_NAME,
                description="Guardrail for AR Chatbot with automated reasoning validation",
                automatedReasoningPolicyConfig={
                    "policies": [ policy_arn ],
                    "confidenceThreshold": 1.0
                },
                blockedInputMessaging="This input cannot be processed.",
                blockedOutputsMessaging="This output cannot be provided.",
                crossRegionConfig={ "guardrailProfileIdentifier": f"arn:aws:bedrock:{policy_arn_parts[3]}:{policy_arn_parts[4]}:guardrail-profile/us.guardrail.v1:0" },
            )
            
            guardrail_version = response.get("version", "DRAFT")
            
            logger.info(f"Updated guardrail: {guardrail_id} (version: {guardrail_version})")
            
            # Update current config if it exists
            if self._current_config:
                self._current_config.guardrail_id = guardrail_id
                self._current_config.guardrail_version = guardrail_version
            
            return guardrail_id, guardrail_version
            
        except ClientError as e:
            logger.error(f"Failed to update guardrail: {str(e)}")
            raise
