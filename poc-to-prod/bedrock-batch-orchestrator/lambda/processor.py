from abc import ABC, abstractmethod
from typing import Dict, Literal, Optional

from custom_types import BatchInferenceRecord


"""
To support other model providers, extend the BaseProcessor class and implement the 
`process_input` and `process_output` according to the signatures in the abstract method.

They should properly structure/parse the request/response dicts according to the model provider's API definition.

You will also need to update the `get_processor_for_model_id` function below with logic to associate a given
model_id with your new BaseProcessor.
"""


class BaseProcessor(ABC):
    """
    Abstract base class implementing basic processing for Bedrock model inputs/outputs

    Extend this class with process_* functions for each provider's (e.g. Anthropic, AI21 Labs, Llama 3)
    expected input/output structure.
    
    Attributes:
        model_type: Type of model ('embedding' or 'text')
        supports_images: Whether this processor supports multimodal image inputs
    """
    model_type: Literal['embedding', 'text']
    supports_images: bool = False

    @abstractmethod
    def process_input(
        self, 
        input_text: str, 
        record_id: str,
        image_data: Optional[str] = None,
        image_s3_uri: Optional[str] = None,
        **kwargs
    ) -> BatchInferenceRecord:
        """
        Prepare input JSON document for bedrock batch inference
        
        Args:
            input_text: The text prompt to send to the model
            record_id: Unique identifier for this record
            image_data: Optional base64-encoded image data for multimodal inputs
            image_s3_uri: Optional S3 URI for image (alternative to image_data)
            **kwargs: Additional model-specific parameters
            
        Returns:
            BatchInferenceRecord with recordId and modelInput fields
        """
        pass

    @abstractmethod
    def process_output(self, output_data: Dict, **kwargs) -> Dict:
        """
        Process model output JSON document
        
        Args:
            output_data: Raw output from the batch inference job
            **kwargs: Additional processing parameters
            
        Returns:
            Dictionary with record_id and response/embedding fields
        """
        pass


class AnthropicProcessor(BaseProcessor):
    """Processor for Anthropic Models that use the Messages API"""

    model_type = 'text'
    supports_images = True

    def process_input(
        self, 
        input_text: str, 
        record_id: str,
        image_data: Optional[str] = None,
        image_s3_uri: Optional[str] = None,
        **kwargs
    ) -> BatchInferenceRecord:
        """
        Prepare according to the Messages API structure with optional image support
        
        For multimodal inputs, constructs a content array with image and text blocks.
        Image is placed before text in the content array per Anthropic's recommendations.
        """
        content = []
        
        # Add image first if provided (Anthropic recommends image before text)
        if image_data:
            content.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': 'image/jpeg',  # Default to JPEG, could be detected from data
                    'data': image_data
                }
            })
        
        # Add text content
        content.append({
            'type': 'text',
            'text': input_text,
        })
        
        return {
            'recordId': record_id,
            'modelInput': {
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': kwargs.get('max_tokens', 1024),
                'messages': [
                    {
                        'role': 'user',
                        'content': content
                    }
                ]
            }
        }

    def process_output(self, output_data: Dict, **kwargs) -> Dict:
        """Return the model's text response"""
        model_output = output_data.get('modelOutput', {'content': [{'text': None}]})
        return {
            'record_id': output_data['recordId'],
            'response': model_output['content'][-1]['text'],
        }


class NovaProcessor(BaseProcessor):
    """Processor for Amazon Nova Models (Micro, Lite, Pro, Premier)"""

    model_type = 'text'
    supports_images = True

    def process_input(
        self, 
        input_text: str, 
        record_id: str,
        image_data: Optional[str] = None,
        image_s3_uri: Optional[str] = None,
        **kwargs
    ) -> BatchInferenceRecord:
        """
        Prepare input according to Nova's messages API format
        
        Supports both base64-encoded images and S3 location references.
        Constructs a content array with text and optional image blocks.
        """
        content = []
        
        # Add text content
        content.append({
            'text': input_text
        })
        
        # Add image if provided
        if image_data:
            # Base64-encoded image
            content.append({
                'image': {
                    'format': 'jpeg',  # Default format, could be detected
                    'source': {
                        'bytes': image_data
                    }
                }
            })
        elif image_s3_uri:
            # S3 location reference
            content.append({
                'image': {
                    'format': 'jpeg',  # Default format
                    'source': {
                        's3Location': {
                            'uri': image_s3_uri,
                            'bucketOwner': kwargs.get('bucket_owner')
                        }
                    }
                }
            })
        
        return {
            'recordId': record_id,
            'modelInput': {
                'messages': [
                    {
                        'role': 'user',
                        'content': content
                    }
                ]
            }
        }

    def process_output(self, output_data: Dict, **kwargs) -> Dict:
        """
        Extract text response from Nova's output structure
        
        Nova returns responses in a content array. This method extracts
        the text from the appropriate content block.
        """
        model_output = output_data.get('modelOutput', {})
        content = model_output.get('content', [])
        
        # Extract text from content array
        text_response = None
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                text_response = item['text']
                break
        
        return {
            'record_id': output_data['recordId'],
            'response': text_response
        }


class TitanV2Processor(BaseProcessor):
    """Processor for Amazon Titan-V2 Embedding Model"""

    model_type = 'embedding'

    def process_input(
        self, 
        input_text: str, 
        record_id: str,
        image_data: Optional[str] = None,
        image_s3_uri: Optional[str] = None,
        **kwargs
    ) -> BatchInferenceRecord:
        """Prepare input according to V2 embedding request structure"""
        return {
            'recordId': record_id,
            'modelInput': {
                'inputText': input_text,
                **kwargs,
            }
        }

    def process_output(self, output_data: Dict, **kwargs) -> Dict:
        """Return the model's embedding output (float[]) & record id"""
        return {
            'record_id': output_data['recordId'],
            'embedding': output_data['modelOutput']['embedding']
        }


def get_processor_for_model_id(model_id: str) -> BaseProcessor:
    """
    Utility for getting the relevant BaseProcessor based on the model_id
    
    Args:
        model_id: The Bedrock model identifier
        
    Returns:
        Appropriate processor instance for the model
        
    Raises:
        ValueError: If the model_id is not supported
    """
    if 'amazon.nova' in model_id:
        return NovaProcessor()
    elif 'anthropic' in model_id:
        return AnthropicProcessor()
    elif 'amazon.titan-embed-text-v2:0' in model_id:
        return TitanV2Processor()
    # add logic for additional providers here, e.g.
    # elif 'llama3' in model_id:
    #     return Llama3Processor()
    else:
        raise ValueError(
            f'Unsupported model_id: {model_id}. '
            f'Supported models: Amazon Nova (amazon.nova-*), '
            f'Anthropic Claude (anthropic.*), '
            f'Amazon Titan V2 Embeddings (amazon.titan-embed-text-v2:0)'
        )
