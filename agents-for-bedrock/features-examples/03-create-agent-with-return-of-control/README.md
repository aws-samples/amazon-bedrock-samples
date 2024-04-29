# Create Agents with Return of Control (Function Calling)

In this folder, provide an example of an HR agent using Agents for Amazon Bedrock new capabilities for function definition and return of control for function calling.

The agent allows the employee to `get_available_vacations_days` and `book_vacations` according to the employee's requests.

Both functionalities are implemented in memory in the notebook and would be available in an existant applications for production use cases.

The notebook logic connects with a generated in-memory SQLite database that contains information about employee's available vacation days and planned holidays.

The database structure created is as following:

<img src="images/HR_DB.png" style="width:50%;display:block;margin: 0 auto;">

The agent allows the employee to `get_available_vacations_days` and `book_vacations` according to the employee's requests. The functions are defined using Function Definition as a list of JSON objects:

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
            'name': 'book_vacations',
            'description': 'book the vacation days for the employeed',
            'parameters': {
                "employee_id": {
                    "description": "the id of the employee to get the available vacations",
                    "required": True,
                    "type": "integer"
                },
                "start_date": {
                    "description": "the start date for the vacation booking",
                    "required": True,
                    "type": "string"
                },
                "end_date": {
                    "description": "the end date for the vacation booking",
                    "required": True,
                    "type": "string"
                }
            }
        },
    ]
```
When creating the Agent Action Group, the `actionGroupExecutor` parameter is set to `{'customControl': 'RETURN_CONTROL'}` to indicate that no Lambda function is provided and that the agent should return which function to call and with which parameters.

```python
    agent_action_group_response = bedrock_agent_client.create_agent_action_group(
        agentId=agent_id,
        agentVersion='DRAFT',
        actionGroupExecutor={
            'customControl': 'RETURN_CONTROL'
        },
        actionGroupName=agent_action_group_name,
        functionSchema={
            'functions': agent_functions
        },
        description=agent_action_group_description
    )
```

An Agent executing with Return of Control will then output an object containing either `functionInvocationInput` if a function definition was used (the example presented in this folder) or `apiInvocationInput` if an API schema was used.

Example JSON for function definition:

```json
{
    "returnControl": {
        "invocationId": "<INVOCATION_ID>", 
        "invocationInputs": [{
            "functionInvocationInput": {
                "actionGroup": "<ACTION_GROUP>", 
                "function": "get_available_vacations_days", 
                "parameters": [{
                    "name": "employee_id", 
                    "type": "integer", 
                    "value": 1
                }]
            }
        }]
    }
}
```

Example JSON for API Schema:
```json
{
    "returnControl": {
        "invocationId": "<INVOCATION_ID>",
        "invocationInputs": [{
            "apiInvocationInput": {
                "actionGroup": "<ACTION_GROUP>",
                "apiPath": "get_available_vacations_days",
                "httpMethod": "get",
                "parameters": [{
                    "name": "employee_id",
                    "type": "integer",
                    "value": "1"
                }]
            }
        }]
    }
}
```

Once the function has been executed, the output of the function is passed to the `invoke_agent` call.

Here is the syntax for the agents with function definition:

```python
raw_response_with_roc = bedrock_agent_runtime_client.invoke_agent(
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    sessionState={
        'invocationId': "<INVOCATION_ID>",
        'returnControlInvocationResults': [{
                'functionResult': {
                    'actionGroup': agent_action_group_name,
                    'function': "get_available_vacations_days",
                    'responseBody': {
                        "TEXT": {
                            'body': "available_vacation_days: "+str(available_vacation_days)
                        }
                    }
                }
        }]}
)
```

And the same example with API schema
```python
raw_response_with_roc = bedrock_agent_runtime_client.invoke_agent(
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    sessionState={
        'invocationId': "<INVOCATION_ID>",
        'returnControlInvocationResults': [{
            "apiResult": {
                "actionGroup": agent_action_group_name,
                "httpStatusCode": 200,
                "httpMethod": "get",
                "apiPath": "get_available_vacations_days",
                "responseBody": {
                    "text": {
                        "body": "available_vacation_days: "+str(available_vacation_days)
                    }
                }
            },
        }]}
)
```