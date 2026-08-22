import json
import logging
from urllib.parse import urlparse

from src.aws_clients import AWSClients

# Configure logging
logger = logging.getLogger(__name__)

# Get AWS client
aws = AWSClients()
bedrock_runtime_client = aws.bedrock_runtime

def read_s3_object(s3_uri):
    # Parse the S3 URI
    parsed_uri = urlparse(s3_uri)
    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')
    # Create an S3 client
    aws = AWSClients()
    s3_client = aws.s3_client
    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)

        # Read the content of the object
        content = response['Body'].read()
        return content
    except Exception as e:
        print(f"Error reading S3 object: {e}")
        return None

def rewrite_prompt_bedrock(field_name, original_prompt, expected_output):
    """
    Calls Amazon Bedrock's Anthropic Claude model to rewrite the prompt for better extraction.

    Args:
        field_name (str): The name of the field to extract. 
        original_prompt (str): The existing prompt.
        expected_output (str): The expected output to guide the rewriting process.

    Returns:
        str: The rewritten prompt with unwanted characters removed.
    """
    

    request_body = json.dumps({
        "prompt": f"\n\nHuman: You are an expert at prompt engineering. \
        Improve this instruction for accurate extraction: '{original_prompt}'. \
        This instruction is given to an LLM to properly extract the {field_name} from a given document. \
        The expected output should resemble: '{expected_output}'. Only output the new instruction, without any text before or after. \
        Do not include any newlines or escape characters in the instruction. Your response cannot be more than 300 characters. \n\nAssistant:",
        # "prompt": prompt,
        "max_tokens_to_sample": 200,
        "temperature": 0.1,
        "top_p": 0.9
    })

    response = bedrock_runtime_client.invoke_model(
        modelId="anthropic.claude-v2",
        body=request_body,
        accept="application/json",
        contentType="application/json"
    )

    response_body = json.loads(response["body"].read())
    completion_text = response_body["completion"].strip()

    # Remove prefixed explanation if present
    if "\n" in completion_text:
        completion_text = completion_text.split("\n", 1)[-1].strip()
    
    # Remove any quototation marks and escape characters/backslashes
    completion_text = completion_text.strip('"').strip("'")
    completion_text = completion_text.replace('\\','').replace('"','').replace("'",'')
    
    # Clean the final output
    #cleaned_text = clean_response(completion_text)

    return completion_text



def extract_text_from_document(source_document_path):
    """
    Extract text content from a document.
    
    Args:
        source_document_path (str): Path to source document (S3 URI)
        
    Returns:
        str: Extracted text content
    """
    try:
        # Read document from S3
        document_bytes = read_s3_object(source_document_path)
        if not document_bytes:
            logger.error(f"Failed to read document from {source_document_path}")
            return ""
        
        # Get AWS client
        aws = AWSClients()
        bedrock_runtime_client = aws.bedrock_runtime
        
        # Create message with document
        doc_message = {
            "role": "user",
            "content": [
                {
                    "document": {
                        "name": "Document",
                        "format": "pdf",
                        "source": {
                            "bytes": document_bytes
                        }
                    }
                },
                {"text": "Extract all text content from this document. Return only the extracted text, with no additional commentary."}
            ]
        }
        
        # Call Bedrock to extract text
        response = bedrock_runtime_client.converse(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[doc_message],
            inferenceConfig={
                "maxTokens": 4000,
                "temperature": 0
            },
        )
        
        # Extract text from response
        extracted_text = response['output']['message']['content'][0]['text'].strip()
        
        return extracted_text
        
    except Exception as e:
        logger.error(f"Error extracting text from document: {str(e)}")
        return ""

def rewrite_prompt_bedrock_with_document(field_name, original_prompt, expected_output, source_document_path):
    """
    Calls Amazon Bedrock's Anthropic Claude model to rewrite the prompt for better extraction.

    Args:
        field_name (str): The name of the field to extract. 
        original_prompt (str): The existing prompt.
        expected_output (str): The expected output to guide the rewriting process.
        source_document_path (str): Path to source document to pass to LLM. 

    Returns:
        str: The rewritten prompt with unwanted characters removed.
    """
    
    prompt = f"""
    You are an expert at prompt engineering. You need to create an instruction that will accurately extract the {field_name} from the given document. 
    This is the current instruction: '{original_prompt}'. The expected output of the extraction should resemble '{expected_output}.  
    Using the given document and the above information, create a better instruction.
    Only output the new instruction, without any text before or after. Do not include any newlines or escape characters in the instruction.
    Do not directly use words from the expected output in your instruction. Your instruction cannot be more than 300 characters. 
    """
    
    try: 
        document_bytes = read_s3_object(source_document_path)
    except Exception as e: 
        print(f"An error occured: {e}")
    
    doc_message = {
        "role": "user",
        "content": [
            {
                "document": {
                    "name": "Document 1",
                    "format": "pdf",
                    "source": {
                        "bytes": document_bytes
                    }
                }
            },
            {"text": prompt}
        ]
    }


    response = bedrock_runtime_client.converse(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        messages=[doc_message],
        inferenceConfig={
            "maxTokens": 2000,
            "temperature": 0
        },
    )

    completion_text = response['output']['message']['content'][0]['text'].strip()
    # print("Output from LLM:", completion_text)


    # Remove prefixed explanation if present
    if "\n" in completion_text:
        completion_text = completion_text.split("\n", 1)[-1].strip()
    
    # Remove any quototation marks and escape characters/backslashes
    completion_text = completion_text.strip('"').strip("'")
    completion_text = completion_text.replace('\\','').replace('"','').replace("'",'')
    

    return completion_text
