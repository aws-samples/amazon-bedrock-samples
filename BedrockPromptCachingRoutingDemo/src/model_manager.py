
import weakref

from bedrock_service import BedrockService

class ModelManager:
    """Manages model information and selection
    
    This class maintains a list of Bedrock models that support prompt caching
    and provides methods for displaying and selecting models. It can be used
    independently or integrated with other components.
    """
    
    def __init__(self, bedrock_service=None):
        """Initialize with models that support prompt caching
        
        Args:
            bedrock_service: BedrockService instance for API calls
                           If None, a new instance will be created
                           
        Raises:
            TypeError: If bedrock_service is not a BedrockService instance
        """
        # Validate bedrock_service type if provided
        if bedrock_service is not None and not isinstance(bedrock_service, BedrockService):
            raise TypeError("bedrock_service must be an instance of BedrockService")
            
        # Initialize bedrock_service first so it's available for any methods called during initialization
        # Use weakref to avoid circular references if this ModelManager is used by the same object
        # that owns the bedrock_service
        if bedrock_service:
            self._bedrock_service_ref = weakref.ref(bedrock_service)
            self._owns_bedrock_service = False
        else:
            self._bedrock_service = BedrockService()
            self._bedrock_service_ref = weakref.ref(self._bedrock_service)
            self._owns_bedrock_service = True
        
        # Get models after bedrock_service is initialized
        self.models = self._get_prompt_cache_enabled_models()
        
    @property
    def bedrock_service(self):
        """Get the bedrock service instance
        
        Returns:
            BedrockService instance
        
        Raises:
            RuntimeError: If the bedrock service has been garbage collected
        """
        service = self._bedrock_service_ref()
        if service is None:
            raise RuntimeError("BedrockService is no longer available")
        return service
    
    def _get_prompt_cache_enabled_models(self):
        """Return a dictionary of models that support prompt caching
        
        This method returns a static list of models known to support prompt caching.
        In a production environment, this could be dynamically determined by
        querying the Bedrock service for models with specific capabilities.
        
        Returns:
            Dictionary with model categories as keys and lists of model IDs as values
            
        Raises:
            RuntimeError: If there's an error creating the model list
        """
        try:
            return {
                "Anthropic Claude Models": [
                    "anthropic.claude-haiku-4-5-20251001-v1:0",
                    "anthropic.claude-sonnet-4-5-20250929-v1:0",
                    "anthropic.claude-opus-4-1-20250805-v1:0"
                ],
                "Amazon Nova Models": [
                    "amazon.nova-micro-v1:0",
                    "amazon.nova-lite-v1:0",
                    "amazon.nova-pro-v1:0"
                ]
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create model list: {str(e)}")
    
    def display_models(self):
        """Display available models with headers
        
        Raises:
            RuntimeError: If models data structure is invalid
        """
        if not self.models:
            print("No models available to display")
            return
            
        if not isinstance(self.models, dict):
            raise RuntimeError("Models data structure is invalid")
            
        for category, model_list in self.models.items():
            if not isinstance(model_list, list):
                print(f"Warning: Skipping invalid category '{category}'")
                continue
                
            print(f"\n{category}:")
            for i, model in enumerate(model_list, 1):
                if isinstance(model, str):
                    print(f"{i}. {model}")
                else:
                    print(f"{i}. <Invalid model>")
                    
        print("")  # Add a blank line at the end
    
    def get_model_arn_from_inference_profiles(self, model_id):
        """Get model ARN from inference profiles for non-ON_DEMAND models
        
        This method resolves model IDs to their actual ARNs by checking:
        1. If the model is an ON_DEMAND type (returns as-is)
        2. If the model has a specific mapping to an inference profile
        3. If the model has a default mapping as fallback
        
        Args:
            model_id: The model ID or alias to resolve
            
        Returns:
            Resolved model ID that can be used with Bedrock APIs
            
        Raises:
            ValueError: If model_id is invalid
            RuntimeError: If there's an error communicating with Bedrock service
        """
        if not model_id or not isinstance(model_id, str):
            raise ValueError("Model ID must be a non-empty string")
            
        # Define specific model mappings to ensure correct matching
        model_mappings = {
            "anthropic.claude-sonnet-4-5-20250929-v1:0": "claude-sonnet-4-5",
            "anthropic.claude-haiku-4-5-20251001-v1:0": "claude-haiku-4-5",
            "anthropic.claude-opus-4-1-20250805-v1:0": "claude-opus-4-1"
        }
        
        # Default mappings as fallback
        default_mappings = {
            "anthropic.claude-sonnet-4-5-20250929-v1:0": "anthropic.claude-sonnet-4-5-20250929-v1:0",
            "anthropic.claude-haiku-4-5-20251001-v1:0": "anthropic.claude-haiku-4-5-20251001-v1:0",
            "anthropic.claude-opus-4-1-20250805-v1:0": "anthropic.claude-opus-4-1-20250805-v1:0"
        }
        
        # First check if we can use the default mapping directly (faster)
        if model_id in default_mappings:
            try:
                # Try to get the bedrock service, but handle the case where it's no longer available
                bedrock_service = self.bedrock_service
            except RuntimeError:
                # If bedrock service is gone, fall back to default mapping
                return default_mappings.get(model_id)
        
        try:
            # Try to get the bedrock service
            bedrock_service = self.bedrock_service
            
            # First check if the model is an ON_DEMAND type
            on_demand_models = []
            try:
                response = bedrock_service.bedrock.list_foundation_models(byInferenceType="ON_DEMAND")
                for model in response.get('modelSummaries', []):
                    model_id_value = model.get('modelId')
                    if model_id_value:
                        on_demand_models.append(model_id_value)
            except Exception as e:
                raise RuntimeError(f"Failed to list foundation models: {str(e)}")
            
            # If the model is ON_DEMAND, no need to look up inference profiles
            if model_id in on_demand_models:
                return model_id
            
            # If we don't have a specific mapping for this model, return as is
            if model_id not in model_mappings:
                return model_id
                
            # Get the specific model identifier to look for
            model_identifier = model_mappings.get(model_id)
            
            # For non-ON_DEMAND models, check inference profiles
            try:
                response = bedrock_service.list_inference_profiles(type_equals='SYSTEM_DEFINED')
            except Exception as e:
                raise RuntimeError(f"Failed to list inference profiles: {str(e)}")
            
            # Search for the model in the profiles using exact model identifier
            for profile in response.get('inferenceProfileSummaries', []):
                profile_arn = profile.get('inferenceProfileArn', '')
                
                if profile_arn and model_identifier in profile_arn:
                    # Extract the model ID from the ARN (last part after the slash)
                    try:
                        extracted_model_id = profile_arn.split('/')[-1]
                        print(f"Found inference profile for {model_id}: {profile_arn}")
                        return extracted_model_id
                    except Exception:
                        # If extraction fails, continue to next profile
                        continue
            
            # If no matching profile found, use default mapping
            if model_id in default_mappings:
                print(f"No matching inference profile found, using default mapping for {model_id}")
                return default_mappings.get(model_id)
            
            # If no default mapping, return original model ID
            return model_id
            
        except RuntimeError as e:
            # Re-raise RuntimeError for service communication issues
            raise
        except Exception as e:
            print(f"Error getting model ID from inference profiles: {e}")
            # Use default mapping if available
            if model_id in default_mappings:
                return default_mappings.get(model_id)
            return model_id
    
    def select_model(self):
        """Allow user to select a model from the available options
        
        This method displays all available models with their categories,
        marks the default model, and prompts the user to make a selection.
        It then resolves the selected model ID using inference profiles.
        
        Returns:
            Resolved model ID ready to use with Bedrock APIs
            
        Raises:
            RuntimeError: If there's an error resolving the model ID or no models are available
            ValueError: If user input is invalid after multiple attempts
        """
        if not self.models:
            raise RuntimeError("No models available for selection")
            
        print("\nAvailable models:")
        
        # Get default model ID and name for marking
        default_model_name = "Claude Sonnet 4.5"
        default_model = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        try:
            default_model_resolved = self.get_model_arn_from_inference_profiles(default_model)
        except Exception as e:
            print(f"Warning: Could not resolve default model: {str(e)}")
            default_model_resolved = default_model
        
        # Display models with default model marked
        model_index = 1
        all_models = []
        
        # Validate models structure
        if not isinstance(self.models, dict):
            raise RuntimeError("Models data structure is invalid")
            
        for category, model_list in self.models.items():
            if not isinstance(model_list, list):
                print(f"Warning: Skipping invalid category '{category}'")
                continue
                
            print(f"\n{category}:")
            for model in model_list:
                if not isinstance(model, str):
                    continue  # Skip invalid models
                    
                if model == default_model or model == default_model_resolved:
                    print(f"{model_index}. {model} [DEFAULT - {default_model_name}]")
                else:
                    print(f"{model_index}. {model}")
                all_models.append(model)
                model_index += 1
        
        if not all_models:
            raise RuntimeError("No valid models found for selection")
            
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            try:
                choice = int(input("\nSelect a model (enter number): "))
                if 1 <= choice <= len(all_models):
                    selected_model = all_models[choice-1]
                    try:
                        resolved_model = self.get_model_arn_from_inference_profiles(selected_model)
                        if resolved_model != selected_model:
                            print(f"Selected model {selected_model} resolved to {resolved_model}")
                        return resolved_model
                    except Exception as e:
                        print(f"Error resolving model: {str(e)}")
                        # Fall back to selected model if resolution fails
                        print(f"Using unresolved model ID: {selected_model}")
                        return selected_model
                else:
                    print(f"Please enter a number between 1 and {len(all_models)}")
            except ValueError:
                print("Please enter a valid number")
            
            attempts += 1
            
        # If we've exhausted attempts, use default model
        print(f"Maximum attempts reached. Using default model: {default_model_resolved}")
        return default_model_resolved
        
    def __del__(self):
        """Clean up resources when the object is garbage collected"""
        # Clear references to help with garbage collection
        if hasattr(self, '_owns_bedrock_service') and self._owns_bedrock_service:
            if hasattr(self, '_bedrock_service'):
                self._bedrock_service = None
        
        self._bedrock_service_ref = None
        self.models = None