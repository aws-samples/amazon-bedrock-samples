import boto3
import botocore
import json
import os
from botocore.session import Session

# Configuration
DEFAULT_GUARDRAIL_NAME = "<DEFAULT_GUARDRAIL_NAME>"
AR_POLICY = "<AR_POLICY_ID>"
REGION = "us-west-2" #Region - AR checks is currently available in us-west-2 for allow-listed accounts

def register_custom_models():
    try:
        print(f"Current directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir('.')}")
        
        # Use absolute path from Lambda runtime
        base_path = '/var/task'
        bedrock_file = os.path.join(base_path, 'models', 'bedrock-2023-04-20.api.json')
        runtime_file = os.path.join(base_path, 'models', 'bedrock-runtime-2023-09-30.api.json')
        
        print(f"Loading models from: {bedrock_file} and {runtime_file}")
        
        # Create a custom session for loading the models
        custom_session = Session()
        loader = custom_session.get_component('data_loader')
        
        # Monkey-patch the loader to use our custom model files
        original_load_service_model = loader.load_service_model
        
        def custom_load_service_model(service_name, type_name, *args, **kwargs):
            if service_name == 'bedrock' and type_name == 'service-2':
                with open(bedrock_file, 'r') as f:
                    return json.load(f)
            elif service_name == 'bedrock-runtime' and type_name == 'service-2':
                with open(runtime_file, 'r') as f:
                    return json.load(f)
            else:
                return original_load_service_model(service_name, type_name, *args, **kwargs)
        
        # Apply the monkey patch
        loader.load_service_model = custom_load_service_model
        
        # Create a new boto3 session that will use our custom loader
        return boto3.Session(botocore_session=custom_session, region_name=REGION)
    
    except Exception as e:
        print(f"Error registering custom models: {e}")
        if isinstance(e, FileNotFoundError):
            print(f"File not found. Contents of /var/task: {os.listdir('/var/task')}")
            if os.path.exists('/var/task/models'):
                print(f"Contents of /var/task/models: {os.listdir('/var/task/models')}")
        return None

def find_guardrail_id(client, name):
    resp = client.list_guardrails()
    for g in resp["guardrails"]:
        if g["name"] == name:
            return g["id"], g["version"]
    return None, None

def generate_corrected_response(runtime_client, query, response, automated_reasoning):
    """Generate corrected response using Claude 3 Haiku based on reasoning results."""
    # Quick validation
    if not automated_reasoning or "findings" not in automated_reasoning:
        return None
        
    findings = automated_reasoning.get("findings", [])
    if not findings:
        return None
    
    result = findings[0].get("result")
    suggestions = findings[0].get("suggestions", [])
    
    if result == "VALID":
        # Handle valid but incomplete responses with assumptions
        assumptions = []
        for suggestion in suggestions:
            if suggestion.get("type") == "ASSUMPTION":
                assumptions.append(f"{suggestion.get('key')}: {suggestion.get('value')}")
        
        if not assumptions:
            return None
            
        correction_message = (
            "The core answer is correct, but please enhance it with relevant policy details. "
            "Below are logical assumptions that were verified during analysis:\n\n"
            f"<assumptions>\n{', '.join(assumptions)}\n</assumptions>\n\n"
            "Focus only on the key policy implications related to eligibility criteria. "
            "Do not incorporate specific employee circumstances unless directly relevant to the question. "
            "Keep your response general and policy-focused. "
            "Do not mention that you received feedback or list assumptions."
        )
    
    elif result == "INVALID":
        # Handle invalid responses with corrections and rules
        corrections = []
        for suggestion in suggestions:
            if suggestion.get("type") == "CORRECTION":
                corrections.append(f"{suggestion.get('key')}: {suggestion.get('value')}")
        
        rule_descriptions = []
        for rule in findings[0].get("rules", []):
            if "description" in rule:
                rule_descriptions.append(rule["description"])
        
        if not corrections and not rule_descriptions:
            return None
            
        correction_message = (
            "Your answer contains inaccuracies. Rewrite it using the feedback below.\n\n"
            f"<corrections>\n{', '.join(corrections)}\n</corrections>\n\n"
            f"<policy_rules>\n{'. '.join(rule_descriptions)}\n</policy_rules>\n\n"
            "Apply these policy rules in the context of the original query. Ensure your response "
            "accurately reflects the policy rules and maintains consistency with the"
            "original situation. Translate these code-like values to natural language. "
            "Do not mention that you received feedback or reference rules verbatim."
        )
    
    else:
        return None
    
    # Build prompt
    prompt = f"Original query: {query}\n\nOriginal response: {response}\n\n{correction_message}\n\nPlease provide a more accurate response:"
    
    # Call FM
    try:
        claude_response = runtime_client.invoke_model(
            modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        return json.loads(claude_response['body'])['content'][0]['text']
    except Exception as e:
        print(f"Error generating corrected response: {e}")
        return None

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
        
        # Create or find guardrail
        guardrail_id, guardrail_version = find_guardrail_id(bedrock_client, DEFAULT_GUARDRAIL_NAME)
        
        if guardrail_id is None:
            create_resp = bedrock_client.create_guardrail(
                name=DEFAULT_GUARDRAIL_NAME,
                description="Automated Reasoning checks demo guardrail",
                automatedReasoningPolicyConfig={
                    "policyIdentifier": AR_POLICY,
                    "policyVersion": "1"
                },
                blockedInputMessaging='Input is blocked',
                blockedOutputsMessaging='Output is blocked',
            )
            guardrail_id = create_resp["guardrailId"]
            guardrail_version = create_resp["version"]

        # Apply guardrail
        query = event.get('query')
        response = event.get('response')
        # New parameter to control whether to include corrected response
        include_corrected_response = event.get('include_corrected_response', True)
        
        # Validate input parameters
        if not query or not response:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters: query and response'})
            }
        
        guardrail_input = [
            {"text": {"text": query, "qualifiers": ["query"]}},
            {"text": {"text": response, "qualifiers": ["guard_content"]}}
        ]

        guardrails_output = runtime_client.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="OUTPUT",
            content=guardrail_input,
        )
        
        # Extract just the automatedReasoningPolicy part
        automated_reasoning = None
        if 'assessments' in guardrails_output and guardrails_output['assessments']:
            if 'automatedReasoningPolicy' in guardrails_output['assessments'][0]:
                automated_reasoning = guardrails_output['assessments'][0]['automatedReasoningPolicy']
        
        # Generate corrected response only if the feature is enabled
        corrected_response = None
        if include_corrected_response:
            corrected_response = generate_corrected_response(runtime_client, query, response, automated_reasoning)
        
        result = {
            'input': guardrail_input,
            'automatedReasoning': automated_reasoning
        }
        
        # Include corrected_response in the result only if it was generated
        if include_corrected_response:
            result['corrected_response'] = corrected_response
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str, indent=2)
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}