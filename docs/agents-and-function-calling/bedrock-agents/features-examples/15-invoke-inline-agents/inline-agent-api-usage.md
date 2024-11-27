---
tags:
    - Agents/ Dynamic Inline Agent
    - API-Usage-Example
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/15-invoke-inline-agents/inline-agent-api-usage.ipynb){:target="_blank"}"

<h2>Building Dynamic AI Assistants with Amazon Bedrock Inline Agents</h2>

In this notebook, we'll walk through the process of setting up and invoking an inline agent, showcasing its flexibility and power in creating dynamic AI assistants. By following our progressive approach, you will gain a comprehensive understanding of how to use inline agents for various use cases and complexity levels. Throughout a single interactive conversation, we will demonstrate how the agent can be enhanced `on the fly` with new tools and instructions while maintaining context of our ongoing discussion.

We'll follow a progressive approach to building our assistant:

1. Simple Inline Agent: We'll start with a basic inline agent with a code interpreter.
2. Adding Knowledge Bases: We'll enhance our agent by incorporating a knowledge base with role-based access.
3. Integrating Action Groups: Finally, we'll add custom tools to extend the agent's functionality.

<h3>What are Inline Agents?</h3>

[Inline agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-create-inline.html) are a powerful feature of Amazon Bedrock that allow developers to create flexible and adaptable AI assistants. 

Unlike traditional static agents, inline agents can be dynamically configured at runtime, enabling real time adjustments to their behavior, capabilities, and knowledge base.

Key features of inline agents include:

1. **Dynamic configuration**: Modify the agent's instructions, action groups, and other parameters on the fly.
2. **Flexible integration**: Easily incorporate external APIs and services as needed for each interaction.
3. **Contextual adaptation**: Adjust the agent's responses based on user roles, preferences, or specific scenarios.

<h3>Why Use Inline Agents?</h3>

Inline agents offer several advantages for building AI applications:

1. **Rapid prototyping**: Quickly experiment with different configurations without redeploying your application.
2. **Personalization**: Tailor the agent's capabilities to individual users or use cases in real time.
3. **Scalability**: Efficiently manage a single agent that can adapt to multiple roles or functions.
4. **Cost effectiveness**: Optimize resource usage by dynamically selecting only the necessary tools and knowledge for each interaction.

<h3>Prerequisites</h3>

Before you begin, make sure that you have:

1. An active AWS account with access to Amazon Bedrock.
2. Necessary permissions to create and invoke inline agents.
3. Be sure to complete additonal prerequisites, visit [Amazon Bedrock Inline Agent prerequisites documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/inline-agent-prereq.html) to learn more.

<h3>Installing prerequisites</h3>
Let's begin with installing the required packages. This step is important as you need `boto3` version `1.35.68` or later to use inline agents.



```python
# uncomment to install the required python packages
!pip install --upgrade -r requirements.txt
```


```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

<h2>Setup and Imports</h2>
First, let's import the necessary libraries and set up our Bedrock client.

```python
import os
import json
from pprint import pprint
import boto3
from datetime import datetime
import random
import pprint
from termcolor import colored
from rich.console import Console
from rich.markdown import Markdown

session = boto3.session.Session()
region = session.region_name

# Runtime Endpoints
bedrock_rt_client = boto3.client(
    "bedrock-agent-runtime",
    region_name=region
)

sts_client = boto3.client("sts")
account_id = sts_client.get_caller_identity()["Account"]

# To manage session id:
random_int = random.randint(1,100000)
```

<h3>Configuring the Inline Agent</h3>

Next, we'll set up the basic configuration for our Amazon Bedrock Inline Agent. This includes specifying the foundation model, session management, and basic instructions.


```python
# change model id as needed:
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

sessionId = f'custom-session-id-{random_int}'
endSession = False
enableTrace = True

# customize instructions of inline agent:
agent_instruction = """You are a helpful AI assistant helping Octank Inc employees with their questions and processes. 
You write short and direct responses while being cheerful. You have access to python coding environment that helps you extend your capabilities."""
```

<h3>Basic Inline Agent Invocation</h3>

Let's start by invoking a simple inline agent with just the foundation model and basic instructions.


```python
# prepare request parameters before invoking inline agent
request_params = {
    "instruction": agent_instruction,
    "foundationModel": model_id,
    "sessionId": sessionId,
    "endSession": endSession,
    "enableTrace": enableTrace,
}

# define code interpreter tool
code_interpreter_tool = {
    "actionGroupName": "UserInputAction",
    "parentActionGroupSignature": "AMAZON.CodeInterpreter"
}

# add the tool to request parameter of inline agent
request_params["actionGroups"] = [code_interpreter_tool]

# enable traces
request_params["enableTrace"] = True
```


```python
# enter the question you want the inline agent to answer
request_params['inputText'] = 'what is the time right now in pacific timezone?'
```

<h4>Invoking a simple Inline Agent</h4>

We'll send a request to the agent asking it to perform a simple calculation or code execution task. This will showcase how the agent can interpret and run code on the fly.

To do so, we will use the [InvokeInlineAgent](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_InvokeInlineAgent.html) API via boto3 `bedrock-agent-runtime` client.

Our function `invoke_inline_agent_helper` also helps us processing the agent trace request and format it for easier readibility. You do not have to use this function in your system, but it will make it easier to observe the code used by code interpreter, the function invocations and the knowledge base content.

We also provide the metrics for the agent invocation time and the input and output tokens


```python
def invoke_inline_agent_helper(client, request_params, trace_level="core"):
    _time_before_call = datetime.now()

    _agent_resp = client.invoke_inline_agent(
        **request_params
    )

    if request_params["enableTrace"]:
        if trace_level == "all":
            print(f"invokeAgent API response object: {_agent_resp}")
        else:
            print(
                f"invokeAgent API request ID: {_agent_resp['ResponseMetadata']['RequestId']}"
            )
            session_id = request_params["sessionId"]
            print(f"invokeAgent API session ID: {session_id}")

    # Return error message if invoke was unsuccessful
    if _agent_resp["ResponseMetadata"]["HTTPStatusCode"] != 200:
        _error_message = f"API Response was not 200: {_agent_resp}"
        if request_params["enableTrace"] and trace_level == "all":
            print(_error_message)
        return _error_message

    _total_in_tokens = 0
    _total_out_tokens = 0
    _total_llm_calls = 0
    _orch_step = 0
    _sub_step = 0
    _trace_truncation_lenght = 300
    _time_before_orchestration = datetime.now()

    _agent_answer = ""
    _event_stream = _agent_resp["completion"]

    try:
        for _event in _event_stream:
            _sub_agent_alias_id = None

            if "chunk" in _event:
                _data = _event["chunk"]["bytes"]
                _agent_answer = _data.decode("utf8")

            if "trace" in _event and request_params["enableTrace"]:
                if "failureTrace" in _event["trace"]["trace"]:
                    print(
                        colored(
                            f"Agent error: {_event['trace']['trace']['failureTrace']['failureReason']}",
                            "red",
                        )
                    )

                if "orchestrationTrace" in _event["trace"]["trace"]:
                    _orch = _event["trace"]["trace"]["orchestrationTrace"]

                    if trace_level in ["core", "outline"]:
                        if "rationale" in _orch:
                            _rationale = _orch["rationale"]
                            print(colored(f"{_rationale['text']}", "blue"))

                        if "invocationInput" in _orch:
                            # NOTE: when agent determines invocations should happen in parallel
                            # the trace objects for invocation input still come back one at a time.
                            _input = _orch["invocationInput"]
                            print(_input)

                            if "actionGroupInvocationInput" in _input:
                                if 'function' in _input['actionGroupInvocationInput']:
                                    tool = _input['actionGroupInvocationInput']['function']
                                elif 'apiPath' in _input['actionGroupInvocationInput']:
                                    tool = _input['actionGroupInvocationInput']['apiPath']
                                else:
                                    tool = 'undefined'
                                if trace_level == "outline":
                                    print(
                                        colored(
                                            f"Using tool: {tool}",
                                            "magenta",
                                        )
                                    )
                                else:
                                    print(
                                        colored(
                                            f"Using tool: {tool} with these inputs:",
                                            "magenta",
                                        )
                                    )
                                    if (
                                        len(
                                            _input["actionGroupInvocationInput"][
                                                "parameters"
                                            ]
                                        )
                                        == 1
                                    ) and (
                                        _input["actionGroupInvocationInput"][
                                            "parameters"
                                        ][0]["name"]
                                        == "input_text"
                                    ):
                                        print(
                                            colored(
                                                f"{_input['actionGroupInvocationInput']['parameters'][0]['value']}",
                                                "magenta",
                                            )
                                        )
                                    else:
                                        print(
                                            colored(
                                                f"{_input['actionGroupInvocationInput']['parameters']}\n",
                                                "magenta",
                                            )
                                        )

                            elif "codeInterpreterInvocationInput" in _input:
                                if trace_level == "outline":
                                    print(
                                        colored(
                                            f"Using code interpreter", "magenta"
                                        )
                                    )
                                else:
                                    console = Console()
                                    _gen_code = _input[
                                        "codeInterpreterInvocationInput"
                                    ]["code"]
                                    _code = f"```python\n{_gen_code}\n```"

                                    console.print(
                                        Markdown(f"**Generated code**\n{_code}")
                                    )

                        if "observation" in _orch:
                            if trace_level == "core":
                                _output = _orch["observation"]
                                if "actionGroupInvocationOutput" in _output:
                                    print(
                                        colored(
                                            f"--tool outputs:\n{_output['actionGroupInvocationOutput']['text'][0:_trace_truncation_lenght]}...\n",
                                            "magenta",
                                        )
                                    )

                                if "agentCollaboratorInvocationOutput" in _output:
                                    _collab_name = _output[
                                        "agentCollaboratorInvocationOutput"
                                    ]["agentCollaboratorName"]
                                    _collab_output_text = _output[
                                        "agentCollaboratorInvocationOutput"
                                    ]["output"]["text"][0:_trace_truncation_lenght]
                                    print(
                                        colored(
                                            f"\n----sub-agent {_collab_name} output text:\n{_collab_output_text}...\n",
                                            "magenta",
                                        )
                                    )

                                if "finalResponse" in _output:
                                    print(
                                        colored(
                                            f"Final response:\n{_output['finalResponse']['text'][0:_trace_truncation_lenght]}...",
                                            "cyan",
                                        )
                                    )


                    if "modelInvocationOutput" in _orch:
                        _orch_step += 1
                        _sub_step = 0
                        print(colored(f"---- Step {_orch_step} ----", "green"))

                        _llm_usage = _orch["modelInvocationOutput"]["metadata"][
                            "usage"
                        ]
                        _in_tokens = _llm_usage["inputTokens"]
                        _total_in_tokens += _in_tokens

                        _out_tokens = _llm_usage["outputTokens"]
                        _total_out_tokens += _out_tokens

                        _total_llm_calls += 1
                        _orch_duration = (
                            datetime.now() - _time_before_orchestration
                        )

                        print(
                            colored(
                                f"Took {_orch_duration.total_seconds():,.1f}s, using {_in_tokens+_out_tokens} tokens (in: {_in_tokens}, out: {_out_tokens}) to complete prior action, observe, orchestrate.",
                                "yellow",
                            )
                        )

                        # restart the clock for next step/sub-step
                        _time_before_orchestration = datetime.now()

                elif "preProcessingTrace" in _event["trace"]["trace"]:
                    _pre = _event["trace"]["trace"]["preProcessingTrace"]
                    if "modelInvocationOutput" in _pre:
                        _llm_usage = _pre["modelInvocationOutput"]["metadata"][
                            "usage"
                        ]
                        _in_tokens = _llm_usage["inputTokens"]
                        _total_in_tokens += _in_tokens

                        _out_tokens = _llm_usage["outputTokens"]
                        _total_out_tokens += _out_tokens

                        _total_llm_calls += 1

                        print(
                            colored(
                                "Pre-processing trace, agent came up with an initial plan.",
                                "yellow",
                            )
                        )
                        print(
                            colored(
                                f"Used LLM tokens, in: {_in_tokens}, out: {_out_tokens}",
                                "yellow",
                            )
                        )

                elif "postProcessingTrace" in _event["trace"]["trace"]:
                    _post = _event["trace"]["trace"]["postProcessingTrace"]
                    if "modelInvocationOutput" in _post:
                        _llm_usage = _post["modelInvocationOutput"]["metadata"][
                            "usage"
                        ]
                        _in_tokens = _llm_usage["inputTokens"]
                        _total_in_tokens += _in_tokens

                        _out_tokens = _llm_usage["outputTokens"]
                        _total_out_tokens += _out_tokens

                        _total_llm_calls += 1
                        print(colored("Agent post-processing complete.", "yellow"))
                        print(
                            colored(
                                f"Used LLM tokens, in: {_in_tokens}, out: {_out_tokens}",
                                "yellow",
                            )
                        )

                if trace_level == "all":
                    print(json.dumps(_event["trace"], indent=2))

            if "files" in _event.keys() and request_params["enableTrace"]:
                console = Console()
                files_event = _event["files"]
                console.print(Markdown("**Files**"))

                files_list = files_event["files"]
                for this_file in files_list:
                    print(f"{this_file['name']} ({this_file['type']})")
                    file_bytes = this_file["bytes"]

                    # save bytes to file, given the name of file and the bytes
                    file_name = os.path.join("output", this_file["name"])
                    with open(file_name, "wb") as f:
                        f.write(file_bytes)

        if request_params["enableTrace"]:
            duration = datetime.now() - _time_before_call

            if trace_level in ["core", "outline"]:
                print(
                    colored(
                        f"Agent made a total of {_total_llm_calls} LLM calls, "
                        + f"using {_total_in_tokens+_total_out_tokens} tokens "
                        + f"(in: {_total_in_tokens}, out: {_total_out_tokens})"
                        + f", and took {duration.total_seconds():,.1f} total seconds",
                        "yellow",
                    )
                )

            if trace_level == "all":
                print(f"Returning agent answer as: {_agent_answer}")

        return _agent_answer

    except Exception as e:
        print(f"Caught exception while processing input to invokeAgent:\n")
        input_text = request_params["inputText"]
        print(f"  for input text:\n{input_text}\n")
        print(
            f"  request ID: {_agent_resp['ResponseMetadata']['RequestId']}, retries: {_agent_resp['ResponseMetadata']['RetryAttempts']}\n"
        )
        print(f"Error: {e}")
        raise Exception("Unexpected exception: ", e)
```


```python
invoke_inline_agent_helper(bedrock_rt_client, request_params, trace_level="core")
```

<h3>Adding a Knowledge Base</h3>

Now, we'll demonstrate how to incorporate a knowledge base into our inline agent invocation. Let's first create a knowledge base using fictional HR policy documents that we will later use in with inline agent.

We will use [Amazon Bedrock Knowledge Base](https://aws.amazon.com/bedrock/knowledge-bases/) to create our knowledge base. To do so, we use the support function `create_knowledge_base` available in the `create_knowledge_base.py` file. It will abstract away the work to create the underline vector database, the vector indexes with the appropriated chunking strategy as well as the indexation of the documents to the knowledge base. Take a look at the `create_knowledge_base.py` file for more details.


```python
import os
from create_knowledge_base import create_knowledge_base

# Configuration
bucket_name = f"inline-agent-bucket-{random_int}"
kb_name = f"policy-kb-{random_int}"
data_path = "policy_documents"

# Create knowledge base and upload documents
kb_id, bucket_name, kb_metadata = create_knowledge_base(region, bucket_name, kb_name, data_path)
```

<h4>Setting up Knowledge Base configuration to invoke inline agent</h4>

Let's now set up the knowledge base configuration to invoke our inline agent


```python
# define number of chunks to retrieve
num_results = 3
search_strategy = "HYBRID"

# provide instructions about knowledge base that inline agent can use
kb_description = 'This knowledge base contains information about company HR policies, code or conduct, performance reviews and much more'

# lets define access level for metadata filtering
user_profile = 'basic'
access_filter = {
    "equals": {
        "key": "access_level",
        "value": user_profile
    }
}

# lets revise our Knowledge bases configuration
kb_config = {
    "knowledgeBaseId": kb_id,
    "description": kb_description,
    "retrievalConfiguration": {
        "vectorSearchConfiguration": {
            "filter": access_filter,
            "numberOfResults": num_results,
            "overrideSearchType": "HYBRID"
        }
    }
}

# lets add knowledge bases to our request parameters
request_params["knowledgeBases"] = [kb_config]
    
# update the agent instructions to inform inline agent that it has access to a knowlegde base
new_capabilities = """You have access to Octank Inc company policies knowledge base. 
Use this database to search for information about company policies, company HR policies, code or conduct, performance reviews and much more. And use them to briefly answer the use question."""
request_params["instruction"] += f"\n\n{new_capabilities}"

# check updated request parameters including instructions for the inline agent
print(request_params)
```

<h4>Querying the Enhanced Agent</h4>

We'll send a query that requires the agent to retrieve information from the knowledge base and provide an informed response.


```python
# enter the question that will use knowledge bases
request_params['inputText'] = 'How much is the employee compensation bonus?'
```


```python
# invoke the inline agent
invoke_inline_agent_helper(bedrock_rt_client, request_params)
```

<h4>Analyzing the Knowledge Base Integration</h4>

We see that there are two types of access levels defined in the knowledge base, basic and manager. Compensation related access is `Manager` only. Let's try the same query with proper filter.


```python
# lets define access level for metadata filtering
user_profile = 'Manager'
# user_profile = 'basic'
access_filter = {
    "equals": {
        "key": "access_level",
        "value": user_profile
    }
}

# lets revise our Knowledge bases configuration
kb_config = {
    "knowledgeBaseId": kb_id,
    "description": kb_description,
    "retrievalConfiguration": {
        "vectorSearchConfiguration": {
            "filter": access_filter,
            "numberOfResults": num_results,
            "overrideSearchType": "HYBRID"
        }
    }
}

# lets add knowledge bases to our request parameters
request_params["knowledgeBases"] = [kb_config]

# invoke the inline agent
invoke_inline_agent_helper(bedrock_rt_client, request_params)
```

<h3>Integrating Action Groups</h3>

In this section, we'll show how to add a custom tool (action group) to our agent invocation. This illustrates how to extend the agent's functionality with external services via the API.

Let's first create a lambda function that we will later use in with inline agent.


```python
# run lambda function creation
from lambda_creator import create_lambda_function_and_its_resources
import os

present_directory = os.getcwd()
lambda_function_code_path = str(present_directory) + "/pto_lambda/lambda_function.py"

# Create all resources
resources = create_lambda_function_and_its_resources(
    region=region,
    account_id=account_id,
    custom_name=f"hr-inlineagent-lambda-{random_int}",
    lambda_code_path=lambda_function_code_path
)

# Access the created resources
lambda_function = resources['lambda_function']
lambda_function_arn = lambda_function['FunctionArn']
print(lambda_function_arn)
```

<h4>Configuring the Agent with the Action Group</h4>

We'll update our agent configuration to include the new action group, allowing it to interact with the external service.
For this example we are providing an OpenAPI Schema to define our action group tools. You can also use function definition to do the same, but your lambda function even will change a bit. For more information see the documentation [here](https://docs.aws.amazon.com/bedrock/latest/userguide/action-define.html)


```python
apply_vacation_tool = {
            'actionGroupName': 'FetchDetails',
            "actionGroupExecutor": {
                "lambda": lambda_function_arn
            }, "apiSchema": {
                "payload": """
    {
    "openapi": "3.0.0",
    "info": {
        "title": "Vacation Management API",
        "version": "1.0.0",
        "description": "API for managing vacation requests"
    },
    "paths": {
        "/vacation": {
            "post": {
                "summary": "Process vacation request",
                "description": "Process a vacation request or check balance",
                "operationId": "processVacation",
                "parameters": [
                    {
                        "name": "action",
                        "in": "query",
                        "description": "The type of vacation action to perform",
                        "required": true,
                        "schema": {
                            "type": "string",
                            "enum": ["check_balance", "check balance", "apply", "request"],
                            "description": "Action type for vacation management"
                        }
                    },
                    {
                        "name": "days",
                        "in": "query",
                        "description": "Number of vacation days requested",
                        "required": false,
                        "schema": {
                            "type": "integer",
                            "minimum": 1
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Request processed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {
                                            "type": "string",
                                            "enum": ["approved", "pending", "rejected", "info"],
                                            "description": "Status of the vacation request"
                                        },
                                        "message": {
                                            "type": "string",
                                            "description": "Detailed response message"
                                        },
                                        "ticket_url": {
                                            "type": "string",
                                            "description": "Ticket URL for long vacation requests"
                                        }
                                    },
                                    "required": ["status", "message"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
    """
            },
            "description": "Process vacation and check leave balance"
}
            
# update the tools that inline agent has access to
request_params["actionGroups"] = [code_interpreter_tool, apply_vacation_tool]
```

<h4>Testing the Full Featured Agent</h4>

We'll send a complex query that requires the agent to use its language understanding, access the knowledge base, and interact with the external service via the action group.

<h4>Analyzing the Complete Agent Behavior</h4>

We'll examine the agent's response, focusing on how it orchestrates different capabilities (language model, knowledge base, and external actions) to handle complex queries.


```python
# ask question:
request_params['inputText'] = 'I will be out of office from 2024/11/28 for the next 3 days'

# invoke the inline agent
invoke_inline_agent_helper(bedrock_rt_client, request_params)
```

<h3>Clean up</h3>

Let's delete the resources that were created in this notebook


```python
lambda_client = boto3.client('lambda')
iam_client = boto3.client('iam')

def delete_iam_roles_and_policies(role_name, iam_client):
    try:
        iam_client.get_role(RoleName=role_name)
    except iam_client.exceptions.NoSuchEntityException:
        print(f"Role {role_name} does not exist") 
    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]
    print(f"======Attached policies with role {role_name}========\n", attached_policies)
    for attached_policy in attached_policies:
        policy_arn = attached_policy["PolicyArn"]
        policy_name = attached_policy["PolicyName"]
        iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print(f"Detached policy {policy_name} from role {role_name}")
        if str(policy_arn.split("/")[1]) == "service-role":
            print(f"Skipping deletion of service-linked role policy {policy_name}")
        else: 
            iam_client.delete_policy(PolicyArn=policy_arn)
            print(f"Deleted policy {policy_name} from role {role_name}")

    iam_client.delete_role(RoleName=role_name)
    print(f"Deleted role {role_name}")
    print("======== All IAM roles and policies deleted =========")
    
# delete lambda function
response = lambda_client.delete_function(
    FunctionName=resources['lambda_function']['FunctionName']
)
# delete lamnda role and policy
delete_iam_roles_and_policies(resources['lambda_role']['Role']['RoleName'], iam_client)
# delete knowledge base
kb_metadata.delete_kb(delete_s3_bucket=True, delete_iam_roles_and_policies=True)
```

<h2>Conclusion</h2>

This notebook has demonstrated the key aspects of using the Amazon Bedrock Inline Agents API:

1. Basic agent invocation
2. Incorporating knowledge bases
3. Adding custom action groups
4. Implementing guardrails

By leveraging these API capabilities, developers can create dynamic, adaptable AI assistants that can be easily customized for various use cases without redeploying applications.

Key takeaways:
1. Inline agents offer great flexibility through their API
2. Knowledge bases and action groups can be easily integrated
3. Guardrails help maintain responsible AI practices
