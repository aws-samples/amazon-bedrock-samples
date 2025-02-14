import os
import json
from pprint import pprint
import boto3
from datetime import datetime
from typing import Dict, Any, List
from config import generate_instruction, VACATION_API_SCHEMA, BUDGET_API_SCHEMA, COMPENSATION_API_SCHEMA

def create_bedrock_client(region: str = "us-east-1"):
    return boto3.client(
        "bedrock-agent-runtime", 
        region_name="us-east-1"
    )

# Global variable to store resources
RESOURCES = {}

def load_resources(resources_file: str = "resources_info.json") -> Dict:
    """Load resources information from resources.json file."""
    global RESOURCES
    
    if not os.path.exists(resources_file):
        raise FileNotFoundError(f"Resources file {resources_file} not found")
        
    with open(resources_file, 'r') as f:
        RESOURCES = json.load(f)
    
    return RESOURCES

def get_lambda_arn(lambda_name: str) -> str:
    """Get Lambda ARN from loaded resources."""
    if not RESOURCES:
        load_resources()
    return RESOURCES['lambda'][lambda_name]['full_response']['FunctionArn']

def get_kb_id() -> str:
    """Get Knowledge Base ID from loaded resources."""
    if not RESOURCES:
        load_resources()
    return RESOURCES['knowledge_base']['kb_id']

def load_lambda_functions_info(input_file: str = "lambda_functions_info.json") -> Dict:
    """Load Lambda functions information from a JSON file."""
    if not os.path.exists(input_file):
        return {}
        
    with open(input_file, 'r') as f:
        return json.load(f)

def get_available_tools() -> Dict:
    """Generate the action group configuration using the Lambda functions information."""
    return {
        'code_interpreter': {
            'access_level': ['basic', 'Employee', 'Manager'],
            'config': {
                'actionGroupName': 'CodeInterpreterAction',
                'parentActionGroupSignature': 'AMAZON.CodeInterpreter'
            }
        },
        'compensation': {
            'access_level': ['Manager'],
            'config': {
                'actionGroupName': 'PerformanceEvaluation',
                'actionGroupExecutor': {
                    'lambda': get_lambda_arn('compensation')
                },
                'apiSchema': {
                    'payload': COMPENSATION_API_SCHEMA
                },
                'description': 'Used for submitting employee pay change raise request to HR team.'
            }
        },
        'vacation_tool': {
            'access_level': ['Employee', 'Manager'],
            'config': {
                'actionGroupName': 'VacationManagement',
                'actionGroupExecutor': {
                    'lambda': get_lambda_arn('vacation')
                },
                'apiSchema': {
                    'payload': VACATION_API_SCHEMA
                },
                'description': 'Manage vacation requests and check balance'
            }
        },
        'budget_tool': {
            'access_level': ['Employee', 'Manager'],
            'config': {
                'actionGroupName': 'FetchDetails',
                'actionGroupExecutor': {
                    'lambda': get_lambda_arn('budget')
                },
                'apiSchema': {
                    'payload': BUDGET_API_SCHEMA
                },
                'description': 'Process bills for approval.'
            }
        }
    }

def get_allowed_action_groups(access_level: str = 'basic', selected_tools: List[str] = None) -> List[Dict]:
    """
    Get allowed action groups based on access level and selected tools
    Always includes code interpreter as a basic tool
    """
    available_tools = get_available_tools()
    allowed_tools = []

    # Always add code interpreter as a basic tool
    allowed_tools.append(available_tools['code_interpreter']['config'])

    # If no specific tools are selected, return just the basic tools
    if not selected_tools:
        return allowed_tools

    # Add other selected tools if user has appropriate access
    for tool_id in selected_tools:
        tool = available_tools.get(tool_id)
        if tool and access_level in tool['access_level']:
            allowed_tools.append(tool['config'])

    return allowed_tools

def configure_knowledge_base(access_level, 
                           kb_description = 'This knowledge base contains information about Octank Inc. company HR policy, performance, code of conduct etc. Only managers has access to certain content like performance, bonus, and compensation'):
    kb_id = get_kb_id()
    
    if access_level != 'Manager':
        access_filter = {
                        "equals": {
                            "key": "access_level",
                            "value": "Basic"
                        }
            }
        return {
            "knowledgeBaseId": kb_id,
            "description": kb_description,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "filter": access_filter,
                    "numberOfResults": 2,
                    "overrideSearchType": "HYBRID"
                }
            }
        }
    else:
        access_filter = {
                        "equals": {
                            "key": "access_level",
                            "value": "Manager"
                        }
            }
        return {
            "knowledgeBaseId": kb_id,
            "description": kb_description,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "filter": access_filter,
                    "numberOfResults": 2,
                    "overrideSearchType": "HYBRID"
                }
            }
        }

def prepare_request_params(
    input_text: str,
    persona_id: str = "professional",
    foundation_model: str = "anthropic.claude-3-sonnet-20240229-v1:0",
    session_id: str = "default-session",
    end_session: bool = False,
    enable_trace: bool = True,
    access_level: str = "basic",
    selected_tools: List[str] = None
) -> Dict[str, Any]:
    
    # Get allowed action groups based on access level and selected tools
    action_groups = get_allowed_action_groups(access_level, selected_tools)
    
    # Generate instruction combining persona tone and tool capabilities
    instruction = generate_instruction(persona_id, selected_tools, foundation_model)

    # Get KB info:
    if "knowledge_base" in selected_tools:
        kb_config = configure_knowledge_base(access_level)
        return {
            "inputText": input_text,
            "instruction": instruction,
            "foundationModel": foundation_model,
            "sessionId": session_id,
            "endSession": end_session,
            "enableTrace": enable_trace,
            "actionGroups": action_groups,
            "knowledgeBases": [kb_config]
        }
    else:
        return {
            "inputText": input_text,
            "instruction": instruction,
            "foundationModel": foundation_model,
            "sessionId": session_id,
            "endSession": end_session,
            "enableTrace": enable_trace,
            "actionGroups": action_groups
        }

def invoke_bedrock_agent(rt_client, request_params: Dict[str, Any]) -> Dict[str, Any]:
    print("invoking-agent")
    response = rt_client.invoke_inline_agent(**request_params)
    
    completion = ""
    traces = []
    
    for event in response.get("completion"):
        if "trace" in event:
            traces.append(event["trace"])
        else:
            chunk = event["chunk"]
            completion = completion + chunk["bytes"].decode()

    return {
        "request_id": response['ResponseMetadata']['RequestId'],
        "completion": response.get("completion"),
        "full_response": response,
        "processed_completion": completion,
        "traces": traces
    }

def save_interaction(request_params: Dict[str, Any], response_data: Dict[str, Any]) -> str:
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "request_id": response_data["request_id"],
        "request_params": request_params,
        "response": {
            "completion": response_data["processed_completion"],
            "trace": response_data["traces"],
            "ResponseMetadata": response_data["full_response"].get('ResponseMetadata')
        }
    }

    filename = f"agent_interaction_{response_data['request_id']}.json"
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    return filename