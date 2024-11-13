---
tags:
    - Agents/ Function Definition
    - Agents/ Memory
    - Bedrock/ Prompt-Management
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/06-prompt-and-session-attributes/06-prompt-and-session-attributes.ipynb){:target="_blank"}"

<h2>Prompt and session parameters</h2>

Bedrock Agent provides two types of session attributes to maintain conversation context:

- sessionAttributes

- promptSessionAttributes

In this notebook, we will demonstrate how to use these attributes to personalize the conversation and simplify the dialog flow. 

We assume that the user enters the system through an SSO authentication process, which provides the agent with their first name, last name, and employee ID. We can store this information in  `sessionAttributes` to personalize the user experience throughout the conversation. 

The users will be able to interact with HR agent as designed in prior sessions. They can check available vacation days or request a new vacation leave. 

The agent is able to use `PromptSessionAttributes` to get temporal context, specifically, it has `CurrentDate` information stored in `PromptSessionAttributes`. If users ask relative information like "tomorrow", the agent can determine the exact date that "tomorrow" refers to.

<h2>Prerequisites</h2>
Before starting, let's update the botocore and boto3 packages to ensure we have the latest version


```python
!python3 -m pip install --upgrade -q botocore
!python3 -m pip install --upgrade -q boto3
!python3 -m pip install --upgrade -q awscli
```

Let's now check the boto3 version to ensure the correct version has been installed. Your version should be bigger or equal to 1.34.90.


```python
import boto3
import json
import time
import zipfile
from io import BytesIO
import uuid
import pprint
import logging
from datetime import datetime
print(boto3.__version__)
```


```python
<h2>setting logger</h2>
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
```

Let's now create the boto3 clients for the required AWS services


```python
<h2>getting boto3 clients for required AWS services</h2>
sts_client = boto3.client('sts')
iam_client = boto3.client('iam')
lambda_client = boto3.client('lambda')
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
```

Next we can set some configuration variables for the agent and for the lambda function being created


```python
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
region, account_id
```


```python
<h2>configuration variables</h2>
suffix = f"{region}-{account_id}"
agent_name = "hr-assistant-function-def"
agent_bedrock_allow_policy_name = f"{agent_name}-ba-{suffix}"
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
agent_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"
agent_description = "Agent for providing HR assistance to reserve vacation time off"
agent_instruction = "You are an HR agent, helping employees understand HR policies and manage vacation time"
agent_action_group_name = "VacationsActionGroup"
agent_action_group_description = "Actions for getting the number of available vactions days for an employee and reserve new vacation time in the system"
agent_alias_name = f"{agent_name}-alias"
lambda_function_role = f'{agent_name}-lambda-role-{suffix}'
lambda_function_name = f'{agent_name}-{suffix}'
```

<h2>Creating Lambda Function</h2>

We will now create a lambda function that interacts with the SQLite file `employee_database.db`. To do so we will:
1. Create the `employee_database.db` file which contains the employee database with some generated data.
2. Create the `lambda_function.py` file which contains the logic for our lambda function
3. Create the IAM role for our Lambda function
4. Create the lambda function infrastructure with the required permissions


```python
<h2>creating employee database to be used by lambda function</h2>
import sqlite3
import random
from datetime import date, timedelta

<h2>Connect to the SQLite database (creates a new one if it doesn't exist)</h2>
conn = sqlite3.connect('employee_database.db')
c = conn.cursor()

<h2>Create the employees table</h2>
c.execute('''CREATE TABLE IF NOT EXISTS employees
                (employee_id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT, employee_job_title TEXT, employee_start_date TEXT, employee_employment_status TEXT)''')

<h2>Create the vacations table</h2>
c.execute('''CREATE TABLE IF NOT EXISTS vacations
                (employee_id INTEGER, year INTEGER, employee_total_vacation_days INTEGER, employee_vacation_days_taken INTEGER, employee_vacation_days_available INTEGER, FOREIGN KEY(employee_id) REFERENCES employees(employee_id))''')

<h2>Create the planned_vacations table</h2>
c.execute('''CREATE TABLE IF NOT EXISTS planned_vacations
                (employee_id INTEGER, vacation_start_date TEXT, vacation_end_date TEXT, vacation_days_taken INTEGER, FOREIGN KEY(employee_id) REFERENCES employees(employee_id))''')

<h2>Generate some random data for 10 employees</h2>
employee_names = ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams', 'Tom Brown', 'Emily Davis', 'Michael Wilson', 'Sarah Taylor', 'David Anderson', 'Jessica Thompson']
job_titles = ['Manager', 'Developer', 'Designer', 'Analyst', 'Accountant', 'Sales Representative']
employment_statuses = ['Active', 'Inactive']

for i in range(10):
    name = employee_names[i]
    job_title = random.choice(job_titles)
    start_date = date(2015 + random.randint(0, 7), random.randint(1, 12), random.randint(1, 28)).strftime('%Y-%m-%d')
    employment_status = random.choice(employment_statuses)
    c.execute("INSERT INTO employees (employee_name, employee_job_title, employee_start_date, employee_employment_status) VALUES (?, ?, ?, ?)", (name, job_title, start_date, employment_status))
    employee_id = c.lastrowid

    # Generate vacation data for the current employee
    for year in range(date.today().year, date.today().year - 3, -1):
        total_vacation_days = random.randint(10, 30)
        days_taken = random.randint(0, total_vacation_days)
        days_available = total_vacation_days - days_taken
        c.execute("INSERT INTO vacations (employee_id, year, employee_total_vacation_days, employee_vacation_days_taken, employee_vacation_days_available) VALUES (?, ?, ?, ?, ?)", (employee_id, year, total_vacation_days, days_taken, days_available))

        # Generate some planned vacations for the current employee and year
        num_planned_vacations = random.randint(0, 3)
        for _ in range(num_planned_vacations):
            start_date = date(year, random.randint(1, 12), random.randint(1, 28)).strftime('%Y-%m-%d')
            end_date = (date(int(start_date[:4]), int(start_date[5:7]), int(start_date[8:])) + timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d')
            days_taken = (date(int(end_date[:4]), int(end_date[5:7]), int(end_date[8:])) - date(int(start_date[:4]), int(start_date[5:7]), int(start_date[8:])))
            c.execute("INSERT INTO planned_vacations (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (?, ?, ?, ?)", (employee_id, start_date, end_date, days_taken.days))

<h2>Commit the changes and close the connection</h2>
conn.commit()
conn.close()
```

Let's now create our lambda function. It implements the functionality for `get_available_vacations_days` for a given employee_id and `reserve_vacation_time` for an employee giving a start and end date


```python
%%writefile lambda_function.py
import os
import json
import shutil
import sqlite3
from datetime import datetime

def get_available_vacations_days(employee_id):
    # Connect to the SQLite database
    conn = sqlite3.connect('/tmp/employee_database.db')
    c = conn.cursor()

    if employee_id:

        # Fetch the available vacation days for the employee
        c.execute("""
            SELECT employee_vacation_days_available
            FROM vacations
            WHERE employee_id = ?
            ORDER BY year DESC
            LIMIT 1
        """, (employee_id,))

        available_vacation_days = c.fetchone()

        if available_vacation_days:
            available_vacation_days = available_vacation_days[0]  # Unpack the tuple
            print(f"Available vacation days for employed_id {employee_id}: {available_vacation_days}")
            conn.close()
            return available_vacation_days
        else:
            return_msg = f"No vacation data found for employed_id {employee_id}"
            print(return_msg)
            conn.close()
            return return_msg
    else:
        raise Exception(f"No employeed id provided")

    # Close the database connection
    conn.close()
    
    
def reserve_vacation_time(employee_id, start_date, end_date):
    # Connect to the SQLite database

    conn = sqlite3.connect('/tmp/employee_database.db')
    c = conn.cursor()
    try:
        # Calculate the number of vacation days
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        vacation_days = (end_date - start_date).days + 1

        # Get the current year
        current_year = start_date.year

        # Check if the employee exists
        c.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        employee = c.fetchone()
        if employee is None:
            return_msg = f"Employee with ID {employee_id} does not exist."
            print(return_msg)
            conn.close()
            return

        # Check if the vacation days are available for the employee in the current year
        c.execute("SELECT employee_vacation_days_available FROM vacations WHERE employee_id = ? AND year = ?", (employee_id, current_year))
        available_days = c.fetchone()
        if available_days is None or available_days[0] < vacation_days:
            return_msg = f"Employee with ID {employee_id} does not have enough vacation days available for the requested period."
            print(return_msg)
            conn.close()
            return

        # Insert the new vacation into the planned_vacations table
        c.execute("INSERT INTO planned_vacations (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (?, ?, ?, ?)", (employee_id, start_date, end_date, vacation_days))

        # Update the vacations table with the new vacation days taken
        c.execute("UPDATE vacations SET employee_vacation_days_taken = employee_vacation_days_taken + ?, employee_vacation_days_available = employee_vacation_days_available - ? WHERE employee_id = ? AND year = ?", (vacation_days, vacation_days, employee_id, current_year))

        conn.commit()
        return_msg = f"Vacation booked successfully for employee with ID {employee_id} from {start_date} to {end_date}."
        print(return_msg)
        # Close the database connection
        conn.close()
        return return_msg
    except Exception as e:
        raise Exception(f"Error occurred: {e}")
        conn.rollback()
        # Close the database connection
        conn.close()
        return f"Error occurred: {e}"
        

def lambda_handler(event, context):
    original_db_file = 'employee_database.db'
    target_db_file = '/tmp/employee_database.db'
    if not os.path.exists(target_db_file):
        shutil.copy2(original_db_file, target_db_file)
        
    # Retrieve agent session attributes for context 
    session_attributes = event.get('sessionAttributes', {})
    first_name = session_attributes.get('firstName', '')
    last_name = session_attributes.get('lastName', '')
    employee_id = session_attributes.get('employeeId', '')
    current_date = event.get('promptSessionAttributes', {}).get('currentDate', '')
    
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    responseBody =  {
        "TEXT": {
            "body": "Error, no function was called"
        }
    }
    
    if function == 'get_available_vacations_days':
        ## If we were not using session attributes, we would need to pass employee ID as a parameter

        # employee_id = None
        # for param in parameters:
        #     if param["name"] == "employee_id":
        #         employee_id = param["value"]

        if not employee_id:
            raise Exception("Missing mandatory parameter: employee_id")
        vacation_days = get_available_vacations_days(employee_id)
        responseBody =  {
            'TEXT': {
                "body": f"available vacation days for employed_id {employee_id}: {vacation_days}"
            }
        }
    elif function == 'reserve_vacation_time':
        # employee_id = None
        start_date = None
        end_date = None
        for param in parameters:
            # if param["name"] == "employee_id":
            #     employee_id = param["value"]
            if param["name"] == "start_date":
                start_date = param["value"]
            if param["name"] == "end_date":
                end_date = param["value"]
            
        # if not employee_id:
        #     raise Exception("Missing mandatory parameter: employee_id")
        if not start_date:
            raise Exception("Missing mandatory parameter: start_date")
        if not end_date:
            raise Exception("Missing mandatory parameter: end_date")
        
        completion_message = reserve_vacation_time(employee_id, start_date, end_date)
        responseBody =  {
            'TEXT': {
                "body": completion_message
            }
        }  
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    function_response = {
                    'response': action_response,
                    'messageVersion': event['messageVersion'],
                    'sessionState': {
                        'sessionAttributes': session_attributes,
                        'promptSessionAttributes': event.get('promptSessionAttributes', {})
                                    }
                        }
    print("Response: {}".format(function_response))

    return function_response

```

Next let's create the lambda IAM role and policy to invoke a Bedrock model


```python
<h2>Create IAM Role for the Lambda function</h2>
try:
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)

    lambda_iam_role = iam_client.create_role(
        RoleName=lambda_function_role,
        AssumeRolePolicyDocument=assume_role_policy_document_json
    )

    # Pause to make sure role is created
    time.sleep(10)
except:
    lambda_iam_role = iam_client.get_role(RoleName=lambda_function_role)

iam_client.attach_role_policy(
    RoleName=lambda_function_role,
    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
)
```

We can now package the lambda function to a Zip file and create the lambda infrastructure using boto3


```python
<h2>Package up the lambda function code</h2>
s = BytesIO()
z = zipfile.ZipFile(s, 'w')
z.write("lambda_function.py")
z.write("employee_database.db")
z.close()
zip_content = s.getvalue()

<h2>Create Lambda Function</h2>
lambda_function = lambda_client.create_function(
    FunctionName=lambda_function_name,
    Runtime='python3.12',
    Timeout=180,
    Role=lambda_iam_role['Role']['Arn'],
    Code={'ZipFile': zip_content},
    Handler='lambda_function.lambda_handler'
)
```

<h2>Create Agent</h2>
We will now create the agent. To do so, we first need to create the agent policies that allow bedrock model invocation and the agent IAM role with the policy associated to it. We will allow this agent to invoke the Claude Sonnet model


```python
<h2>Create IAM policies for agent</h2>
bedrock_agent_bedrock_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                f"arn:aws:bedrock:{region}::foundation-model/{agent_foundation_model}"
            ]
        }
    ]
}

bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)

agent_bedrock_policy = iam_client.create_policy(
    PolicyName=agent_bedrock_allow_policy_name,
    PolicyDocument=bedrock_policy_json
)


```


```python
<h2>Create IAM Role for the agent and attach IAM policies</h2>
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": "bedrock.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
    }]
}

assume_role_policy_document_json = json.dumps(assume_role_policy_document)
agent_role = iam_client.create_role(
    RoleName=agent_role_name,
    AssumeRolePolicyDocument=assume_role_policy_document_json
)

<h2>Pause to make sure role is created</h2>
time.sleep(10)
    
iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_bedrock_policy['Policy']['Arn']
)
```

<h3>Creating agent</h3>
Once the needed IAM role is created, we can use the bedrock agent client to create a new agent. To do so we use the `create_agent` function. It requires an agent name, underline foundation model and instruction. You can also provide an agent description. Note that the agent created is not yet prepared. We will focus on preparing the agent and then using it to invoke actions and use other APIs


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

Let's now store the agent id in a local variable to use it on the next steps


```python
agent_id = response['agent']['agentId']
agent_id
```

<h2>Create Agent Action Group</h2>
We will now create an agent action group that uses the lambda function created before. The [`create_agent_action_group`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/create_agent_action_group.html) function provides this functionality. We will use `DRAFT` as the agent version since we haven't yet create an agent version or alias. To inform the agent about the action group functionalities, we will provide an action group description containing the functionalities of the action group.

In this example, we will provide the Action Group functionality using a `functionSchema`. You can also provide an `APISchema`. The notebook [02-create-agent-with-api-schema.ipynb](02-create-agent-with-api-schema/02-create-agent-with-api-schema.ipynb) provides an example of it.

To define the functions using a function schema, you need to provide the `name`, `description` and `parameters` for each function.

NOTE: Since we are taking advantage of Agent Session Attributes, we are NOT passing in employee ID as an explicit parameter in our functions. Instead, the action will be able to retrieve such context directly from the session.


```python
agent_functions = [
    {
        'name': 'get_available_vacations_days',
        'description': 'get the number of vacation days available for the current employee',
        'parameters': {}
    },
    {
        'name': 'reserve_vacation_time',
        'description': 'reserve a number of vacation days for the current employee',
        'parameters': {
            "start_date": {
                "description": "the start date for the vacation time off",
                "required": True,
                "type": "string"
            },
            "end_date": {
                "description": "the end date for the vacation time off",
                "required": True,
                "type": "string"
            }
        }
    },
]
```


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

<h2>Allowing Agent to invoke Action Group Lambda</h2>
Before using the action group, we need to allow the agent to invoke the lambda function associated with the action group. This is done via resource-based policy. Let's add the resource-based policy to the lambda function created


```python
<h2>Create allow invoke permission on lambda</h2>
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

<h2>Preparing Agent</h2>

Let's create a DRAFT version of the agent that can be used for internal testing.



```python
response = bedrock_agent_client.prepare_agent(
    agentId=agent_id
)
print(response)
```


```python
<h2>Pause to make sure agent is prepared</h2>
time.sleep(30)

<h2>Extract the agentAliasId from the response</h2>
agent_alias_id = "TSTALIASID"
```

<h2>Invoke Agent</h2>

Now that we've created the agent, let's use the `bedrock-agent-runtime` client to invoke this agent and perform some tasks.

<h3>Session Attribute</h3>

By leveraging `sessionAttributes`, we can provide a personalized experience, such as greeting the user by name and retrieving their specific data based on their employee ID. As long as the same `sessionId` is used throughout the conversation, the user's information will be accessible from `sessionAttributes`.


```python
<h2>Assuming we have collected the following user information from SSO authentication</h2>
first_name = "John"
last_name = "Doe"
employee_id = "1"
```


```python
<h2>create a random id for session initiator id</h2>
session_id:str = str(uuid.uuid1())
enable_trace:bool = True
end_session:bool = False

<h2>invoke the agent API</h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="Hello, I would like to check my vacation balance.",
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    endSession=end_session,
    sessionState={
        "sessionAttributes": {
            "firstName": first_name,
            "lastName": last_name,
            "employeeId": employee_id
        }
    }
)

logger.info(pprint.pprint(agentResponse))
```


```python
%%time
event_stream = agentResponse['completion']
try:
    for event in event_stream:        
        if 'chunk' in event:
            data = event['chunk']['bytes']
            logger.info(f"Final answer ->\n{data.decode('utf8')}")
            agent_answer = data.decode('utf8')
            end_event_received = True
            # End event indicates that the request finished successfully
        elif 'trace' in event:
            logger.info(json.dumps(event['trace'], indent=2))
        else:
            raise Exception("unexpected event.", event)
except Exception as e:
    raise Exception("unexpected event.", e)
```


```python
<h2>And here is the response if you just want to see agent's reply</h2>
print(agent_answer)
```

<h3>Prompt Session Attribute</h3>



`promptSessionAttributes` allow you to provide dynamic information for the current turn of the conversation. By leveraging `promptSessionAttributes`, you can handle user requests that involve relative time expressions, such as "next Monday" or "tomorrow".

In our use case, when a customer mentions a relative time, we can set the current date in the `promptSessionAttributes`. The agent can then use this information to convert the relative time expression into a precise date.


```python
<h2>create a random id for session initiator id</h2>
session_id:str = str(uuid.uuid1())
enable_trace:bool = True
end_session:bool = False

<h2>invoke the agent API </h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="Please book vacation for me from next Monday to next Tuesday",
    agentId=agent_id,
    agentAliasId=agent_alias_id,
    sessionId=session_id,
    enableTrace=enable_trace,
    endSession=end_session,
    sessionState={
        "sessionAttributes": {
            "firstName": first_name,
            "lastName": last_name,
            "employeeId": employee_id
        },
        "promptSessionAttributes": {
            "currentDate": datetime.now().strftime("%Y-%m-%d"),
        }
    }
)

logger.info(pprint.pprint(agentResponse))
```


```python
%%time
event_stream = agentResponse['completion']
try:
    for event in event_stream:        
        if 'chunk' in event:
            data = event['chunk']['bytes']
            logger.info(f"Final answer ->\n{data.decode('utf8')}")
            agent_answer = data.decode('utf8')
            end_event_received = True
            # End event indicates that the request finished successfully
        elif 'trace' in event:
            logger.info(json.dumps(event['trace'], indent=2))
        else:
            raise Exception("unexpected event.", event)
except Exception as e:
    raise Exception("unexpected event.", e)
```


```python
<h2>And here is the response if you just want to see agent's reply</h2>
print(agent_answer)
```


```python
<h2>invoke the agent API with same Session ID</h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="How much vacation time do I have left?",
    agentId=agent_id,
    agentAliasId=agent_alias_id,
    sessionId=session_id,
    enableTrace=enable_trace,
    endSession=end_session,
    sessionState={
        "sessionAttributes": {
            "firstName": first_name,
            "lastName": last_name,
            "employeeId": employee_id
        },
        "promptSessionAttributes": {
            "currentDate": datetime.now().strftime("%Y-%m-%d"),
        }
    }
)

logger.info(pprint.pprint(agentResponse))
```


```python
%%time
event_stream = agentResponse['completion']
try:
    for event in event_stream:        
        if 'chunk' in event:
            data = event['chunk']['bytes']
            logger.info(f"Final answer ->\n{data.decode('utf8')}")
            agent_answer = data.decode('utf8')
            end_event_received = True
            # End event indicates that the request finished successfully
        elif 'trace' in event:
            logger.info(json.dumps(event['trace'], indent=2))
        else:
            raise Exception("unexpected event.", event)
except Exception as e:
    raise Exception("unexpected event.", e)
```


```python
<h2>And here is the response if you just want to see agent's reply</h2>
print(agent_answer)
```

<h2>Clean up (optional)</h2>

The next steps are optional and demonstrate how to delete our agent. To delete the agent we need to:

1. update the action group to disable it
2. delete agent action group
4. delete agent
5. delete lambda function
6. delete the created IAM roles and policies



```python
<h2>This is not needed, you can delete agent successfully after deleting alias only</h2>
<h2>Additionaly, you need to disable it first</h2>
action_group_id = agent_action_group_response['agentActionGroup']['actionGroupId']
action_group_name = agent_action_group_response['agentActionGroup']['actionGroupName']

response = bedrock_agent_client.update_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupId= action_group_id,
    actionGroupName=action_group_name,
    actionGroupExecutor={
        'lambda': lambda_function['FunctionArn']
    },
    functionSchema={
        'functions': agent_functions
    },
    actionGroupState='DISABLED',
)

action_group_deletion = bedrock_agent_client.delete_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupId= action_group_id
)
```


```python
agent_deletion = bedrock_agent_client.delete_agent(
    agentId=agent_id
)
```


```python
<h2>Delete Lambda function</h2>
lambda_client.delete_function(
    FunctionName=lambda_function_name
)
```


```python
<h2>Delete IAM Roles and policies</h2>

for policy in [agent_bedrock_allow_policy_name]:
    iam_client.detach_role_policy(RoleName=agent_role_name, PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}')
    
iam_client.detach_role_policy(RoleName=lambda_function_role, PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')

for role_name in [agent_role_name, lambda_function_role]:
    iam_client.delete_role(
        RoleName=role_name
    )

for policy in [agent_bedrock_policy]:
    iam_client.delete_policy(
        PolicyArn=policy['Policy']['Arn']
)

```

<h2>Conclusion</h2>
We have now experimented with SessionAttributes and PromptSessionAttributes fo

<h2>Take aways</h2>
Adapt this notebook to create new agents using function definitions for your application

<h2>Thank You</h2>
