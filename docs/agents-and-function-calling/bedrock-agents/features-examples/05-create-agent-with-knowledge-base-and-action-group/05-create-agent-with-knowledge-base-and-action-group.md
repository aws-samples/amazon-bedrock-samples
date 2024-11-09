---
tags:
    - Agents/ Function Calling
    - Agent/ RAG
    - Agents/ Tool Binding
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/05-create-agent-with-knowledge-base-and-action-group/05-create-agent-with-knowledge-base-and-action-group.ipynb){:target="_blank"}"

<h2>Create an Agent for Amazon Bedrock integrated with Knowledge Bases for Amazon Bedrock and attach Action Group</h2>

In this notebook you will learn how to create an Amazon Bedrock Agent that makes use of Knowledge Bases for Amazon Bedrock to retrieve data about a restaurant's menu. The use case create a restaurant agent, it's tasks will be to give information to the clients about the adults or childrens menu and be in charge of the table booking system. Client's will be able to create, delete or get booking information. The architecture looks as following:

<img src="images/architecture.png" style="width:70%;display:block;margin: 0 auto;">
<br/>

The steps to complete this notebook are:

1. Import the needed libraries
1. Create the Knowledge Base for Amazon Bedrock
1. Upload the dataset to Amazon S3
1. Create the Agent for Amazon Bedrock
1. Test the Agent
1. Clean-up the resources created

<h2>1. Import the needed libraries</h2>

First step is to install the pre-requisites packages


```python
!pip install --upgrade -q -r requirements.txt
```


```python
import os
import time
import boto3
import logging
import pprint
import json

from knowledge_base import BedrockKnowledgeBase
from agent import create_agent_role_and_policies, create_lambda_role, delete_agent_roles_and_policies
from agent import create_dynamodb, create_lambda, clean_up_resources
```


```python
#Clients
s3_client = boto3.client('s3')
sts_client = boto3.client('sts')
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
region, account_id
```


```python
suffix = f"{region}-{account_id}"
agent_name = 'booking-agent'
knowledge_base_name = f'{agent_name}-kb'
knowledge_base_description = "Knowledge Base containing the restaurant menu's collection"
agent_alias_name = "booking-agent-alias"
bucket_name = f'{agent_name}-{suffix}'
agent_bedrock_allow_policy_name = f"{agent_name}-ba"
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
agent_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

agent_description = "Agent in charge of a restaurants table bookings"
agent_instruction = """
You are a restaurant agent, helping clients retrieve information from their booking, 
create a new booking or delete an existing booking
"""

agent_action_group_description = """
Actions for getting table booking information, create a new booking or delete an existing booking"""

agent_action_group_name = "TableBookingsActionGroup"
```

<h2>2. Create Knowledge Base for Amazon Bedrock</h2>
Let's start by creating a [Knowledge Base for Amazon Bedrock](https://aws.amazon.com/bedrock/knowledge-bases/) to store the restaurant menus. Knowledge Bases allow you to integrate with different vector databases including [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/), [Amazon Aurora](https://aws.amazon.com/rds/aurora/) and [Pinecone](http://app.pinecone.io/bedrock-integration). For this example, we will integrate the knowledge base with Amazon OpenSearch Serverless. To do so, we will use the helper class `BedrockKnowledgeBase` which will create the knowledge base and all of its pre-requisites:
1. IAM roles and policies
2. S3 bucket
3. Amazon OpenSearch Serverless encryption, network and data access policies
4. Amazon OpenSearch Serverless collection
5. Amazon OpenSearch Serverless vector index
6. Knowledge base
7. Knowledge base data source


```python
knowledge_base = BedrockKnowledgeBase(
    kb_name=knowledge_base_name,
    kb_description=knowledge_base_description,
    data_bucket_name=bucket_name
)
```

<h2>3. Upload the dataset to Amazon S3</h2>
Now that we have created the knowledge base, let's populate it with the menu's dataset. The Knowledge Base data source expects the data to be available on the S3 bucket connected to it and changes on the data can be syncronized to the knowledge base using the `StartIngestionJob` API call. In this example we will use the [boto3 abstraction](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/start_ingestion_job.html) of the API, via our helper classe. 

Let's first upload the menu's data available on the `dataset` folder to s3


```python
def upload_directory(path, bucket_name):
        for root,dirs,files in os.walk(path):
            for file in files:
                file_to_upload = os.path.join(root,file)
                print(f"uploading file {file_to_upload} to {bucket_name}")
                s3_client.upload_file(file_to_upload,bucket_name,file)

upload_directory("dataset", bucket_name)
```

Now we start the ingestion job


```python
<h2>ensure that the kb is available</h2>
time.sleep(30)
<h2>sync knowledge base</h2>
knowledge_base.start_ingestion_job()
```

Finally we collect the Knowledge Base Id to integrate it with our Agent later on


```python
kb_id = knowledge_base.get_knowledge_base_id()
```

<h3>3.1 Test the Knowledge Base</h3>
Now the Knowlegde Base is available we can test it out using the [**retrieve**](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/retrieve.html) and [**retrieve_and_generate**](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/retrieve_and_generate.html) functions. 

<h4>Testing Knowledge Base with Retrieve and Generate API</h4>

Let's first test the knowledge base using the retrieve and generate API. With this API, Bedrock takes care of retrieving the necessary references from the knowledge base and generating the final answer using a LLM model from Bedrock


```python
response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": "Which are the 5 mains available in the childrens menu?"
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region, agent_foundation_model),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5
                } 
            }
        }
    }
)

print(response['output']['text'],end='\n'*2)
```

As you can see, with the retrieve and generate API we get the final response directly and we don't see the different sources used to generate this response. Let's now retrieve the source information from the knowledge base with the retrieve API.

<h4>Testing Knowledge Base with Retrieve API</h4>
If you need an extra layer of control, you can retrieve the chuncks that best match your query using the retrieve API. In this setup, we can configure the desired number of results and control the final answer with your own application logic. The API then provides you with the matching content, its S3 location, the similarity score and the chunk metadata


```python
response_ret = bedrock_agent_runtime_client.retrieve(
    knowledgeBaseId=kb_id, 
    nextToken='string',
    retrievalConfiguration={
        "vectorSearchConfiguration": {
            "numberOfResults":5,
        } 
    },
    retrievalQuery={
        'text': 'Which are the 5 mains available in the childrens menu?'
    }
)

def response_print(retrieve_resp):
#structure 'retrievalResults': list of contents. Each list has content, location, score, metadata
    for num,chunk in enumerate(response_ret['retrievalResults'],1):
        print(f'Chunk {num}: ',chunk['content']['text'],end='\n'*2)
        print(f'Chunk {num} Location: ',chunk['location'],end='\n'*2)
        print(f'Chunk {num} Score: ',chunk['score'],end='\n'*2)
        print(f'Chunk {num} Metadata: ',chunk['metadata'],end='\n'*2)

response_print(response_ret)
```

<h2>4. Create the Agent for Amazon Bedrock</h2>

In this section we will go through all the steps to create an Agent for Amazon Bedrock. 

These are the steps to complete:
    
1. Create an Amazon DynamoDB table
2. Create an AWS Lambda function
3. Create the IAM policies needed for the Agent
4. Create the Agent
5. Create the Agent Action Group
6. Allow the Agent to invoke the Action Group Lambda
7. Associate the Knowledge Base to the agent
8. Prepare the Agent and create an alias

<h3>4.1 Create the DynamoDB table</h3>
We will create a DynamoDB table which contains the restaurant bookings information.


```python
table_name = 'restaurant_bookings'
create_dynamodb(table_name)
```

<h3>4.2 Create the Lambda Function</h3>

We will now create a lambda function that interacts with DynamoDB table. To do so we will:

1. Create the `lambda_function.py` file which contains the logic for our lambda function
2. Create the IAM role for our Lambda function
3. Create the lambda function with the required permissions

<h4>Create the function code</h4>
When creating an Agent for Amazon Bedrock, you can connect a Lambda function to the Action Group in order to execute the functions required by the agent. In this option, your agent is responsible for the execution of your functions. Let's create the lambda function tha implements the functions for `get_booking_details`, `create_booking` and `delete_booking`


```python
%%writefile lambda_function.py
import json
import uuid
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('restaurant_bookings')

def get_named_parameter(event, name):
    """
    Get a parameter from the lambda event
    """
    return next(item for item in event['parameters'] if item['name'] == name)['value']


def get_booking_details(booking_id):
    """
    Retrieve details of a restaurant booking
    
    Args:
        booking_id (string): The ID of the booking to retrieve
    """
    try:
        response = table.get_item(Key={'booking_id': booking_id})
        if 'Item' in response:
            return response['Item']
        else:
            return {'message': f'No booking found with ID {booking_id}'}
    except Exception as e:
        return {'error': str(e)}


def create_booking(date, name, hour, num_guests):
    """
    Create a new restaurant booking
    
    Args:
        date (string): The date of the booking
        name (string): Name to idenfity your reservation
        hour (string): The hour of the booking
        num_guests (integer): The number of guests for the booking
    """
    try:
        booking_id = str(uuid.uuid4())[:8]
        table.put_item(
            Item={
                'booking_id': booking_id,
                'date': date,
                'name': name,
                'hour': hour,
                'num_guests': num_guests
            }
        )
        return {'booking_id': booking_id}
    except Exception as e:
        return {'error': str(e)}


def delete_booking(booking_id):
    """
    Delete an existing restaurant booking
    
    Args:
        booking_id (str): The ID of the booking to delete
    """
    try:
        response = table.delete_item(Key={'booking_id': booking_id})
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {'message': f'Booking with ID {booking_id} deleted successfully'}
        else:
            return {'message': f'Failed to delete booking with ID {booking_id}'}
    except Exception as e:
        return {'error': str(e)}
    

def lambda_handler(event, context):
    # get the action group used during the invocation of the lambda function
    actionGroup = event.get('actionGroup', '')
    
    # name of the function that should be invoked
    function = event.get('function', '')
    
    # parameters to invoke function with
    parameters = event.get('parameters', [])

    if function == 'get_booking_details':
        booking_id = get_named_parameter(event, "booking_id")
        if booking_id:
            response = str(get_booking_details(booking_id))
            responseBody = {'TEXT': {'body': json.dumps(response)}}
        else:
            responseBody = {'TEXT': {'body': 'Missing booking_id parameter'}}

    elif function == 'create_booking':
        date = get_named_parameter(event, "date")
        name = get_named_parameter(event, "name")
        hour = get_named_parameter(event, "hour")
        num_guests = get_named_parameter(event, "num_guests")

        if date and hour and num_guests:
            response = str(create_booking(date, name, hour, num_guests))
            responseBody = {'TEXT': {'body': json.dumps(response)}}
        else:
            responseBody = {'TEXT': {'body': 'Missing required parameters'}}

    elif function == 'delete_booking':
        booking_id = get_named_parameter(event, "booking_id")
        if booking_id:
            response = str(delete_booking(booking_id))
            responseBody = {'TEXT': {'body': json.dumps(response)}}
        else:
            responseBody = {'TEXT': {'body': 'Missing booking_id parameter'}}

    else:
        responseBody = {'TEXT': {'body': 'Invalid function'}}

    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }
    }

    function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(function_response))

    return function_response
```

<h4>Create the required permissions</h4>
Now let's also create the lambda role and its required policies. For this case, we need the lambda to be able to access DynamoDB, that is why we also create a DynamoDB policy and attach to our Lambda. To do so, we will use the support function `create_lambda_role`.


```python
lambda_iam_role = create_lambda_role(agent_name, table_name)
```

<h4>Create the function</h4>

Now that we have the Lambda function code and its execution role, let's package it into a Zip file and create the Lambda resources


```python
lambda_function_name = f'{agent_name}-lambda'
```


```python
lambda_function = create_lambda(lambda_function_name, lambda_iam_role)
```

<h3>4.3 Create the IAM policies needed for the Agent</h3>

Now that we have created the Knowledge Base, our DynamoDB table and the Lambda function to execute the tasks for our agent, let's start creating our Agent.


First need to create the agent policies that allow bedrock model invocation and Knowledge Base query and the agent IAM role with the policy associated to it. We will allow this agent to invoke the Claude Sonnet model. Here we use the `create_agent_role_and_policies` to create the agent role and its required policies


```python
agent_role = create_agent_role_and_policies(agent_name, agent_foundation_model, kb_id=kb_id)
```


```python
agent_role
```

<h3>4.4 Create the Agent</h3>
Once the needed IAM role is created, we can use the bedrock agent client to create a new agent. To do so we use the [`create_agent`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/create_agent.html) api from boto3. It requires an agent name, underline foundation model and instruction. You can also provide an agent description. Note that the agent created is not yet prepared. We will focus on preparing the agent and then using it to invoke actions and use other APIs


```python
response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_role['Role']['Arn'],
    description=agent_description,
    idleSessionTTLInSeconds=1800,
    foundationModel=agent_foundation_model,
    instruction=agent_instruction,
)
response
```

Let's get our Agent ID. It will be important to perform operations with our agent


```python
agent_id = response['agent']['agentId']
print("The agent id is:",agent_id)
```

<h3>4.5 Create the Agent Action Group</h3>
We will now create an agent action group that uses the lambda function created before. The [`create_agent_action_group`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/create_agent_action_group.html) function provides this functionality. We will use `DRAFT` as the agent version since we haven't yet created an agent version or alias. To inform the agent about the action group functionalities, we will provide an action group description containing the functionalities of the action group.

In this example, we will provide the Action Group functionality using a [`functionSchema`](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-function.html).

To define the functions using a function schema, you need to provide the `name`, `description` and `parameters` for each function.


```python
agent_functions = [
    {
        'name': 'get_booking_details',
        'description': 'Retrieve details of a restaurant booking',
        'parameters': {
            "booking_id": {
                "description": "The ID of the booking to retrieve",
                "required": True,
                "type": "string"
            }
        }
    },
    {
        'name': 'create_booking',
        'description': 'Create a new restaurant booking',
        'parameters': {
            "date": {
                "description": "The date of the booking",
                "required": True,
                "type": "string"
            },
            "name": {
                "description": "Name to idenfity your reservation",
                "required": True,
                "type": "string"
            },
            "hour": {
                "description": "The hour of the booking",
                "required": True,
                "type": "string"
            },
            "num_guests": {
                "description": "The number of guests for the booking",
                "required": True,
                "type": "integer"
            }
        }
    },
    {
        'name': 'delete_booking',
        'description': 'Delete an existing restaurant booking',
        'parameters': {
            "booking_id": {
                "description": "The ID of the booking to delete",
                "required": True,
                "type": "string"
            }
        }
    },
]
```

We now use the function schema to create the agent action group using the [`create_agent_action_group`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/create_agent_action_group.html) API


```python
<h2>Pause to make sure agent is created</h2>
time.sleep(30)

<h2>Now, we can configure and create an action group here:</h2>
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


```python
agent_action_group_response
```

<h3>4.6 Allow the Agent to invoke the Action Group Lambda</h3>
Before using the action group, we need to allow the agent to invoke the lambda function associated with the action group. This is done via [resource-based policy](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-permissions.html#agents-permissions-lambda). Let's add the resource-based policy to the lambda function created


```python
<h2>Create allow to invoke permission on lambda</h2>
lambda_client = boto3.client('lambda')
response = lambda_client.add_permission(
    FunctionName=lambda_function_name,
    StatementId='allow_bedrock',
    Action='lambda:InvokeFunction',
    Principal='bedrock.amazonaws.com',
    SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}",
)

```


```python
response
```

<h3>4.7 Associate the Knowledge Base to the agent</h3>
Now we have created the Agent we can go ahead and associate the Knowledge Base we created earlier. 


```python
response = bedrock_agent_client.associate_agent_knowledge_base(
    agentId=agent_id,
    agentVersion='DRAFT',
    description='Access the knowledge base when customers ask about the plates in the menu.',
    knowledgeBaseId=kb_id,
    knowledgeBaseState='ENABLED'
)
```


```python
response
```

<h3>4.8 Prepare the Agent and create an alias</h3>

Let's create a DRAFT version of the agent that can be used for internal testing.



```python
response = bedrock_agent_client.prepare_agent(
    agentId=agent_id
)
print(response)
<h2>Pause to make sure agent is prepared</h2>
time.sleep(30)
```

You can invoke the DRAFT version of your agent using the test alias id `TSTALIASID` or you can create a new alias and a new version for your agent. Here we are also going to create an Agent alias to later on use to invoke it with the alias id created


```python
response = bedrock_agent_client.create_agent_alias(
    agentAliasName='TestAlias',
    agentId=agent_id,
    description='Test alias',
)

alias_id = response["agentAlias"]["agentAliasId"]
print("The Agent alias is:",alias_id)
time.sleep(30)
```

<h2>5. Test the Agent</h2>
Now that we've created the agent, let's use the `bedrock-agent-runtime` client to invoke this agent and perform some tasks. You can invoke your agent with the [`invoke_agent`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/invoke_agent.html) API


```python
def invokeAgent(query, session_id, enable_trace=False, session_state=dict()):
    end_session:bool = False
    
    # invoke the agent API
    agentResponse = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=agent_id,
        agentAliasId=alias_id, 
        sessionId=session_id,
        enableTrace=enable_trace, 
        endSession= end_session,
        sessionState=session_state
    )
    
    if enable_trace:
        logger.info(pprint.pprint(agentResponse))
    
    event_stream = agentResponse['completion']
    try:
        for event in event_stream:        
            if 'chunk' in event:
                data = event['chunk']['bytes']
                if enable_trace:
                    logger.info(f"Final answer ->\n{data.decode('utf8')}")
                agent_answer = data.decode('utf8')
                end_event_received = True
                return agent_answer
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                if enable_trace:
                    logger.info(json.dumps(event['trace'], indent=2))
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)
```

<h5>Invoke Agent to query Knowledge Base</h5>
Let's now use our support `invokeAgent` function to query our Knowledge Base with the Agent


```python
%%time
import uuid
session_id:str = str(uuid.uuid1())
query = "What are the starters in the childrens menu?"
response = invokeAgent(query, session_id)
print(response)
```

<h5>Invoke Agent to execute function from Action Group</h5>
Now let's test our Action Group functionality and create a new reservation


```python
%%time
query = "Hi, I am Anna. I want to create a booking for 2 people, at 8pm on the 5th of May 2024."
response = invokeAgent(query, session_id)
print(response)
```

<h5>Invoke Agent with prompt attribute</h5>

Great! We've used our agent to do the first reservation. However, often when booking tables in restaurants we are already logged in to systesm that know our names. How great would it be if our agent would know it as well?

To do so, we can use the session context to provide some attributes to our prompt. In this case we will provide it directly to the prompt using the [`promptSessionAttributes`](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-session-state.html) parameter. Let's also start a new session id so that our agent does not memorize our name.


```python
%%time
session_id:str = str(uuid.uuid1())
query = "I want to create a booking for 2 people, at 8pm on the 5th of May 2024."
session_state = {
    "promptSessionAttributes": {
        "name": "John"
    }
}
response = invokeAgent(query, session_id, session_state=session_state)
print(response)
```

<h5>Validating prompt attribute</h5>
Let's now use our session context to validate that the reservation was done under the correct name


```python
%%time
query = "What was the name used in my last reservation?"
response = invokeAgent(query, session_id)
print(response)
```

<h5>Retrieving information from the database in a new session</h5>

Next, let's confirm that our reservation system is working correctly. To do so, let's use our previous booking ID and retrieve our reservation details using a new session id


**Important**: remember to replace the information in next queries with your generated booking id


```python
%%time
session_id:str = str(uuid.uuid1())
query = "I want to get the information for booking 007659d1"
response = invokeAgent(query, session_id)
print(response)
```

<h5>Canceling reservation</h5>

As plans change, we would now like to cancel the reservation we just did using our Agent for it.


```python
%%time
query = "I want to delete the booking 007659d1"
response = invokeAgent(query, session_id)
print(response)
```

And let's make sure everything worked out correctly


```python
%%time
session_id:str = str(uuid.uuid1())
query = "I want to get the information for booking 007659d1"
response = invokeAgent(query, session_id)
print(response)
```

<h5>Handling context with PromptAttributes</h5>

With real-life applications, context is really important. We want to make reservations considering the current date and the days sorounding it. Amazon Bedrock Agents also allow you to provide temporal context for the agent with the prompt attributes. Let's test it with a reservation for tomorrow


```python
<h2>retrieving today</h2>
from datetime import datetime
today = datetime.today().strftime('%b-%d-%Y')
today
```


```python
%%time
<h2>reserving a table for tomorrow</h2>
session_id:str = str(uuid.uuid1())
query = "I want to create a booking for 2 people, at 8pm tomorrow."
session_state = {
    "promptSessionAttributes": {
        "name": "John",
        "today": today
    }
}
response = invokeAgent(query, session_id, session_state=session_state)
print(response)
```

And finally, let's validate our reservation

**Important**: remember to replace the booking id with the new one


```python
%%time
session_id:str = str(uuid.uuid1())
query = "I want to get the information for booking 98e6464f"
response = invokeAgent(query, session_id)
print(response)
```

<h5>Invoke Agent with Trace</h5>

Amazon Bedrock Agents also provides you with the details of steps being orchestrated by the Agent using the [Trace](https://docs.aws.amazon.com/bedrock/latest/userguide/trace-events.html). You can enable the trace during agent invocation. Let's now invoke the agent with the trace enabled


```python
%%time
session_id:str = str(uuid.uuid1())
query = "What are the desserts on the adult menu?"
response = invokeAgent(query, session_id, enable_trace=True)
print(response)
```

<h2>Agent Evaluation Framework - Testing the Agent (Optional)</h2>

The [Agent Evaluation Framework](https://awslabs.github.io/agent-evaluation/) offers a structured approach for assessing the performance, accuracy, and effectiveness of Bedrock Agents.

The next steps are optional, and show you how to write test cases and run them against the Bedrock Agent.


```python
!python3 -m pip install agent-evaluation==0.2.0 # Installs the agent-evaluation framework tool

!which agenteval # Checks the agent evaluation framework is properly installed
```

- The following sections prepare the `agenteval.yml` file by providing the Agent ID and Alias ID created with this notebook into line 5. In the `agenteval.yml` file you will find the different test cases defined to test the Agent.
- As of writing, only Claude 3 Sonnet is supported as an evaluator. The Claude-3 model specified in the yml file refers to Claude 3 Sonnet.


```python
agent_id # Prints the Agent ID for reference here

!sed -i 's/{{agent_id}}/{alias_id}/g' agenteval.yml
!sed -i 's/none/{agent_id}/' agenteval.yml
```


```python
<h2>Run the defined test cases that are part of the repo (i.e. the agenteval.yml file)</h2>

!agenteval run
```

- The output above shows the results of the testing evaluation. You can find a detailed report about the tests evaluation under the following generated file: `agenteval_summary.md.` You can preview it by right-clicking and select open with -> markdown preview
  
- You will notice that some new files have been generated as well once the test have been executed (e.g. `check_number_of_vacation.json`), where you will find the detailed traces from the test conversation between the test User and the test Agent.

<h2>6. Clean-up </h2>
Let's delete all the associated resources created to avoid unnecessary costs. 


```python
clean_up_resources(
    table_name, lambda_function, lambda_function_name, agent_action_group_response, agent_functions, 
    agent_id, kb_id, alias_id
)
```


```python
<h2>Delete the agent roles and policies</h2>
delete_agent_roles_and_policies(agent_name)
```


```python
<h2>delete KB</h2>
knowledge_base.delete_kb(delete_s3_bucket=True, delete_iam_roles_and_policies=True)
```
