"""
LLM service for generating instructions for the BDA optimization application.
"""
import json
import logging
import time
import random
from typing import List, Optional, Dict, Any
import boto3
import botocore
from botocore.config import Config

from src.models.field_history import FieldHistory
from src.models.strategy import FieldData

# Configure logging
logger = logging.getLogger(__name__)

class LLMService:
    """
    Service for generating instructions using LLM.
    """
    def __init__(self, model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0", region: str = "us-east-1"):
        """
        Initialize the LLM service.
        
        Args:
            model_id: ID of the model to use
            region: AWS region
        """
        self.model_id = model_id
        self.region = region
        
        # Configure boto3 client
        config = Config(
            region_name=region,
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
        
        # Create bedrock runtime client
        self.client = boto3.client('bedrock-runtime', config=config)
        
        logger.info(f"Initialized LLM service with model {model_id} in region {region}")
    
    def call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000, temperature: float = 0.0) -> str:
        """
        Call the LLM with the given prompts.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation
            
        Returns:
            str: Generated text
        """
        # Combine system prompt and user prompt into a single user message
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Create messages with proper content format for AWS Bedrock Runtime API
        messages = [
            {"role": "user", "content": [{"text": combined_prompt}]}
        ]
        
        # Retry parameters
        max_retries = 8  # Increased from default 3
        base_delay = 2  # Base delay in seconds
        max_delay = 60  # Maximum delay in seconds
        
        # Try different models if the primary one fails
        models_to_try = [
            self.model_id,  # Try the selected model first
            "anthropic.claude-3-haiku-20240307-v1:0",  # Fallback to Haiku if selected model fails
            "meta.llama3-8b-instruct-v1:0"  # Fallback to Llama if both Claude models fail
        ]
        
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))
        
        last_exception = None
        
        # Try each model in sequence
        for model_id in models_to_try:
            # Reset retry counter for each model
            retries = 0
            
            while retries <= max_retries:
                try:
                    # Log which model we're trying
                    if retries > 0 or model_id != self.model_id:
                        logger.info(f"Trying model {model_id} (attempt {retries+1})")
                        print(f"  🔄 Trying model {model_id} (attempt {retries+1})")
                    
                    # Call the model
                    response = self.client.converse(
                        modelId=model_id,
                        messages=messages,
                        inferenceConfig={
                            "maxTokens": max_tokens,
                            "temperature": temperature
                        }
                    )
                    
                    # Extract response
                    completion_text = response['output']['message']['content'][0]['text'].strip()
                    
                    # If we're using a fallback model, log that
                    if model_id != self.model_id:
                        logger.info(f"Successfully used fallback model {model_id}")
                        print(f"  ✅ Successfully used fallback model {model_id}")
                    
                    return completion_text
                    
                except botocore.exceptions.ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    last_exception = e
                    
                    # Handle specific error codes
                    if error_code == 'ThrottlingException':
                        if retries < max_retries:
                            # Calculate delay with exponential backoff and jitter
                            delay = min(max_delay, base_delay * (2 ** retries)) + random.uniform(0, 1)
                            logger.warning(f"Throttling error with model {model_id}. Retrying in {delay:.2f} seconds...")
                            print(f"  ⚠️ Throttling error with model {model_id}. Retrying in {delay:.2f} seconds...")
                            time.sleep(delay)
                            retries += 1
                            continue
                    elif error_code == 'ValidationException' and 'on-demand throughput' in str(e):
                        # This model requires a provisioned throughput, try the next model
                        logger.warning(f"Model {model_id} requires provisioned throughput. Trying next model...")
                        print(f"  ⚠️ Model {model_id} requires provisioned throughput. Trying next model...")
                        break  # Break the retry loop and try the next model
                    
                    # For other errors or if we've exhausted retries, log and continue to next model
                    logger.error(f"Error calling model {model_id}: {str(e)}")
                    print(f"  ❌ Error calling model {model_id}: {str(e)}")
                    break  # Break the retry loop and try the next model
                
                except Exception as e:
                    last_exception = e
                    logger.error(f"Unexpected error with model {model_id}: {str(e)}")
                    print(f"  ❌ Unexpected error with model {model_id}: {str(e)}")
                    break  # Break the retry loop and try the next model
            
            # If we've exhausted retries for this model, try the next one
        
        # If all models failed, log the error and return a fallback instruction
        logger.error(f"All models failed. Last error: {str(last_exception)}")
        print(f"  ❌ All models failed. Last error: {str(last_exception)}")
        return "Extract the field from the document."
    
    def generate_initial_instruction(self, field_name: str, expected_output: str, field_type: str = "text") -> str:
        """
        Generate the first instruction attempt using LLM.
        
        Args:
            field_name: Name of the field
            expected_output: Expected output
            field_type: Type of the field
            
        Returns:
            str: Generated instruction
        """
        system_prompt = """
        You are an expert at creating simple extraction instructions for document AI systems.
        Create short, clear instructions (under 100 characters if possible) to extract fields from documents.
        
        Your response should be ONLY the instruction text, with no additional explanation or formatting.
        """
        
        type_guidance = ""
        if field_type:
            type_guidance = f"""
            This field appears to be a {field_type} type field. Consider extraction strategies 
            appropriate for {field_type} data.
            """
        
        user_prompt = f"""
        Create a short, simple instruction to extract the '{field_name}' field from a document.
        
        Expected output example: '{expected_output}'
        
        {type_guidance}
        
        Keep your instruction under 100 characters if possible. Be direct and simple.
        
        IMPORTANT: Respond with ONLY the instruction text, nothing else.
        """
        
        # Call LLM
        instruction = self.call_llm(system_prompt, user_prompt)
        
        return instruction
    
    def generate_improved_instruction(
        self, 
        field_name: str, 
        previous_instructions: List[str], 
        previous_results: List[str], 
        expected_output: str, 
        field_type: str = "text"
    ) -> str:
        """
        Generate improved instruction based on previous attempts.
        
        Args:
            field_name: Name of the field
            previous_instructions: Previous instructions
            previous_results: Previous results
            expected_output: Expected output
            field_type: Type of the field
            
        Returns:
            str: Generated instruction
        """
        system_prompt = """
        You are an expert at creating simple extraction instructions for document AI systems.
        Create a better, shorter instruction (under 100 characters if possible) based on previous attempts.
        
        Your response should be ONLY the instruction text, with no additional explanation or formatting.
        """
        
        # Format previous attempts for context
        attempts_context = ""
        for i, (instr, result) in enumerate(zip(previous_instructions, previous_results)):
            attempts_context += f"Attempt {i+1}:\n"
            attempts_context += f"Instruction: {instr}\n"
            attempts_context += f"Result: {result}\n\n"
        
        type_guidance = ""
        if field_type:
            type_guidance = f"""
            This field appears to be a {field_type} type field. Consider extraction strategies 
            appropriate for {field_type} data.
            """
        
        user_prompt = f"""
        Extract field '{field_name}' from a document.
        
        Previous attempts:
        {attempts_context}
        
        Expected output: '{expected_output}'
        
        {type_guidance}
        
        Create a simple, direct instruction under 100 characters if possible.
        
        IMPORTANT: Respond with ONLY the instruction text, nothing else.
        """
        
        # Call LLM
        instruction = self.call_llm(system_prompt, user_prompt)
        
        return instruction


    def generate_document_based_instruction(
            self,
            field_name: str,
            previous_instructions: List[str],
            previous_results: List[str],
            expected_output: str,
            document_content: str,
            field_type: str = "text"
    ) -> str:
        """
        Generate instruction using document as context.

        Args:
            field_name: Name of the field
            previous_instructions: Previous instructions
            previous_results: Previous results
            expected_output: Expected output
            document_content: Document content
            field_type: Type of the field

        Returns:
            str: Generated instruction
        """
        system_prompt = """
        You are an expert at creating simple extraction instructions for document AI systems.
        Create a short, direct instruction (under 100 characters if possible) based on document content.

        Your response should be ONLY the instruction text, with no additional explanation or formatting.
        """

        # Format previous attempts for context
        attempts_context = ""
        for i, (instr, result) in enumerate(zip(previous_instructions, previous_results)):
            attempts_context += f"Attempt {i + 1}:\n"
            attempts_context += f"Instruction: {instr}\n"
            attempts_context += f"Result: {result}\n\n"

        type_guidance = ""
        if field_type:
            type_guidance = f"""
            This field appears to be a {field_type} type field. Consider extraction strategies 
            appropriate for {field_type} data.
            """

        # Truncate document content if too long
        max_doc_length = 10000
        if len(document_content) > max_doc_length:
            document_content = document_content[:max_doc_length] + "... [document truncated]"

        user_prompt = f"""
        Extract field '{field_name}' from a document.

        Previous attempts:
        {attempts_context}

        Expected output: '{expected_output}'

        {type_guidance}

        Document content:
        {document_content}

        Create a simple, direct instruction under 100 characters if possible.

        IMPORTANT: Respond with ONLY the instruction text, nothing else.
        """

        # Call LLM with longer max tokens
        instruction = self.call_llm(system_prompt, user_prompt, max_tokens=2000)

        return instruction

    def generate_docu_based_instruction(self,
                                        fields: List[str],
                                        fields_datas: Dict[str, FieldData],
                                        fields_history_list: List[Optional[FieldHistory]],
                                        document_content) -> str:
        """
        Generate instruction using document as context.

        Args:
            field_name: Name of the field
            previous_instructions: Previous instructions
            previous_results: Previous results
            expected_output: Expected output
            document_content: Document content
            field_type: Type of the field

        Returns:
            str: Generated instruction
        """
        _fields_data = []
        for field_name in fields:
            field_data = fields_datas[field_name]
            interested_field = {
                "field_name" : field_name,
                "description": field_data.instruction,
                "expected_output": field_data.expected_output
            }
            _fields_data.append( interested_field )
        print(f"  ✅ Document based strategy prompt used {json.dumps(_fields_data)}")

        system_prompt = """
            You are expert in extracting data from documents using patterns. You will learn about the document, understand 
            the purpose of the document and help to create field extractions prompts.
            """
        results = {
            "results" : [
                {
                    "field_name": "field name",
                    "instruction" : "valid string type",
                }
            ]
        }
        # Truncate document content if too long
        max_doc_length = 30000
        if len(document_content) > max_doc_length:
            document_content = document_content[:max_doc_length] + "... [document truncated]"
        history = []
        history.append("<fields_history>")
        for field_history in fields_history_list:
            history.append(f"Field name: {field_history.field_name}")
            history.append( f"Previous instruction attempts:")
            history.append( json.dumps(field_history.instructions) )
            history.append( "   ")
        history.append("</fields_history>")
        ##Create new extraction instruction for all the fields which will be used by LLM later to extract data from similar documents.
          ##  Extraction instruction should be generalized instruction to extract these type of fields from the documents.

        user_prompt = f"""
            Your job is to improve the extraction prompts(instructions) for the fields in <field_hints>.
            Go through the document content line by line, understand the document layout and purpose of the document for example
            contract document, lease document, legal agreements etc.
            Use field_hints to understand the purpose of the field with field_name and description. Use field_hints expected_output as ground truth to validate the instruction.
            Extraction prompts should be generic, it should describe the field under 10 words and provide hints like sections or locations of document where we can find the field.
            Extraction prompt should not contain the actual field value, which will make it specific to this document so it should be avoided.    
            <field_hints>
            {json.dumps(_fields_data)}
            </field_hints>
            Field History contains extraction instructions tried before and failed, learn from this history to improve the instruction:
            {json.dumps(history)}
            <document_content>
            {document_content}
            </document_content>
            Verify and Return a valid JSON in this format: <result>{json.dumps(results)}</result>
            No preamble.
            """
        #print(f"  ✅ Document based strategy prompt used {_fields_data}")

        # Call LLM with longer max tokens
        instruction = self.call_llm(system_prompt, user_prompt, max_tokens=4000)
        #print(f"  ✅ Document based strategy result {instruction}")
        start = "<result>"
        end = "</result>"

        # Find the index of the start substring
        idx1 = instruction.find(start)

        # Find the index of the end substring, starting after the start substring
        idx2 = instruction.find(end, idx1 + len(start))
        # Check if both delimiters are found and extract the substring between them
        if idx1 != -1 and idx2 != -1:
            return instruction[idx1 + len(start):idx2]
        else:
            raise Exception("Not able to get expected results from LLM")

