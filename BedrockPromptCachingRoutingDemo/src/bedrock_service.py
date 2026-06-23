
# AWS SDK for Python
import boto3  # For AWS API interactions
from botocore.exceptions import ClientError, NoCredentialsError  # For handling API errors


class BedrockService:
    """Handles connections to Amazon Bedrock services
    
    This class initializes and provides access to Bedrock clients:
    - bedrock-runtime: For model inference and prompt caching operations
    - bedrock: For management operations (model listing, etc.)
    """
    
    def __init__(self, region_name=None):
        """Initialize Bedrock clients using boto3
        
        Args:
            region_name: AWS region name (optional)
            
        Raises:
            NoCredentialsError: If AWS credentials are not found
            ClientError: If there's an error creating the clients
        """
        try:
            # Create clients with explicit parameters to avoid potential issues
            kwargs = {'service_name': 'bedrock-runtime'}
            if region_name:
                kwargs['region_name'] = region_name
                
            self._bedrock_runtime = boto3.client(**kwargs)
            
            kwargs['service_name'] = 'bedrock'
            self._bedrock = boto3.client(**kwargs)
            
        except NoCredentialsError as e:
            raise NoCredentialsError("AWS credentials not found. Please configure your credentials.") from e
        except Exception as e:
            raise ClientError(
                error_response={"Error": {"Message": f"Failed to initialize Bedrock clients: {str(e)}"}},
                operation_name="__init__"
            ) from e
    
    def get_runtime_client(self):
        """Return the Bedrock runtime client for inference operations
        
        Returns:
            boto3 client for bedrock-runtime
            
        Raises:
            RuntimeError: If the client is not initialized
        """
        if not hasattr(self, '_bedrock_runtime') or self._bedrock_runtime is None:
            raise RuntimeError("Bedrock runtime client is not initialized")
        return self._bedrock_runtime
    
    def get_bedrock_client(self):
        """Return the Bedrock management client for admin operations
        
        Returns:
            boto3 client for bedrock
            
        Raises:
            RuntimeError: If the client is not initialized
        """
        if not hasattr(self, '_bedrock') or self._bedrock is None:
            raise RuntimeError("Bedrock management client is not initialized")
        return self._bedrock
    
    @property
    def bedrock_runtime(self):
        """Property to access the bedrock runtime client"""
        return self.get_runtime_client()
        
    @property
    def bedrock(self):
        """Property to access the bedrock management client"""
        return self.get_bedrock_client()
        
    def list_inference_profiles(self, max_results=None, next_token=None, type_equals=None):
        """List inference profiles from Bedrock
        
        Args:
            max_results: Maximum number of results to return
            next_token: Token for pagination
            type_equals: Filter by profile type ('SYSTEM_DEFINED' or 'APPLICATION')
            
        Returns:
            Response from the list_inference_profiles API call
            
        Raises:
            ClientError: If there's an error calling the API
            RuntimeError: If the client is not initialized
        """
        # Validate parameters
        if max_results is not None and not isinstance(max_results, int):
            raise ValueError("max_results must be an integer")
            
        if type_equals is not None and type_equals not in ['SYSTEM_DEFINED', 'APPLICATION']:
            raise ValueError("type_equals must be 'SYSTEM_DEFINED' or 'APPLICATION'")
        
        params = {}
        if max_results:
            params['maxResults'] = max_results
        if next_token:
            params['nextToken'] = next_token
        if type_equals:
            params['typeEquals'] = type_equals
            
        try:
            return self.bedrock.list_inference_profiles(**params)
        except ClientError as e:
            # Re-raise with more context
            raise ClientError(
                error_response=e.response,
                operation_name="list_inference_profiles"
            ) from e
            
    def __del__(self):
        """Clean up resources when the object is garbage collected"""
        # Clear references to help with garbage collection
        if hasattr(self, '_bedrock_runtime'):
            self._bedrock_runtime = None
        if hasattr(self, '_bedrock'):
            self._bedrock = None
    
