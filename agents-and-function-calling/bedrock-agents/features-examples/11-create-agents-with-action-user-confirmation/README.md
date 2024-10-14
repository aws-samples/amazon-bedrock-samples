# Create Agents with Action user confirmation

In this folder, we will provide three examples of how to use user confirmation when enabled. This configuration is disabled by default, but enabling user confirmation can safeguard your end user from malicious prompt injections. Below is a screenshot of how this configuration appears in the AWS Console

![](images/enable_confirmation_action_group_function.png)

1. Enable user confirmation during action definition with function definition or API schema
2. Handle the request of confirmation with your application and return the confirmation to your agent using the ``returnControlInvocationResults`` parameter of the ``InvokeAgent`` API

When the agent decides to trigger an action, the details of the API or function that were gathered from the user, along with the user confirmation settings, are included in the ``invocationInputs`` field of the ``InvokeAgent`` response. This response also contains the ``invocationType`` and a unique ``invocationId``. The agent then calls the API or function specified in the ``invocationInputs``. If user confirmation is required, the user is asked to either ``CONFIRM`` or ``DENY`` the action presented in the response.

- If the user selects CONFIRM, the function or API is executed as planned.
- If the user selects DENY, the function or API is not executed.

## Examples:

### 11.1 - Create Agent with function definition and user confirmation

In this folder [11.1-create-agent-with-function-definition-and-user-confirmation](11.1-create-agent-with-function-definition-and-user-confirmation/11.1-create-agent-with-function-definition-and-user-confirmation.ipynb), we will provide an example based on folder ``01-create-agent-with-function-definition/``, where we enable user confirmation before calling the `reserve_vacation_time` function. After the user confirms with ``CONFIRM``, we will invoke a Lambda function

### 12.2 - Create Agent with function definition, return of control and user confirmation

In this folder [11.2-create-agent-with-function-definition-roc-and-user-confirmation](11.2-create-agent-with-function-definition-roc-and-user-confirmation/11.2-create-agent-with-function-definition-roc-and-user-confirmation.ipynb), we will provide an example based on folder ``03-create-agent-with-return-of-control/``, where we enable user confirmation before calling the `reserve_vacation_time` function. After the user confirms with ``CONFIRM``, we will call ``def`` Python Functions

### 12.3 - Create Agent with API schema and user confirmation

In this folder [11.3-create-agent-with-API-schema-and-user-confirmation](11.3-create-agent-with-API-schema-and-user-confirmation/11.3-create-agent-with-API-schema-and-user-confirmation.ipynb), we will provide an example based on the folder ``02-create-agent-with-api-schema/``, where in this case we will enable user confirmation through an API Schema (``insurance_claims_agent_openapi_schema.json``) in the ``/notify`` path, and whenever it is called, user confirmation will be required. After the user confirms with ``CONFIRM``, we will invoke a Lambda function
