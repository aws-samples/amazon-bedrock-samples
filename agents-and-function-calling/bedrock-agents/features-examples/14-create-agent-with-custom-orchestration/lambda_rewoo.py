#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import re
import uuid
import xml.etree.ElementTree as ET

tool_state = {
    "plan": None,
    "tool_state": {
        "last_tool_used": None,
        "last_tool_result": None,
        "parent_tool_result": None,
        "is_summary": False
    }
}


# Entry point for the orchestration lambda
def lambda_handler(event, context):
    print(f"The incoming event: {json.dumps(event)}")
    
    # Extract state from the event
    state = event.get("state", '')
    print(f"Current state: {state}")

    event_response = nextEvent(event)
    print(f"Response Event: {event_response}")
    return event_response


# Determines the next state of the Agent
def nextEvent(event): 
    # Possible Current States:
    # START - Start of the conversation turn
    # MODEL_INVOKED - Model has been invoked and next action to be determined
    # TOOL_INVOKED - Tool has been invoked and next action needs to be determined

    # Resulting States:
    # INVOKE_MODEL - Invokes the model
    # INVOKE_TOOL - Invokes a Tool (i.e. vacation_days)
    # FINISH - Conversation turn is completed

    incoming_state = event.get("state", {})
    _state = {}

    # Invoke the model if this is the start of the conversation turn
    if incoming_state == 'START': 
        response_event = 'INVOKE_MODEL'
        response_trace = "This is on start debug trace!"
        payload_data = json.dumps(create_prompt(event, create_planning_system_prompt))

    # If the model was invoked then either finish the conversation or invoke a tool
    elif incoming_state == 'MODEL_INVOKED': 
        if is_end_state(event):
            response_event = 'FINISH'
            response_trace = "This is on finish debug trace!"
            payload_data = json.dumps(get_end_turn_payload(event))
        else:
            response_event = 'INVOKE_TOOL'
            response_trace = "This is on tool use debug trace!"
            payload_data, _state = execute_plan_on_generation(event)
            payload_data = json.dumps(payload_data)

    # If the invoked tool was incorrect invoke tool again, else invoke model
    elif incoming_state == 'TOOL_INVOKED':
        # process results and determine next tool
        payload_data, _state = continue_execution(event) 
        if payload_data:
            response_event = 'INVOKE_TOOL'
            response_trace = "This is on tool use debug trace!"
            payload_data = json.dumps(payload_data)
        else:
            # Reset the tool state and INVOKE_MODEL again
            _state = {
                "plan": None,
                "tool_state": {
                    "last_tool_used": None,
                    "parent_tool_result": None,
                    "last_tool_result": None,
                    "is_summary": True
                }
            }
            response_event = 'INVOKE_MODEL'
            response_trace = "This is on model invocation debug trace!"
            payload_data = json.dumps(create_prompt(event, create_summary_system_prompt))

    # Incorrect state provided, error returned
    else:
        raise 'Invalid state provided!'

    # temp work around, to be removed
    _lambda_arn = event.get("context", {}).get("sessionAttributes", {}).get("lambda", None)

    event["context"] = {
        "sessionAttributes": {
            "state": json.dumps(_state),
            "lambda": _lambda_arn
        }
    }
    payload = create_payload(payload_data, response_event, response_trace, event.get("context", {}))
    return payload


# Processes the result of a tool invocation and determines the next tool to use.
def continue_execution(event):
    # get the session state from context
    _state = json.loads(event.get("context", {}).get("sessionAttributes", {}).get("state", {}))

    # get the plan from context
    _plan = _state.get("plan", "")

    # get the last tool invoked from context
    _tool_state = _state.get("tool_state", {})

    # get the last tool result
    _tool_result = json.loads(event.get("input", {}).get("text", {})).get("toolResult", {})

    # update context with last tool result
    _tool_state["last_tool_result"] = _tool_result.get("content", {})[0].get("text", "")
    if not _tool_state["parent_tool_result"]:
        _tool_state["parent_tool_result"] = _tool_result.get("content", {})[0].get("text", "")

    tool_to_use, function_signature, parent_tool_result = get_tool_to_execute(_plan, _tool_state)
    _current_plan = _plan

    if tool_to_use:
        _state = {
            "plan": _current_plan,
            "tool_state": {
                "last_tool_used": function_signature,
                "parent_tool_result": parent_tool_result,
                "last_tool_result": None,
                "is_summary": False
            }
        }
        return tool_to_use, dict(_state)
    return None, None

# Extracts and executes the plan created by the model
def execute_plan_on_generation(event):
    _plan = json.loads(event.get("input", {}).get("text", {}))
    _plan = _plan.get("output", {}).get("content", {})[0].get("text", "").replace("\n", "")
    tool_to_use, function_signature, parent_tool_result = get_tool_to_execute(_plan)
    _state = {
        "plan": _plan,
        "tool_state": {
            "last_tool_used": function_signature,
            "parent_tool_result": parent_tool_result,
            "last_tool_result": parent_tool_result,
            "is_summary": False
        }
    }
    return tool_to_use, dict(_state)


# Parses the plan's XML and determines which tool to use next
def get_tool_to_execute(_plan, _tool_state=None):
    print("Plan:", _plan)
    # Extract plan between tags from _plan
    effective_plan = re.findall(r'<plan>(.*?)</plan>', _plan.strip(), re.DOTALL)[0].strip()
    tree = ET.ElementTree(ET.fromstring('<plan>' + effective_plan + '</plan>'))

    # Iterate through the plan 
    _to_continue_process = False
    for element in tree.iter():
        # If the element is a step, continue
        if 'step' in element.tag:
            plan_step = element.text
            for_step = element.find('for')

            # If there is a for tag within the element
            if for_step is not None and for_step.text:
                if for_step.attrib and 'expression' in for_step.attrib:
                    # get the for loop function (i.e. item in items)
                    for_loop = re.findall(r'(.*?)in(.*)', for_step.attrib.get('expression', '').strip(), re.DOTALL)[0]
                    iteration_var = for_loop[0].strip()
                    function = for_step.text.strip()
                    last_listed_responses = _tool_state.get("parent_tool_result", {})

                    # get the list of values to replace
                    var_to_replace = re.findall(f'={iteration_var}.(.*?),', function, re.DOTALL)[0].strip()
                    replaceable_values = find_value(last_listed_responses, var_to_replace)

                    for replaceable_value in replaceable_values:
                        function_param_filled = function.replace(f"{iteration_var}.{var_to_replace}", replaceable_value)
                        variable_name, repl_function = parse_tool(function_param_filled)

                        if (_tool_state is not None
                                and _tool_state.get("last_tool_used") == repl_function and not _to_continue_process):
                            _to_continue_process = True
                            continue

                        if _tool_state is not None and not _to_continue_process:
                            continue

                        return create_tool_use(repl_function), repl_function, last_listed_responses

            # If there is no text or no plan but the fn:: prefix is included
            elif 'fn::' in plan_step:
                # parse the tool to use from the step
                variable_name, function = parse_tool(plan_step)
                if _tool_state is not None and _tool_state.get("last_tool_used") == function and not _to_continue_process:
                    _to_continue_process = True
                    continue

                if _tool_state is not None and not _to_continue_process:
                    continue

                parent_tool_result = None
                if _tool_state is not None:
                    parent_tool_result = _tool_state.get("parent_tool_result")
                # Return the tool use
                return create_tool_use(function), function, parent_tool_result
    return None, None, None


# Find all the replaceable values
def find_value(string, key):
    results = []
    values = re.findall(f'"(.*?){key}(.*?)"(.*?):(.*?)"(.*?)"', string.strip(), re.DOTALL)
    if values:
        for value in values:
            if isinstance(value[4], str):
                results.append(str(f"\"{value[4]}\""))
            else:
                results.append(value[4])

    values = re.findall(f'"(.*?){key}(.*?)"(.*?)=(.*?)"(.*?)"', string.strip(), re.DOTALL)
    if values:
        for value in values:
            if isinstance(value[4], str):
                results.append(str(f"\"{value[4]}\""))
            else:
                results.append(value[4])

    return results


# extract function name and parameters from a plan step
def parse_tool(_plan_step):
    _current_plan = str(_plan_step.strip())
    variable_name = re.findall(r'(.*?)fn::', _current_plan, re.DOTALL)[0].replace('=', '').strip()
    function = re.findall(r'(.*?)fn::(.*)', _current_plan, re.DOTALL)[0][1].strip()
    return variable_name, function


# Prepares the payload for a tool invocation
def create_tool_use(_function):
    function = re.findall(r'(.*?)\((.*?)\)', _function.strip(), re.DOTALL)[0]
    predicted_params = function[1]
    params = dict(e.strip().split('=') for e in predicted_params.split(','))

    return {
        "toolUse": {
            "toolUseId": str(uuid.uuid4()),
            "name": function[0].replace("fn::", '').strip(),
            "input": params
        }
    }


# Checks the state object to determine if the conversation turn is complete
def is_end_state(event):
    _state = json.loads(event.get("context", {}).get("sessionAttributes", {}).get("state", {}))
    return _state.get("tool_state", {}).get("is_summary", "")


# Collect the final payload
def get_end_turn_payload(event):
    input = event.get("input", {}).get("text", "")
    json_input = json.loads(input)
    return json_input.get("output", {}).get("content", [])[0].get("text", "")


# Constructs the prompt for Bedrock
def create_prompt(event, _create_prompt_function):
    # Prepare the Bedrock Converse API request
    messages = construct_messages(event.get("context", {}), event.get("input", {}), _create_prompt_function)
    return create_converse_api_prompt(event.get("context", {}), messages)


# Formats the response payload for the next event
def create_payload(payload_data, action_event, trace_data, context):
    response = {
        "version": "1.0",
        "actionEvent": action_event,
        "output": {
            "text": payload_data,
            "trace": {
                "event": {
                    "text": trace_data
                }
            }
        },
        "context": {
            "sessionAttributes": context.get("sessionAttributes", {}),
            "promptSessionAttributes": context.get("promptSessionAttributes", {})
        }
    }
    return response


# Prepare the Bedrock Converse API request
def create_converse_api_prompt(context, messages):
    #Note for models:
    #"meta.llama3-8b-instruct-v1:0" # no tool support in streaming/non-streaming mode; in us-west-2
    #"mistral.mistral-small-2402-v1:0"  # no tool support in streaming mode; in us-east-1

    model_id = context.get("agentConfiguration", {}).get("defaultModelId", '')

    tools = context.get("agentConfiguration", {}).get("tools", {})
    bedrock_converse_api_request = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": 500,
            "temperature": 0,
            "topP": 0.9
        },
        "toolConfig": {
            "tools": tools
        }
    }
    # Return the converse api request
    return bedrock_converse_api_request


# Reconstruct the conversation history
def construct_messages(context, input, _create_prompt_function):
    conversations_in_session = context.get("session", {})
    messages = []

    for turn in conversations_in_session:
        if turn:
            intermediary_steps = turn.get("intermediarySteps", {})
            for intermediary_step in intermediary_steps:
                if intermediary_step:
                    orchestration_input = intermediary_step.get("orchestrationInput", {})
                    orchestration_output = intermediary_step.get("orchestrationOutput", {})

                    if orchestration_input.get("state", '') == "START":
                        messages.append(message('user', {'text': orchestration_input.get("text", '')}))

                    if _create_prompt_function == create_summary_system_prompt:
                        if orchestration_input.get("state", '') == 'MODEL_INVOKED':
                            messages.append(json.loads(orchestration_input.get("text", {})).get("output", {}))

                        if orchestration_input.get("state", '') == 'TOOL_INVOKED':
                            messages.append(message('user', json.loads(orchestration_input.get("text", {}))))

                        if orchestration_output.get("event", '') == 'INVOKE_TOOL':
                            messages.append(message('assistant', json.loads(orchestration_output.get("text", {}))))

    if input:
        text = json.loads(input.get("text", {}))
        message_content = text
        if "text" in text and _create_prompt_function == create_summary_system_prompt:
            message_content = {"text": text.get("text", "") + "\n\n" + _create_prompt_function(context)}
        elif "text" in text and _create_prompt_function == create_planning_system_prompt:
            message_content = {"text": create_planning_system_prompt(context) + "\n\n" + text.get("text", "")}
        messages.append(message("user", message_content))

    return merge_conversation_turn(messages, context)


# Merges conversation history into single formatted message
def merge_conversation_turn(messages, context):
    model_id = context.get("agentConfiguration", {}).get("defaultModelId", '').lower()
    
    if not messages:
        return messages
    last_role = ''
    merged_messages = []
    for _message in messages:
        if last_role == _message.get("role", ""):
            merged_messages[len(merged_messages) - 1]["content"] = _message.get("content")
        else:
            merged_messages.append(_message)
        last_role = _message.get("role")
    return merged_messages


# helper function for construct messages - formats in Bedrock Converse format
def message(role, content):
    return {
        "role": role,
        "content": [content]
    }


# Prompt used at beginning of conversation turn to create a plan (Orchestration template)
def create_planning_system_prompt(context):
    prompt_variables = ""
    if "promptSessionAttributes" in context:
        for attribute in context['promptSessionAttributes']:
            prompt_variables += "<context>"
            prompt_variables += f"   <key>{attribute}</key>"
            value = context['promptSessionAttributes'][attribute]
            prompt_variables += f"  <value>{value}</value>"
            prompt_variables += "</context>"

    return f"""
{context.get("agentConfiguration", {}).get("instruction", '')}
Create a structured execution plan using the following format:

<plan>
    <step_[number]> operation </step_[number]>
</plan>

Rules:
1. Each step must contain exactly one function call or control structure
2. Function calls syntax: result=fn::FunctionName(param=value)
3. Control structures:
   - For loops: 
     <for expression="item in collection">
         operation
     </for>
   - If conditions:
     <if expression="condition">
         operation
     </if>

4. Variable assignments must use '='
5. Return statements must be in final step
6. All steps must be numbered sequentially
7. Each operation must be self-contained and atomic

Example:
Input: Process items with function X(input=A)->B then Y(input=B)->C

<plan>
    <step_1>
        results = []
        <for expression="item in items">
            B=fn::X(input=item)
            C=fn::Y(input=B)
            results.append(C)
        </for>
    </step_1>
    <step_2> return results </step_2>
</plan>
<guidelines>
- Never assume any parameter values while invoking a function. 
- You should always provide the value of parameters to the plan, do not abstract it away as variables.
</guidelines>

Please provide the execution plan following these specifications.
Here are some context information that you can use while creating the plan:
{prompt_variables}
"""


def create_summary_system_prompt(context):
    return f"""
Given the previous conversation, answer the user's question.
"""
