import boto3
import json
import os
from botocore.session import Session
from rewrite import ResponseRewriter
from policy_definition import get_policy_definition

# Configuration
# -------------
# Policy arn for which will be attached to the guardrail
AR_POLICY_ARN="<AR_POLICY_ARN>"

# Unique identifier for the automated reasoning policy
AR_POLICY_ID="<AR_POLICY_ID>"

# Version of the automated reasoning policy to use
AR_POLICY_VERSION = "DRAFT"

# Guardrail profile ID used when creating guardrail
# Guardrails with automated reasoning must have cross region guardrail profile
GUARDRAIL_PROFILE_ID = 'us.guardrail.v1:0'

# Name of the new guardrail that will be used for validation
DEFAULT_GUARDRAIL_NAME = "<DEFAULT_GUARDRAIL_NAME>"

# AWS region to use
REGION = "us-west-2"

# Model ID mapping
MODEL_MAPPING = {
    "nova_lite": "us.amazon.nova-lite-v1:0",     # Using cross-region inference profile
    "nova_micro": "us.amazon.nova-micro-v1:0",   # Using cross-region inference profile
    "nova_pro": "us.amazon.nova-pro-v1:0",       # Using cross-region inference profile
    "claude_3_5_sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude_3_5_haiku": "anthropic.claude-3-5-haiku-20241022-v1:0"  # Default model
}

# Default model if not specified
DEFAULT_MODEL = "nova_pro"

# Register custom Bedrock API models
def register_custom_models():
    """
    Register custom Bedrock API models with boto3.
    
    This function patches boto3's session to use our custom API models for Bedrock services.
    """
    try:
        # Get the directory of the current file
        current_dir = os.getcwd()
        
        # Define paths to the custom model definitions
        bedrock_file = os.path.join(current_dir, 'models', 'bedrock-2023-04-20.normal.json')
        runtime_file = os.path.join(current_dir, 'models', 'bedrock-runtime-2023-09-30.normal.json')
        policy_file = os.path.join(current_dir, 'models', 'bedrock-policy-2018-05-10.api.json') 
        
        # Create a custom session with the model overrides
        REGION_NAME="us-west-2"
        session = boto3.Session(region_name=REGION_NAME)
        
        # Store the original loader function
        original_loader = session._loader.load_service_model
        
        def custom_load_service_model(service_name, type_name, *args, **kwargs):
            if service_name == 'bedrock' and type_name == 'service-2':
                with open(bedrock_file, 'r') as f:
                    return json.load(f)
            elif service_name == 'bedrock-runtime' and type_name == 'service-2':
                with open(runtime_file, 'r') as f:
                    return json.load(f)
            elif service_name == 'bedrock-policy' and type_name == 'service-2':  
                with open(policy_file, 'r') as f:
                    return json.load(f)
            else:
                return original_loader(service_name, type_name, *args, **kwargs)
            
        # Apply the monkey patch
        session._loader.load_service_model = custom_load_service_model
        
        return session
    except Exception as e:
        print(f"Error registering custom models: {str(e)}")
        return None

def find_guardrail_id(client, name):
    """Find the guardrail ID based on name with pagination support"""
    next_token = None
    
    try:
        print(f"Searching for guardrail with name: {name}")
        while True:
            # Handle pagination
            if next_token:
                resp = client.list_guardrails(nextToken=next_token)
            else:
                resp = client.list_guardrails()
            
            # Search for guardrail by name
            for g in resp.get("guardrails", []):
                if g["name"] == name:
                    print(f"Found guardrail: {g['id']} (version {g['version']})")
                    return g["id"], g["version"]
            
            # Check if there are more pages
            next_token = resp.get("nextToken")
            if not next_token:
                break
                
        print(f"No guardrail found with name: {name}")
        return None, None
    except Exception as e:
        print(f"Error finding guardrail: {e}")
        return None, None

# Extract 'automatedReasoningPolicy' part of the ApplyGuardrails API response
def extract_automated_reasoning_validation_result(guardrails_output):
    if 'assessments' in guardrails_output and guardrails_output['assessments']:
        if 'automatedReasoningPolicy' in guardrails_output['assessments'][0]:
            return guardrails_output['assessments'][0]['automatedReasoningPolicy']

    raise Exception("guardrails response does not contain automated reasoning validation result")

# Validates the input event parameters for the Lambda function
def validate_input(event):
    if not event.get('query') or not event.get('response'):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required parameters: query and response'})
        }
    
    # New parameter for model selection
    model_type = event.get('model_type', DEFAULT_MODEL)
    if model_type not in MODEL_MAPPING:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f"Invalid model_type: {model_type}. Valid options are: {', '.join(MODEL_MAPPING.keys())}"})
        }

def find_or_create_guardrail(bedrock_client):
    guardrail_id, guardrail_version = find_guardrail_id(bedrock_client, DEFAULT_GUARDRAIL_NAME)
    if guardrail_id is not None:
        return guardrail_id, guardrail_version

    # Guardrail not found, create it
    print("Creating guardrail...")
    create_guardrail_response = bedrock_client.create_guardrail(
        name=DEFAULT_GUARDRAIL_NAME,
        automated_reasoning_policy_config={
            "policies": [f"{AR_POLICY_ARN}:{AR_POLICY_VERSION}"],
            "confidenceThreshold": 1.0
        },
        cross_region_config={ 'guardrailProfileIdentifier': GUARDRAIL_PROFILE_ID },
        blocked_input_messaging="Input is blocked", 
        blocked_output_messaging="Output is blocked")

    return create_guardrail_response["guardrailId"], create_guardrail_response["version"]

def lambda_handler(event, context):
    try:
        # Register custom models and create a boto3 session using them
        print("Registering custom service models...")
        custom_session = register_custom_models()
        if custom_session is None:
            raise Exception("Failed to register custom models")
        
        # Create clients using the custom session
        runtime_client = custom_session.client('bedrock-runtime')
        bedrock_client = custom_session.client('bedrock')
        bedrock_policy_client = custom_session.client('bedrock-policy')
        
        # Validate input parameters
        validation_failure = validate_input(event)
        if validation_failure:
            return validation_failure

        # Extract input from the event
        query = event.get('query')
        response = event.get('response')
        model_id = MODEL_MAPPING.get(event.get('model_type', DEFAULT_MODEL))

        # Find guardrail and create it if it doesn't exist
        guardrail_id, guardrail_version = find_or_create_guardrail(bedrock_client)

        # Get automated reasoning policy definition
        policy_definition = get_policy_definition(bedrock_policy_client, AR_POLICY_ARN)
        
        # Create input for the ApplyGuardrails API call
        guardrail_input = [
            {"text": {"text": query, "qualifiers": ["query"]}},
            {"text": {"text": response, "qualifiers": ["guard_content"]}}
        ]

        # Call ApplyGuardrails and extract automated reasoning validation part from the response
        guardrails_output = runtime_client.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="OUTPUT",
            content=guardrail_input,
        )
        ar_validation_result = extract_automated_reasoning_validation_result(guardrails_output)

        # Rewrite the LLM response based on automated reasoning response
        rewriter = ResponseRewriter(policy_definition, domain="General")
        result = rewriter.rewrite_response(
            user_query=query,
            llm_response=response,
            ar_findings=ar_validation_result,
            model_id=model_id,
            bedrock_runtime_client=runtime_client
        )
            
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str, indent=2)
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}