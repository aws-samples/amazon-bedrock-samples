---
tags:
    - Agents/ Return of Control
    - Agents/ Function Definition
    - Agents/ Tool Binding
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/03-create-agent-with-return-of-control/03-create-agent-with-return-of-control.ipynb){:target="_blank"}"

<h2>Create Agent with Return of Control (ROC)</h2>

In this notebook we will create an Agent for Amazon Bedrock using the new capabilities for function definition and return of control. 

We will use the HR agent as example. With this agent, you can check your available vacation days and request a new vacation leave. We will use a local function to define the logic that checks for the available vacation days and book new ones. Notice that this example does not need an API Schema file, nor does it need a Lambda function.

For this example, we will generate some employee data using an [SQLite](https://www.sqlite.org/) database

<h2>Pre-requisites</h2>
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
import uuid
import pprint
import logging
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
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
```

Next we can set some configuration variables for the agent


```python
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
region, account_id
```


```python
<h2>configuration variables</h2>
suffix = f"{region}-{account_id}"
agent_name = "hr-assistant-function-roc"
agent_bedrock_allow_policy_name = f"{agent_name}-ba-{suffix}"
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
agent_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"
agent_description = "Agent for providing HR assistance to book holidays"
agent_instruction = "You are an HR agent, helping employees understand HR policies and manage vacation time"
agent_action_group_name = "VacationsActionGroup"
agent_action_group_description = "Actions for getting the number of available vactions days for an employee and book new vacations in the system"
agent_alias_name = f"{agent_name}-alias"
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
Once the needed IAM role is created, we can use the Bedrock agent client to create a new agent. To do so we use the `create_agent` function. It requires an agent name, underlying foundation model and instructions. You can also provide an agent description. Note that the agent created is not yet prepared. We will focus on preparing the agent and then using it to invoke actions and use other APIs.


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
We will now create an agent action group. The [`create_agent_action_group`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/create_agent_action_group.html) function provides this functionality. We will use `DRAFT` as the agent version since we haven't yet create an agent version or alias. To inform the agent about the action group functionalities, we will provide an action group description containing the functionalities of the action group.

In this example, we will provide the Action Group functionality using a `functionSchema`. You can also provide and `APISchema`. The notebook [02-create-agent-with-api-schema.ipynb](02-create-agent-with-api-schema/02-create-agent-with-api-schema.ipynb) provides an example of it.

To define the functions using a function schema, you need to provide the `name`, `description` and `parameters` for each function.


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
        'description': 'reserve vacation time for a specific employee - you need all parameters to reserve vacation time',
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
```

Here we create the action group with a `customContrl` executor of `RETURN_CONTROL`. This lets the agent know that instead of executing the function, it should simply return the appropriate function and parameters. The client application is then responsible for executing the function.


```python
<h2>Pause to make sure agent is created</h2>
time.sleep(30)
<h2>Now, we can configure and create an action group here:</h2>
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


```python
agent_action_group_response
```

<h2>Preparing Agent</h2>

Let's create a DRAFT version of the agent that can be used for internal testing.



```python
response = bedrock_agent_client.prepare_agent(
    agentId=agent_id
)
print(response)
```

<h2>Invoke Agent</h2>

Now that we've created the agent, let's use the `bedrock-agent-runtime` client to invoke this agent and perform some tasks.


```python
<h2>Pause to make sure agent is prepared</h2>
time.sleep(30)

<h2>Extract the agentAliasId from the response</h2>
agent_alias_id = "TSTALIASID"
```


```python
<h2>create a random id for session initiator id</h2>
session_id:str = str(uuid.uuid1())
enable_trace:bool = False
end_session:bool = False
<h2>Pause to make sure agent alias is ready</h2>
<h2>time.sleep(30)</h2>

<h2>invoke the agent API</h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="how much vacation time does employee 1 have available?",
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    endSession= end_session
)

logger.info(pprint.pprint(agentResponse))
```


```python
%%time
event_stream = agentResponse['completion']
for event in event_stream:
    if 'returnControl' in event:
        pprint.pp(event)
```

<h2>Defining function implementation</h2>

Let's now implement our functions to get the vacation information for an employee_id and to book a vacation for an employee_id between start_date and end_dates.

To do so, we will first create an SQLite database with generated data


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

Next let's use the generated file `employee_database.db` to provide the results for our query by implementing `get_available_vacations_days` and `reserve_vacation_time`


```python
import sqlite3

def get_available_vacations_days(employee_id):
    # Connect to the SQLite database
    conn = sqlite3.connect('employee_database.db')
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
        conn.close()
        raise Exception(f"No employeed id provided")
    
    
def reserve_vacation_time(employee_id, start_date, end_date):
    # Connect to the SQLite database
    conn = sqlite3.connect('employee_database.db')
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
            return return_msg

        # Check if the vacation days are available for the employee in the current year
        c.execute("SELECT employee_vacation_days_available FROM vacations WHERE employee_id = ? AND year = ?", (employee_id, current_year))
        available_days = c.fetchone()
        if available_days is None or available_days[0] < vacation_days:
            return_msg = f"Employee with ID {employee_id} does not have enough vacation days available for the requested period."
            print(return_msg)
            conn.close()
            return return_msg

        # Insert the new vacation into the planned_vacations table
        c.execute("INSERT INTO planned_vacations (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (?, ?, ?, ?)", (employee_id, start_date, end_date, vacation_days))

        # Update the vacations table with the new vacation days taken
        c.execute("UPDATE vacations SET employee_vacation_days_taken = employee_vacation_days_taken + ?, employee_vacation_days_available = employee_vacation_days_available - ? WHERE employee_id = ? AND year = ?", (vacation_days, vacation_days, employee_id, current_year))

        conn.commit()
        print(f"Vacation booked successfully for employee with ID {employee_id} from {start_date} to {end_date}.")
        # Close the database connection
        conn.close()
        return f"Vacation booked successfully for employee with ID {employee_id} from {start_date} to {end_date}."
    except Exception as e:
        conn.rollback()
        # Close the database connection
        conn.close()
        raise Exception(f"Error occurred: {e}")
```


```python
print(event["returnControl"]["invocationInputs"][0]["functionInvocationInput"]["function"])
```

We can now call the `get_available_vacations_days` function with the parameters provided by the agent


```python
available_vacation_days = None
for invocationInput in event["returnControl"]["invocationInputs"]:
    function_to_call = invocationInput["functionInvocationInput"]["function"]
    if function_to_call == "get_available_vacations_days":
        employee_id = None
        for param in invocationInput["functionInvocationInput"]["parameters"]:
            if param["name"] == "employee_id":
                employee_id = param["value"]
        if employee_id:
            available_vacation_days = get_available_vacations_days(employee_id)
available_vacation_days
```

<h2>Invoking the agent with the function results</h2>
Finally, we need to invoke the agent passing the function results as a parameter. This lets us use the agent for generating the final response.


```python
raw_response_with_roc = bedrock_agent_runtime_client.invoke_agent(
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    sessionState={
        'invocationId': event["returnControl"]["invocationId"],
        'returnControlInvocationResults': [{
                'functionResult': {
                    'actionGroup': event["returnControl"]["invocationInputs"][0]["functionInvocationInput"]["actionGroup"],
                    'function': event["returnControl"]["invocationInputs"][0]["functionInvocationInput"]["function"],
                    'responseBody': {
                        "TEXT": {
                            'body': "available_vacation_days: "+str(available_vacation_days)
                        }
                    }
                }
        }]}
)
```


```python
print(raw_response_with_roc)
```


```python
%%time
event_stream = raw_response_with_roc['completion']
for event in event_stream:
    print(event)
```

<h3>Show how ROC handles input text that cannot be resolved with available functions</h3>


```python
def simple_agent_roc_invoke(input_text, agent_id, agent_alias_id, session_id=None, enable_trace=False, end_session=False):
    agentResponse = bedrock_agent_runtime_client.invoke_agent(
        inputText=input_text,
        agentId=agent_id,
        agentAliasId=agent_alias_id, 
        sessionId=session_id,
        enableTrace=enable_trace, 
        endSession= end_session
    )
    logger.info(pprint.pprint(agentResponse))
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
            elif 'returnControl' in event:
                pprint.pp(event)
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)

```

First show a request that has nothing to do with the agent and its available functions.


```python
simple_agent_roc_invoke("who is the president of the United States?", agent_id, agent_alias_id, session_id)

```

Now show what happens when insufficient parameters were provided. In this case, no vacation start date.


```python
simple_agent_roc_invoke("reserve 2 days off for employee 2", agent_id, agent_alias_id, session_id)
```

<h2>Clean up (optional)</h2>

The next steps are optional and demonstrate how to delete our agent. To delete the agent we need to:

1. update the action group to disable it
2. delete agent action group
4. delete agent
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
        'customControl': 'RETURN_CONTROL'
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
<h2>Delete IAM Roles and policies</h2>

for policy in [agent_bedrock_allow_policy_name]:
    iam_client.detach_role_policy(RoleName=agent_role_name, PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}')
    
for role_name in [agent_role_name]:
    iam_client.delete_role(
        RoleName=role_name
    )

for policy in [agent_bedrock_policy]:
    iam_client.delete_policy(
        PolicyArn=policy['Policy']['Arn']
)

```

<h2>Conclusion</h2>
We have now experimented with using boto3 SDK to create, invoke and delete an agent created using function definitions.

<h2>Take aways</h2>
Adapt this notebook to create new agents using function definitions for your application

<h2>Thank You</h2>
