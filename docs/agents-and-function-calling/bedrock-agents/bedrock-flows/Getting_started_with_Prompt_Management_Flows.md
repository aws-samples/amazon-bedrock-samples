---
tags:
    - Bedrock/ Prompt-Management
    - API-Usage-Example
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/bedrock-flows/Getting_started_with_Prompt_Management_Flows.ipynb){:target="_blank"}"

<h2>Getting Started with Prompt Management and Flows for Amazon Bedrock</h2>

This example shows you how to get started with Prompt Management and Prompt Flows in Amazon Bedrock.

[Amazon Bedrock Prompt Management](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management.html) streamlines the creation, evaluation, deployment, and sharing of prompts in the Amazon Bedrock console and via APIs in the SDK. This feature helps developers and business users obtain the best responses from foundation models for their specific use cases.

[Amazon Bedrock Prompt Flows](https://docs.aws.amazon.com/bedrock/latest/userguide/flows.html) allows you to easily link multiple foundation models (FMs), prompts, and other AWS services, reducing development time and effort. It introduces a visual builder in the Amazon Bedrock console and a new set of APIs in the SDK, that simplifies the creation of complex generative AI workflows.

Let's start by making sure we have the lastest version of the Amazon Bedrock SDK, importing the libraries, and setting-up the client.


```python
<h2>Only run this the first time...</h2>
!pip3 install boto3 botocore -qU
```


```python
import boto3
from datetime import datetime
import json
```

Note the Prompt Management and Flows features are part of the Bedrock Agent SDK.


```python
bedrock_agent = boto3.client(service_name = "bedrock-agent", region_name = "us-east-1")
```

<h2>Prompt Management</h2>

<h3>Create and Manage Prompts</h3>

Let's create a sample prompt, in this case for a simple translation task.


```python
response = bedrock_agent.create_prompt(
    name = f"MyTestPrompt-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    description = "This is my test prompt for the customer service use case",
    variants = [
        {
            "inferenceConfiguration": {
                "text": {
                    "maxTokens": 3000,
                    "temperature": 0,
                    "topP": 0.999,
                    "topK": 250,
                }
            },
            "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
            "name": "variant-001",
            "templateConfiguration": {
                "text": {
                    "inputVariables": [
                        {
                            "name": "input"
                        }

                    ],
                    "text": "You're a customer service agent for the ecommerce company Octank. Answer the following user query in a friendly and direct way: {{input}}"
                }
            },
            "templateType": "TEXT"
        }
    ],
    defaultVariant = "variant-001"
)
print(json.dumps(response, indent=2, default=str))
promptId = response["id"]
promptArn = response["arn"]
promptName = response["name"]
print(f"Prompt ID: {promptId}\nPrompt ARN: {promptArn}\nPrompt Name: {promptName}")
```

Now that we have a draft prompt, we can create versions from it.


```python
response = bedrock_agent.create_prompt_version(
    promptIdentifier = promptId
)
print(json.dumps(response, indent=2, default=str))
```

Here we can see the list of prompts in our Prompt Library or catalog.


```python
response = bedrock_agent.list_prompts(
    maxResults = 10
)
print(json.dumps(response["promptSummaries"], indent=2, default=str))
```

We can also read the details of any of our prompts.


```python
response = bedrock_agent.get_prompt(
    promptIdentifier = promptId,
    promptVersion = "1"
)
print(json.dumps(response, indent=2, default=str))
```

-------

<h2>Prompt Flows</h2>

Now that we've learned how to create and manage prompts, we can continue exploring how to build generative AI applications logic by creating workflows. For this, we'll rely on Prompt Flows for Amazon Bedrock.

<h3>Create and Manage Flows</h3>

Let's create a simple flow that will load a prompt from our catalog. Note you can also create more complex flows involving chaining of steps, and conditions for dynamically routing, but let's keep it simple for now.

***Pre-requisite: For using Flows you need to make sure you have the proper AWS IAM permissions in place. You can check details in the [How Prompt Flows for Amazon Bedrock works](https://docs.aws.amazon.com/bedrock/latest/userguide/flows-how-it-works.html) documentation.***


```python
<h3>REPLACE WITH YOUR AWS IAM ROLE WITH FLOWS FOR BEDROCK PERMISSIONS</h3>
flow_role = [REPLACE_WITH_YOUR_ROLE_ARN]
```


```python
response = bedrock_agent.create_flow(
    name = f"MyTestFlow-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    description = "This is my test flow for the customer service use case",
    executionRoleArn = flow_role,
    definition = {
      "nodes": [
          {
              "name": "StartNode",
              "type": "Input",
              "configuration": {
                  "input": {}
              },
              "outputs": [
                  {
                      "name": "document",
                      "type": "String"
                  }
              ],
          },
          {
            "name": "Prompt_1",
            "type": "Prompt",
            "configuration": {
              "prompt": {
                "sourceConfiguration": {
                  "resource": {
                      "promptArn": promptArn
                  }
                }
              }
            },
            "inputs": [
              {
                "expression": "$.data",
                "name": "input",
                "type": "String"
              }
            ],
            "outputs": [
              {
                "name": "modelCompletion",
                "type": "String"
              }
            ],
          },
          {
            "name": "EndNode",
            "type": "Output",
            "configuration": {
                "output": {}
            },
            "inputs": [
              {
                "expression": "$.data",
                "name": "document",
                "type": "String"
              }
            ],
          }
      ],
      "connections": [
          {
              "name": "Connection_1",
              "source": "StartNode",
              "target": "Prompt_1",
              "type": "Data",
              "configuration":{
                  "data": {
                      "sourceOutput": "document",
                      "targetInput": "input"
                  }
              }
          },
          {
              "name": "Connection_2",
              "source": "Prompt_1",
              "target": "EndNode",
              "type": "Data",
              "configuration": {
                  "data": {
                      "sourceOutput": "modelCompletion",
                      "targetInput": "document"
                  }
              }
          }
      ],
    }
)
print(json.dumps(response, indent=2, default=str))
flowId = response["id"]
flowArn = response["arn"]
flowName = response["name"]
print(f"Flow ID: {flowId}\nFlow ARN: {flowArn}\nFlow Name: {flowName}")
```

Now that we have our first flow, we can prepare it. This basically builds and validates our flow.


```python
response = bedrock_agent.prepare_flow(
    flowIdentifier = flowId
)
print(json.dumps(response, indent=2, default=str))
```


```python
response = bedrock_agent.get_flow(
    flowIdentifier = flowId
)
print(json.dumps(response, indent=2, default=str))
```

We can also list all the flows in our account.


```python
response = bedrock_agent.list_flows(
    maxResults=10,
)
print(json.dumps(response["flowSummaries"], indent=2, default=str))
```

Let's create a version from our draft flow. Note flow versions are read-only, meaning these cannot be modified once created as they're intended for using in production. If you need to make changes to a flow you can update your draft.


```python
response = bedrock_agent.create_flow_version(
    flowIdentifier = flowId
)
print(json.dumps(response, indent=2, default=str))
```

We can also create flow alises, so that we can point our application front-ends and any other integrations to these. This allows creating new versions without impacting our service.


```python
response = bedrock_agent.create_flow_alias(
    flowIdentifier = flowId,
    name = flowName,
    description = "Alias for my test flow in the customer service use case",
    routingConfiguration = [
        {
            "flowVersion": "1"
        }
    ]
)
print(json.dumps(response, indent=2, default=str))
flowAliasId = response['id']
```


```python
import json
response = bedrock_agent.list_flow_versions(
    flowIdentifier = flowId,
    maxResults = 10
)
print(json.dumps(response, indent=2, default=str))
```


```python
response = bedrock_agent.get_flow_version(
    flowIdentifier = flowId,
    flowVersion = '1'
)
print(json.dumps(response, indent=2, default=str))
```

We can also update a given alias assigned to a flow, for e.g. pointing to another version if required.


```python
response = bedrock_agent.update_flow_alias(
    flowIdentifier = flowId,
    aliasIdentifier = flowAliasId,
    name = flowName,
    routingConfiguration = [
        {
            "flowVersion": "1"
        }
    ]
)
flowAliasId = response["id"]
print(json.dumps(response, indent=2, default=str))
```


```python
response = bedrock_agent.get_flow_alias(
    flowIdentifier = flowId,
    aliasIdentifier = flowAliasId
)
print(json.dumps(response, indent=2, default=str))
```

<h3>Invoke a Flow</h3>

Now that we have learned how to create and manage flows, we can test these with invocations.

Note for this we'll rely on the Bedrock Agent Runtime SDK.

You can invoke flows from any application front-end or your own systems as required. It effectively exposes all the logic of your flow through an Agent Endpoint API.


```python
bedrock_agent_runtime = boto3.client(service_name = 'bedrock-agent-runtime', region_name = 'us-east-1')
```


```python
response = bedrock_agent_runtime.invoke_flow(
    flowIdentifier = flowId,
    flowAliasIdentifier = flowAliasId,
    inputs = [
        { 
            "content": { 
                "document": "Hi, I need help with my order!"
            },
            "nodeName": "StartNode",
            "nodeOutputName": "document"
        }
    ]
)
event_stream = response["responseStream"]
for event in event_stream:
    print(json.dumps(event, indent=2, ensure_ascii=False))
```

---

<h3>Cleaning-up Resources (optional)</h3>

Before leaving, here's how to delete the resources that we've created.


```python
response = bedrock_agent.delete_flow_alias(
    flowIdentifier = flowId,
    aliasIdentifier = flowAliasId
)
print(json.dumps(response, indent=2, default=str))
```


```python
response = bedrock_agent.delete_flow_version(
    flowIdentifier = flowId,
    flowVersion = '1'
)
print(json.dumps(response, indent=2, default=str))
```


```python
response = bedrock_agent.delete_flow(
    flowIdentifier = flowId
)
print(json.dumps(response, indent=2, default=str))
```


```python
response = bedrock_agent.delete_prompt(
    promptIdentifier = promptId
)
print(json.dumps(response, indent=2, default=str))
```

-------
