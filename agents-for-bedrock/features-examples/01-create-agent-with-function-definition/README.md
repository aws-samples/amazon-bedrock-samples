# Create Agents with Function Definition

In this folder, we provide an example of an HR agent using Agents for Amazon Bedrock new capabilities for function definition.

The agent connects with an in-memory SQLite database that contains generated data about employee's available vacation days and planned time off.

The database structure created is as following:

<img src="images/HR_DB.png" style="width:50%;display:block;margin: 0 auto;">

The agent allows the employee to `get_available_vacations_days` and `reserve_vacation_time` according to the employee's requests.

The code below shows the definition of the functions as a list of JSON objects that is passed to the Agent's Action group via the `functionSchema` parameter
```python
    agent_functions = [
        {
            'name': 'get_available_vacations_days',
            'description': 'get the number of vacations available for a certain employee',
            'parameters': {
                "employee_id": {
                    "description": "the id of the employee to get the available vacations",
                    "required": True,
                    "type": "integer"
                }
            }
        },
        {
            'name': 'reserve_vacation_time',
            'description': 'reserve vacation time for a specific employee',
            'parameters': {
                "employee_id": {
                    "description": "the id of the employee for which time off will be reserved",
                    "required": True,
                    "type": "integer"
                },
                "start_date": {
                    "description": "the start date for the vacation time",
                    "required": True,
                    "type": "string"
                },
                "end_date": {
                    "description": "the end date for the vacation time",
                    "required": True,
                    "type": "string"
                }
            }
        },
    ]
    agent_action_group_response = bedrock_agent_client.create_agent_action_group(
        agentId=agent_id,
        agentVersion='DRAFT',
        actionGroupExecutor={
            'lambda': lambda_function['FunctionArn']
        },
        actionGroupName=agent_action_group_name,
        functionSchema={
            'functions': agent_functions
        },
        description=agent_action_group_description
    )
```

Both actions are implemented as part of an AWS Lambda function that receives the inputs from the Agent via an event.

The event has the following structure:

```json
{
    "messageVersion": "1.0", 
    "agent": {
        "alias": "<AGENT_ALIAS>", 
        "name": "hr-assistant-function-def", 
        "version": "<AGENT_VERSION>",
        "id": "<AGENT_ID>"
    }, 
    "sessionId": "<SESSION_ID>", 
    "sessionAttributes": {
        "<ATTRIBUTE_NAME>": "# Session attributes to be addressed in example 06-prompt-and-session-attributes"
    }, 
    "promptSessionAttributes": {
        "<PROMPT_NAME>": "# Session attributes to be addressed in example 06-prompt-and-session-attributes"
    }, 
    "inputText": "<USER_INPUT_TEXT>", 
    "actionGroup": "VacationsActionGroup", 
    "function": "<FUNCTION_TRIGGERED_BY_USER_INPUT_TEXT>", 
    "parameters": [{
        "<PARAM_1>": "<PARAM_1_VAL>", 
        "<PARAM_2>": "<PARAM_2_VAL>", 
        "<PARAM_N>": "<PARAM_N_VAL>"
    }]
}
```

To process the action that the Agent is invoking, the following code is added to the Lambda function:

```python
def lambda_handler(event, context):
    action_group = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    
    # setting expected response body
    responseBody =  {
        "TEXT": {
            "body": "sample response"
        }
    }
    
    # Logic to process the requested action goes here
    ...
    
    # Lastly, return the response back to the agent
    action_response = {
        'actionGroup': action_group,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    function_response = {
        'response': action_response, 
        'messageVersion': event['messageVersion']
    }
    return function_response
```