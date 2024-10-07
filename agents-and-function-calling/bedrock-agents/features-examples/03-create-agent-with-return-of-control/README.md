# Create Agents with Return of Control (Function Calling)
In this folder, we provide an example of an HR agent using [Amazon Bedrock Agents](https://aws.amazon.com/bedrock/agents/) new capabilities for function definition and [return of control]( https://docs.aws.amazon.com/bedrock/latest/userguide/agents-returncontrol.html) for function calling.

Return of control for function calling allows developers to define an action schema and get the control back whenever the agent invokes the action. This provides developers more options to implement business logic in addition to the already available Lambda approach. Furthermore, with Return of Control, developers get the ability to execute time consuming actions in the background (asynchronous execution), while continuing the orchestration flow. For example, if a user requests to encode three different video files, the agent needs to make three individual encode_video API calls. Developers can now build workflows with Return of Control to invoke the three APIs in parallel without waiting for the results from the first call. This feature can allow you as a developer to achieve higher efficiency, more flexibility over how actions are executed, and enhanced workflow management with asynchronous execution for their Agents. 

The agent for this section allows the employee to get_available_vacations_days and book_vacations according to the employee's requests.

Both functionalities are implemented in memory in the notebook and would be available in an existent applications for production use cases. The agent use case is similar to the Lab 1, but the function execution happens outside the scope of the agent, as shown in the architecture below:

![HR Assistant Agent](images/architecture.png)

The notebook logic connects with a generated in-memory SQLite database that contains information about employee's available vacation days and planned holidays.

The database structure created is as following:
![Three tables: {employees, vacations, planned_vacations}, employees: {employee_id - INTEGER, employee_name - TEXT, employee_job_title - TEXT, employee_start_date - TEXT, employee_employment_status - TEXT}, vacations: {employee_id - INTEGER, year - INTEGER, employee_total_vacation_days - INTEGER, employee_vacation_days_taken - INTEGER, employee_vacation_days_available - INTEGER}, planned_vacations: {employee_id - INTEGER, vacation_start_date - TEXT, vacation_end_date - TEXT, vacation_days_taken - INTEGER}](images/HR_DB.png)

The functions are defined using Function Definition as a list of `JSON` objects:

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

When creating the Agent Action Group, the actionGroupExecutor parameter is set to {'customControl': 'RETURN_CONTROL'} to indicate that no Lambda function is provided and that the agent should return which function to call and with which parameters.

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

An Agent executing with Return of Control will then output an object containing either `functionInvocationInput`, if a function definition was used (the example presented in this folder), or `apiInvocationInput`, if an API schema was used.

Example `JSON` for function definition:

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

Example `JSON` for API Schema:

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

Once the function has been executed, the output of the function is passed to the `invoke_agent` call in the `returnControlInvocationResults` parameter.

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

And the same example with API schema:

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