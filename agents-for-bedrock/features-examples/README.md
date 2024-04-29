# Create Agents with Function Definition

In this folder, provide an example of an HR agent using Agents for Amazon Bedrock new capabilities for function definition.

The agents connects with a generated in-memory SQLite database that contains information about employee's available vacation days and planned holidays.

The database structure created is as following:

<img src="./images/HR_DB.png" style="width:50%;display:block;margin: 0 auto;">

The agent allows the employee to `get_available_vacations_days` and `book_vacations` according to the employee's requests.

Both functionalities are implemented as part of an AWS Lambda function that receives the inputs from the Agent via an event.

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
        # Session attributes to be addressed in example 06-prompt-and-session-attributes
    }, 
    "promptSessionAttributes": {
        # Session attributes to be addressed in example 06-prompt-and-session-attributes
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

In order to query the correct function and parameters the following code is added to the Lambda function

```python
def lambda_handler(event, context):
    function = event['function']
    parameters = event.get('parameters', [])
```