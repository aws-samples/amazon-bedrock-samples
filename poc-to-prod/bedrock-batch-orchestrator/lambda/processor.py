from abc import ABC, abstractmethod
from typing import Dict, Literal

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
    """
    model_type: Literal['embedding', 'text']

    @abstractmethod
    def process_input(self, input_text: str, record_id: str, **kwargs) -> BatchInferenceRecord:
        """Prepare input JSON document for bedrock batch inference"""
        pass

    @abstractmethod
    def process_output(self, output_data: Dict, **kwargs) -> Dict:
        """Process model output JSON document"""
        pass


class AnthropicProcessor(BaseProcessor):
    """Processor for Anthropic Models that use the Messages API"""

    model_type = 'text'

    def process_input(self, input_text: str, record_id: str, **kwargs) -> BatchInferenceRecord:
        """Prepare according to the Messages API structure"""
        return {
            'recordId': record_id,
            'modelInput': {
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': kwargs.get('max_tokens', 1024),
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': input_text,
                            }
                        ]
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


class TitanV2Processor(BaseProcessor):
    """Processor for Amazon Titan-V2 Embedding Model"""

    model_type = 'embedding'

    def process_input(self, input_text: str, record_id: str, **kwargs) -> BatchInferenceRecord:
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
    """Utility for getting the relevant BaseProcessor based on the model_id"""
    if 'anthropic' in model_id:
        return AnthropicProcessor()
    elif 'amazon.titan-embed-text-v2:0' in model_id:
        return TitanV2Processor()
    # add logic for additional providers here, e.g.
    # elif 'llama3' in model_id:
    #     return Llama3Processor()
    else:
        raise ValueError(f'Unsupported model_id: {model_id}. Only Anthropic and Titan V2 embeddings are supported.')
