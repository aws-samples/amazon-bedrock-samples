"""
LLM Service for interacting with Amazon Bedrock.
"""
import json
import logging
from typing import Optional, List
import boto3

from backend.services.prompt_template_manager import PromptTemplateManager
from backend.services.retry_handler import retry_api_call
from backend.models.thread import Finding

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for generating responses using Amazon Bedrock LLMs.
    
    This class handles communication with Amazon Bedrock, including:
    - Model invocation with proper request/response formatting
    - Retry logic with exponential backoff for transient failures
    - Error handling and logging
    """
    
    def __init__(self, model_id: str, region_name: str = "us-west-2", templates_dir: str = "prompts", policy_context: str = "", requires_inference_profile: bool = False):
        """
        Initialize the LLM service.
        
        Args:
            model_id: The Bedrock model ID to use (e.g., "anthropic.claude-3-5-haiku-20241022-v1:0")
            region_name: AWS region name (default: us-west-2)
            templates_dir: Directory containing prompt templates (default: prompts)
            policy_context: Formatted policy context string to prepend to prompts (default: "")
            requires_inference_profile: Whether this model requires an inference profile (default: False)
        """
        self.model_id = model_id
        self.region_name = region_name
        self.policy_context = policy_context
        self.requires_inference_profile = requires_inference_profile
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name
        )
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds for exponential backoff
        self.template_manager = PromptTemplateManager(templates_dir=templates_dir)
        
        # Determine the model identifier to use for invocation
        self.model_identifier = self._get_model_identifier()
    
    def generate_response(self, prompt: str) -> str:
        """
        Generate a response from the LLM for the given prompt.
        
        Implements retry logic with exponential backoff for transient failures.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The generated response text
            
        Raises:
            Exception: If the request fails after all retries
        """
        def invoke_model():
            request_body = self._prepare_request(prompt)
            response = self.client.invoke_model(
                modelId=self.model_identifier,
                body=json.dumps(request_body)
            )
            response_body = json.loads(response['body'].read())
            return self._parse_response(response_body)
        
        return retry_api_call(
            invoke_model,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            operation_name="generate response"
        )
    
    def _get_model_identifier(self) -> str:
        """
        Get the model identifier to use for Bedrock invocation.
        
        Models that require inference profiles need to be invoked via a regional
        inference profile ID rather than the model ID directly.
        
        Returns:
            The model identifier to use in invoke_model calls
        """
        if self.requires_inference_profile:
            # Convert model ID to inference profile ID based on provider
            # Anthropic: anthropic.claude-{model}-{version} -> us.anthropic.claude-{model}-{version}
            # Amazon: amazon.{model}-{version} -> us.amazon.{model}-{version}
            
            if self.model_id.startswith("anthropic."):
                profile_id = self.model_id.replace("anthropic.", "us.anthropic.", 1)
            elif self.model_id.startswith("amazon."):
                profile_id = self.model_id.replace("amazon.", "us.amazon.", 1)
            else:
                # For other providers, use the same pattern
                # Format: {provider}.{model} -> us.{provider}.{model}
                profile_id = f"us.{self.model_id}"
            
            logger.info(f"Model {self.model_id} requires inference profile, using: {profile_id}")
            return profile_id
        
        return self.model_id
    
    def _prepare_request(self, prompt: str) -> dict:
        """
        Prepare the request body based on the model type.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Dictionary containing the properly formatted request
        """
        # Handle Claude models (Anthropic)
        if "anthropic.claude" in self.model_id or "claude" in self.model_id:
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        
        # Handle Amazon Nova models
        if "amazon.nova" in self.model_id or "nova" in self.model_id:
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 300
                }
            }
        
        # Default format for other models
        return {
            "prompt": prompt,
            "max_tokens": 300
        }
    
    def _parse_response(self, response_body: dict) -> str:
        """
        Parse the response body based on the model type.
        
        Args:
            response_body: The response body from Bedrock
            
        Returns:
            The extracted response text
        """
        # Handle Claude models (Anthropic)
        if "anthropic.claude" in self.model_id or "claude" in self.model_id:
            content = response_body.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
            return ""
        
        # Handle Amazon Nova models
        if "amazon.nova" in self.model_id or "nova" in self.model_id:
            output = response_body.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])
            if content and len(content) > 0:
                return content[0].get("text", "")
            return ""
        
        # Default format for other models
        return response_body.get("completion", response_body.get("text", ""))
    
    def generate_rewriting_prompt(
        self,
        findings: List[Finding],
        original_prompt: str,
        original_response: str,
        all_clarifications: List = None
    ) -> str:
        """
        Generate a rewriting prompt based on validation findings using templates.
        
        Loads the appropriate template based on the validation output type
        and renders it with the findings and context.
        
        Args:
            findings: List of Finding objects from validation
            original_prompt: The user's original prompt
            original_response: The LLM's response that failed validation
            all_clarifications: List of QuestionAnswerExchange objects from all previous clarifications
            
        Returns:
            A prompt asking the LLM to correct its response
        """
        if not findings:
            # Fallback if no findings provided - use template
            fallback_template = self.template_manager.load_template_by_name("fallback_no_findings")
            return self.template_manager.render_template(
                fallback_template,
                original_prompt=original_prompt,
                original_response=original_response
            )
        
        # Get the validation output from the first (highest priority) finding
        validation_output = findings[0].validation_output
        
        # Create context augmentation from all clarifications
        context_augmentation = ""
        if all_clarifications:
            context_augmentation = self.template_manager.create_all_clarifications_context(all_clarifications)
        
        try:
            # Load the appropriate template
            template = self.template_manager.load_template_for_validation_result(validation_output)
            
            # Render the template with the findings and context
            return self.template_manager.render_template(
                template=template,
                original_prompt=original_prompt,
                original_response=original_response,
                findings=findings,
                context_augmentation=context_augmentation,
                policy_context=self.policy_context
            )
        except FileNotFoundError:
            # Fallback to simple format if template not found - use fallback template
            logger.warning(f"Template not found for {validation_output}, using fallback format")
            findings_text = "\n".join([
                f"- {f.validation_output}: {f.details.get('explanation', 'No explanation provided')}"
                for f in findings
            ])
            
            fallback_template = self.template_manager.load_template_by_name("fallback_no_template")
            # Don't pass findings parameter, use kwargs instead to pass pre-formatted string
            return self.template_manager.render_template(
                fallback_template,
                original_prompt=original_prompt,
                original_response=original_response,
                context_augmentation=context_augmentation,
                **{'findings': findings_text}  # Pass as kwarg to override
            )
