import json
from datetime import datetime
from typing import Any, Dict, List
import inspect
import boto3
from pydantic import BaseModel, Field, create_model

### Constants and boto3 client setup
region = "us-west-2"
bedrock = boto3.client("bedrock-runtime", region_name=region)
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

### Functions
### Define decorator for bedrock tools
def bedrock_tool(name, description):
    def decorator(func):
        input_model = create_model(
            func.__name__ + "_input",
            **{
                name: (param.annotation, param.default)
                for name, param in inspect.signature(func).parameters.items()
                if param.default is not inspect.Parameter.empty
            },
        )

        func.bedrock_schema = {
            'toolSpec': {
                'name': name,
                'description': description,
                'inputSchema': {
                    'json': input_model.schema()
                }
            }
        }
        return func

    return decorator

### Tools definition - DEFINE ALL YOUR TOOLS HERE!!!  ###
class ToolsList:
    @bedrock_tool(
        name="get_weather",
        description="Get weather of a location."
    )
    def get_weather(self, city: str = Field(..., description="City of the location"),
                    state: str = Field(..., description="State of the location")):
        result = f'Weather in {city, state} is 70F and clear skies.'
        return result

### Convert tools schema to bedrock tool config
toolConfig = {
    'tools': [tool.bedrock_schema for tool in ToolsList.__dict__.values() if hasattr(tool, 'bedrock_schema')],
    'toolChoice': {'auto': {}}
}

### Function for invoking Bedrock Converse
def converse_with_tools(modelId, messages, system='', toolConfig=None):
    return bedrock.converse(
        modelId=modelId,
        system=system,
        messages=messages,
        toolConfig=toolConfig
    )

### Orchestration workflow with messages
def converse(tool_class, modelId, prompt, system='', toolConfig=None):
    ### First invocation
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    print(f"{datetime.now():%H:%M:%S} - Invoking model...")
    output = converse_with_tools(modelId, messages, system, toolConfig)
    messages.append(output['output']['message'])
    print(f"{datetime.now():%H:%M:%S} - Got output from model...")
    ### Check if function calling
    function_calling = [c['toolUse'] for c in output['output']['message']['content'] if 'toolUse' in c]
    if function_calling:
        tool_result_message = {"role": "user", "content": []}
        for function in function_calling:
            print(f"{datetime.now():%H:%M:%S} - Function calling - Calling tool...")
            tool_name = function['name']
            tool_args = function['input'] or {}
            ### Calling the tool
            tool_response = getattr(tool_class, tool_name)(**tool_args)
            print(f"{datetime.now():%H:%M:%S} - Function calling - Got tool response...")
            ### Add tool response to message
            tool_result_message['content'].append({
                'toolResult': {
                    'toolUseId': function['toolUseId'],
                    'content': [{"text": tool_response}]
                }
            })
        messages.append(tool_result_message)
        print(f"{datetime.now():%H:%M:%S} - Function calling - Calling model with result...")
        ### Second invocation with tool result
        output = converse_with_tools(modelId, messages, system, toolConfig)
        messages.append(output['output']['message'])
        print(f"{datetime.now():%H:%M:%S} - Function calling - Got final answer.")
    return messages, output

### Prompts
### ADJUST YOUR SYSTEM PROMPT HERE - IF DESIRED ###
system_prompt = [{"text":"You're provided with a tool that can get the weather information for a specific location 'get_weather'; \
                              only use the tool if required. You can call the tool multiple times if required. \
                              Don't make reference to the tools in your final answer."}]
### REPLACE WITH YOUR OWN PROMPTS HERE ###
prompt = "What is the weather in Paris and in Berlin?"

### Invocation
messages, output = converse(ToolsList(), MODEL_ID, prompt, system_prompt, toolConfig)
print(f"Output:\n{output['output']['message']['content'][0]['text']}\n")
print(f"Messages:\n{json.dumps(messages, indent=2, ensure_ascii=False)}\n")
