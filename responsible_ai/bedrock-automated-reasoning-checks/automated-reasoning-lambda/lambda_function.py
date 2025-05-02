import boto3
import botocore
import json
import os
from botocore.session import Session

# Configuration
DEFAULT_GUARDRAIL_NAME = "<DEFAULT_GUARDRAIL_NAME>"
AR_POLICY = "<AR_POLICY_ID>"
AR_POLICY_VERSION = "<AR_POLICY_VERSION>" # e.g "1"
REGION = "us-west-2" #or any region where AR is allow-listed accounts

# Model ID mapping
MODEL_MAPPING = {
    "nova_lite": "us.amazon.nova-lite-v1:0",     # Using cross-region inference profile
    "nova_micro": "us.amazon.nova-micro-v1:0",   # Using cross-region inference profile
    "nova_pro": "us.amazon.nova-pro-v1:0",       # Using cross-region inference profile
    "claude_3_5_sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude_3_5_haiku": "anthropic.claude-3-5-haiku-20241022-v1:0"  # Default model
}

# Default model if not specified
DEFAULT_MODEL = "claude_3_5_haiku"

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

def generate_corrected_response(runtime_client, query, response, automated_reasoning, model_type=DEFAULT_MODEL):
    """Generate corrected response using the specified model based on reasoning results."""
    # Quick validation
    if not automated_reasoning or "findings" not in automated_reasoning:
        return None
        
    findings = automated_reasoning.get("findings", [])
    if not findings:
        return None
    
    result = findings[0].get("result")
    suggestions = findings[0].get("suggestions", [])
    
    if result == "VALID":
        # Handle valid responses with rules descriptions
        rule_descriptions = []
        for rule in findings[0].get("rules", []):
            if "description" in rule:
                rule_descriptions.append(rule["description"])
        
        if not rule_descriptions:
            return None
            
        correction_message = (
            "Your answer is valid based on the policy rules. Enhance it with more specific policy details.\n\n"
            f"<policy_rules>\n{'. '.join(rule_descriptions)}\n</policy_rules>\n\n"
            "Use these policy rules to add more specific details to your response. Ensure your enhanced answer "
            "maintains accuracy while providing more comprehensive policy information. "
            "Do not mention that you received feedback or reference rules verbatim."
        )
    
    elif result == "SATISFIABLE":
        # Handle satisfiable responses with assumptions
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
            f"<policy_rules>\n{'. '.join(rule_descriptions)}\n</policy_rules>\n\n"
            "Apply these policy rules in the context of the original query. Ensure your response "
            "accurately reflects the policy rules and maintains consistency with the "
            "original situation. Translate these code-like values to natural language. "
            "Do not mention that you received feedback or reference rules verbatim."
        )
    
    elif result == "NOT_UNDERSTOOD":
        # Handle not understood responses
        correction_message = (
            "The policy evaluation could not reach a definitive conclusion due to computational limits "
            "or complexity in the query. Please provide a response that:\n\n"
            "1. Acknowledges the complexity of the question\n"
            "2. Explains that policy details need to be carefully reviewed\n"
            "3. Suggests consulting with HR or a policy administrator for definitive guidance\n"
            "4. Outlines general principles that might be relevant without making specific claims\n\n"
            "Frame this as a helpful, cautious response without mentioning computational limitations."
        )
    
    else:
        return None
    
    # Build prompt
    prompt = f"Original query: {query}\n\nOriginal response: {response}\n\n{correction_message}\n\nPlease provide a more accurate response:"
    
    # Get model ID from the mapping
    model_id = MODEL_MAPPING.get(model_type, MODEL_MAPPING[DEFAULT_MODEL])
    
    print(f"Attempting to use model: {model_type} (ID: {model_id})")
    
    # Call foundation model using converse API
    try:
        # Use converse API for all models
        converse_response = runtime_client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]
        )
        
        # Extract content from converse response format
        response_content = converse_response['output']['message']['content'][0]['text']
        print(f"Successfully received response using converse API with {model_id}")
        return response_content
        
    except Exception as converse_error:
        print(f"Error with converse API: {converse_error}")
        
        # Fall back to invoke_model as a backup with model-specific formatting
        try:
            print(f"Falling back to invoke_model API for {model_id}")
            
            if "anthropic.claude" in model_id:
                # Claude models
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": prompt}]
                }
            elif "nova" in model_id:
                # Nova models - try with standard format first
                request_body = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 1000,
                        "temperature": 0.7,
                        "stopSequences": []
                    }
                }
            else:
                print(f"No fallback format available for model type: {model_id}")
                return None
                
            model_response = runtime_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response based on model type
            if "claude" in model_id:
                response_content = json.loads(model_response['body'])['content'][0]['text']
            elif "nova" in model_id:
                response_content = json.loads(model_response['body'])['results'][0]['outputText']
            else:
                print(f"Unsupported model type for response parsing: {model_id}")
                return None
                
            print(f"Successfully received response using invoke_model fallback with {model_id}")
            return response_content
            
        except Exception as invoke_error:
            print(f"Error with invoke_model fallback: {invoke_error}")
            
            # If Nova model with cross-region prefix and standard format failed, try with message format
            if "nova" in model_id and "us." in model_id:
                try:
                    print(f"Trying cross-region format for Nova model: {model_id}")
                    request_body = {
                        "messages": [
                            {
                                "role": "user", 
                                "content": [{"text": prompt}]
                            }
                        ],
                        "temperature": 0.7,
                        "topP": 0.9,
                        "maxTokens": 1000
                    }
                    
                    model_response = runtime_client.invoke_model(
                        modelId=model_id,
                        body=json.dumps(request_body)
                    )
                    
                    # Parse response
                    response_body = json.loads(model_response['body'])
                    if 'output' in response_body and 'message' in response_body['output']:
                        response_content = response_body['output']['message']['content'][0]['text']
                    else:
                        response_content = response_body['results'][0]['outputText']
                        
                    print(f"Successfully received response using cross-region format for {model_id}")
                    return response_content
                    
                except Exception as cross_region_error:
                    print(f"All attempts failed for model {model_id}: {cross_region_error}")
                    import traceback
                    traceback.print_exc()
                    return None
            
            import traceback
            traceback.print_exc()
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
                    "policyVersion": AR_POLICY_VERSION
                },
                blockedInputMessaging='Input is blocked',
                blockedOutputsMessaging='Output is blocked',
            )
            guardrail_id = create_resp["guardrailId"]
            guardrail_version = create_resp["version"]

        # Apply guardrail
        query = event.get('query')
        response = event.get('response')
        # Parameters for correction control
        include_corrected_response = event.get('include_corrected_response', True)
        # New parameter for model selection
        model_type = event.get('model_type', DEFAULT_MODEL)
        
        # Validate input parameters
        if not query or not response:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters: query and response'})
            }
        
        # Validate model type
        if model_type not in MODEL_MAPPING:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f"Invalid model_type: {model_type}. Valid options are: {', '.join(MODEL_MAPPING.keys())}"})
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
        
        # Check if we have empty findings - this is our "No relevant findings" case
        has_findings = (automated_reasoning and 
                        "findings" in automated_reasoning and 
                        automated_reasoning["findings"] and 
                        len(automated_reasoning["findings"]) > 0)
        
        # Generate corrected response only if the feature is enabled and we have findings
        corrected_response = None
        if include_corrected_response and has_findings:
            corrected_response = generate_corrected_response(
                runtime_client, 
                query, 
                response, 
                automated_reasoning, 
                model_type
            )
        
        result = {
            'input': guardrail_input,
            'automatedReasoning': automated_reasoning,
            'model_used': MODEL_MAPPING.get(model_type),
            'has_findings': has_findings  # Add this flag to indicate whether we have findings or not
        }
        
        # Include corrected_response in the result only if it was generated
        if include_corrected_response and has_findings and corrected_response:
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