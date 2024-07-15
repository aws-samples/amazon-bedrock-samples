# Create Agents with code interpretation capabilities

In this folder, we provide an example of an analytics agent using Agents for Amazon Bedrock new capabilities for [code interpretation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-code-interpretation.html).

The code interpreter is a sandboxed runtime environment in which the agent can run code. 

In this example we will create a test agent with the following architecture:

![Agent architecture](images/architecture.png)


Code interpretation is made available to the agent via a pre-defined action group. Once the agent is created, you can enable the code interpretation capabilities via the `CreateAgentActionGroup` request using the `parentActionGroupSignature` parameter and setting it to `AMAZON.CodeInterpreter`.


The code below shows how to configure the code interpretation capabilities when creating your agent's action group using the `create_agent_action_group` function from [boto3 SDK](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/create_agent_action_group.html). You should set the  `parentActionGroupSignature` to `AMAZON.CodeInterpreter` and the `actionGroupState` status to `ENABLED`. Note that you must leave the description, apiSchema, and actionGroupExecutor fields blank for this action group.

```python
    response = client.create_agent_action_group(
    actionGroupName='CodeInterpreterAction',
    actionGroupState='ENABLED',
    agentId='<YOUR_AGENT_ID>',
    agentVersion='<YOUR_AGENT_VERSION>',
    parentActionGroupSignature='AMAZON.CodeInterpreter'
)
```

When invoking your agent, should supply parameter including the query text, agent id, agent alias, and a session id. Other parameters allow enabling tracing, to see the details of the model's return communication stream, ending the session, optionally storing conversational memory, and maintaining a state for this session.
```python
    if not session_state:
        session_state = {}
    # invoke the agent API
    agent_response = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        enableTrace=enable_trace, 
        endSession=end_session,
        memoryId=memory_id,
        sessionState=session_state
    )    
    
```
