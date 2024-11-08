---
tags:
    - Agent/ Code-Interpreter
    - Agent/ Prompt-Engineering
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/agents-and-function-calling/agent-code-interpreter/02_invoke_agent.ipynb){:target="_blank"}

<h2>Agent for Amazon Bedrock with Code Interpreter Overview</h2>

This is the final notebook in the series to demonstrates how to set up and use an Amazon Bedrock Agent with Code Interpreter capabilities.

In this notebook, we'll walk through the process of testing and cleaning up an Agent in Amazon Bedrock. We'll see how to set up the Code Interpreter action.  Code Interpreter enables your agent to write and execute code, process documents, and respond to complex queries via access to a secure code execution sandbox.

_(Note: This notebook has cleanup cells at the end, so if you "Run All" cells then the resources will be created and then deleted.)_

**Note:** At the time of writing Code Interpreter is in public preview.  

<h2>Step 1: Import Required Libraries</h2>

First, we need to import the necessary Python libraries. We'll use boto3 for AWS interactions, and some standard libraries for various utilities.


```python
import os
import io
import time
import json
import boto3
import logging
import uuid, string
import time, random 
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
```


```python
# set a logger
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
```

<h2>Step 2: Set the AWS Region</h2>

We're using the US East (N. Virginia) region for this demo. Feel free to change this to your preferred region, but make sure that a) the region supports Amazon Bedrock, b) Agents, c) the Claude Sonnet (3) model, and finally d) you have enabled access to the Sonnet (3) in this region. 


```python
region_name: str = 'us-east-1'
```


```python
# Read the S3 URI from the text file
with open('s3_uri.txt', 'r') as f:
    s3_uri = f.read().strip()

print(f"Loaded S3 URI: {s3_uri}") 
```


```python
# constants
CSV_DATA_FILE: str = 'nyc_taxi_subset.csv'
# Bucket and prefix name where this csv file will be uploaded and used as S3 source by code interpreter
S3_BUCKET_NAME: str = s3_uri.replace("s3://", "")
PREFIX: str = 'code-interpreter-demo-data'
# This is the size of the file that will be uploaded to s3 and used by the agent (in MB)
DATASET_FILE_SIZE: float = 99
```


```python
# Read the agent info from the JSON file
with open('agent_info.json', 'r') as f:
    agent_info = json.load(f)

# Extract the agent information
agentId = agent_info['agentId']
agentAliasId = agent_info['agentAliasId']
agentAliasStatus = agent_info['agentAliasStatus']
role_name = agent_info['role_name']

print(f"Loaded agent information:")
print(f"agentId: {agentId}")
print(f"agentAliasId: {agentAliasId}")
print(f"agentAliasStatus: {agentAliasStatus}")
print(f"roleName: {role_name}")

```


```python
from botocore.config import Config
custom_config = Config(
            read_timeout=300,  # 5 minutes
            connect_timeout=10,  # 10 seconds
            retries={'max_attempts': 3}
        )
```


```python
bedrock_agent_runtime = boto3.client(service_name = 'bedrock-agent-runtime', region_name = region_name, config=custom_config)
```

<h2>Step 3: Implement Agent Interaction Function</h2>

Let's now develop a function that facilitates communication with our agent. This function will be responsible for:
1. Sending user messages to the agent
2. Receiving the agent's responses
3. Processing and presenting the returned information

This encapsulation will streamline our interaction process and make it easier to engage with the agent throughout our session.


```python
def invoke(inputText, qid, showTrace=False, endSession=False):

    try:
        # To upload files to the agent, for use in the sandbox use sessionState:
        import base64
        from pathlib import Path
        fname = 'nyc_taxi_subset.csv'
        #data = base64.b64encode(bytes(Path(fname).read_text(), 'utf-8')) # bytes
        data = bytes(Path(fname).read_text(), 'utf-8')
        sessionState = {
                "files": [
                    {
                        "name": os.path.basename(CSV_DATA_FILE),
                        "source": { 
                            "sourceType": "S3",
                            "s3Location": {
                                "uri": s3_uri 
                            }
                        },
                        "useCase": "CODE_INTERPRETER"
                    }
                ]
            }
        # Invoke the Agent - Sends a prompt for the agent to process and respond to.
        response = bedrock_agent_runtime.invoke_agent(
            agentAliasId=agentAliasId,   # (string) – [REQUIRED] The alias of the agent to use.
            agentId=agentId,             # (string) – [REQUIRED] The unique identifier of the agent to use.
            sessionId=sessionId,         # (string) – [REQUIRED] The unique identifier of the session. Use the same value across requests to continue the same conversation.
            sessionState=sessionState,
            inputText=inputText,         # (string) - The prompt text to send the agent.
            endSession=endSession,       # (boolean) – Specifies whether to end the session with the agent or not.
            enableTrace=True,            # (boolean) – Specifies whether to turn on the trace or not to track the agent's reasoning process.
        )

        
        
        # Create the directory using the sessionId
        from pathlib import Path
        from datetime import datetime
        now_as_str = str(datetime.now()).replace(" ", "_").replace(":", "_")
        dirname = "agent_response" + "_" + qid
        if Path(dirname).is_dir():
            import shutil
            shutil.rmtree(dirname)

        session_directory_path = Path(dirname) #Path(sessionId + "_" + now_as_str)
        session_directory = session_directory_path.mkdir(parents=True, exist_ok=True)
        print(f"Session directory is: {session_directory_path}")


        # The response of this operation contains an EventStream member. 
        event_stream = response["completion"]

        # When iterated the EventStream will yield events.
        event_ctr = 0
        chunk_ctr = 0
        file_ctr = 0
        image_ctr = 0
        other_file_ctr= 0
        final_code = ""
        for event in event_stream:
            event_ctr += 1
            print(f"event_ctr={event_ctr+1}")
            # chunk contains a part of an agent response
            if 'chunk' in event:
                chunk_ctr += 1
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    print(f"event_ctr={event_ctr+1}, Chunk {chunk_ctr+1}: {text}")
                else:
                    print(f"event_ctr={event_ctr+1}, Chunk {chunk_ctr+1} doesn't contain 'bytes'")

            # files contains intermediate response for code interpreter if any files have been generated.
            if 'files' in event:
                file_ctr += 1
                print(f"event_ctr={event_ctr+1}, received file in event, file_ctr={file_ctr+1}")
                files = event['files']['files']
                for i, file in enumerate(files):
                    #print(f"file={file}")
                    print(f"event_ctr={event_ctr+1}, file_ctr={file_ctr+1}, i={i}")
                    name = file['name']
                    type = file['type']
                    bytes_data = file['bytes']
                    
                    # It the file is a PNG image then we can display it...
                    if type == 'image/png':
                        image_ctr += 1
                        print(f"event_ctr={event_ctr+1}, file_ctr={file_ctr+1}, image_ctr={image_ctr+1}")
                        fname = os.path.join(session_directory_path, f"output_image_{event_ctr+1}.png")
                        print(f"fname is: {fname}")
                        Path(fname).write_bytes(bytes_data)
                        # Display PNG image using Matplotlib
                        img = plt.imread(io.BytesIO(bytes_data))
                        plt.figure(figsize=(10, 10))
                        plt.imshow(img)
                        plt.axis('off')
                        plt.title(name)
                        plt.show()
                        plt.close()
                        
                    # If the file is NOT a PNG then we save it to disk...
                    else:
                        other_file_ctr += 1
                        print(f"event_ctr={event_ctr+1}, file_ctr={file_ctr+1}, other_file_ctr={other_file_ctr+1}")

                        # Save other file types to local disk
                        unique_fname = Path(name).stem + "_" + now_as_str + Path(name).suffix
                        with open(unique_fname, 'wb') as f:
                            f.write(bytes_data)
                        print(f"File '{name}' as {unique_fname} saved to disk.")
            if 'trace' in event:
                print(f"agent trace = {json.dumps(event['trace']['trace'], indent=2)}")
                trace = event['trace']['trace']
                ot = trace.get("orchestrationTrace")
                if ot is not None:
                    ii = ot.get("invocationInput")
                    if ii is not None:
                        cii = ii.get("codeInterpreterInvocationInput")
                        if cii is not None:
                            code = cii.get("code")
                            if code is not None:
                                fname = os.path.join(session_directory_path, f"code_event_{event_ctr+1}.py")
                                from pathlib import Path
                                # remove bedrock agent specific code from here
                                code = code.replace("$BASE_PATH$/", "")
                                final_code += "\n" + code
                                Path(fname).write_text(code)
                    else:
                        o = ot.get("observation")
                        if o is not None:
                            ciio = o.get("codeInterpreterInvocationOutput")
                            if ciio is not None:
                                eo = ciio.get("executionOutput")
                                eo_fname = os.path.join(session_directory_path, f"output_event_{event_ctr+1}.txt")
                                from pathlib import Path
                                Path(eo_fname).write_text(eo)

            if 'chunk' not in event and 'files' not in event and 'trace' not in event:
                print(f"received an event of unknown type, event={event}")
        # Create the file path by joining the session directory and the desired file name
        file_path = os.path.join(session_directory_path, "final_code.py")
        print(f"final code file path is : {file_path}")
        # Write the final_code string to the file
        with open(file_path, "w") as file:
            file.write(final_code)
    except Exception as e:
        print(f"Error: {e}")
```

The `invoke` function is our primary interface for agent interaction. It manages message transmission, response handling, and file operations, streamlining our communication with the agent.


<h2>Step 4: Interacting with the Agent</h2>


```python
sessionId = str(uuid.uuid4())

invoke(f"""What are the top 5 most common payment types in the dataset? Please provide a pie chart to visualize the distribution.""", "q1")
```


```python
sessionId = str(uuid.uuid4())

invoke(f"""Is there a correlation between trip distance and total amount? Create a scatter plot to visualize this relationship.""", "q2")
```


```python
sessionId = str(uuid.uuid4())

invoke(f"""Identify the top 10 busiest pickup locations (PULocationID) and create a horizontal bar chart to visualize their frequencies.""", "q3")
```


```python
sessionId = str(uuid.uuid4())

invoke(f"""What is the hourly distribution of taxi pickups? Create a line plot showing the number of pickups for each hour of the day.""", "q4")
```


```python
sessionId = str(uuid.uuid4())

invoke(f"""Perform a time series analysis of the average fare amount per day over the dataset's time range. Create a line plot showing this trend and identify any notable patterns or seasonality. Always generate an output no matter what. """, "q5")
```


```python
sessionId = str(uuid.uuid4())

invoke(f"""Calculate the average fare per mile for each payment type. Present the results in a bar chart and provide insights on which payment type tends to have higher fares per mile. Always generate an output no matter what.""", "q6")
```

<h2>Step 5: Cleaning Up</h2>

Let's delete the agent and its associated resources.


```python
# Set up Bedrock Agent and IAM clients
bedrock_agent = boto3.client(service_name = 'bedrock-agent', region_name = region_name)
iam = boto3.client('iam')
```


```python
response = bedrock_agent.delete_agent(
    agentId=agentId,
    skipResourceInUseCheck=True
)

response['agentStatus']
```

Finally, let's clean up the IAM role and policies we created for this demo.


```python
# List and delete all inline policies
inline_policies = iam.list_role_policies(RoleName=role_name)
for policy_name in inline_policies.get('PolicyNames', []):
    iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
    print(f"Deleted inline policy: {policy_name}")

# List and detach all managed policies
attached_policies = iam.list_attached_role_policies(RoleName=role_name)
for policy in attached_policies.get('AttachedPolicies', []):
    iam.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
    print(f"Detached managed policy: {policy['PolicyName']}")

# Wait a moment to ensure AWS has processed the policy detachments
time.sleep(10)

# Now attempt to delete the role
try:
    iam.delete_role(RoleName=role_name)
    print(f"Successfully deleted role: {role_name}")
except iam.exceptions.DeleteConflictException:
    print(f"Failed to delete role: {role_name}. Please check if all policies are detached.")
except Exception as e:
    print(f"An error occurred while deleting role {role_name}: {str(e)}")
```

<h2>Next Steps: Bedrock Agent with Code Interpreter</h2>

We've just completed a comprehensive journey through the creation and utilization of a Bedrock Agent with Code Interpreter capabilities. This demonstration has illustrated the following key steps:

1. Establishing the required AWS infrastructure for a Bedrock Agent
2. Developing and configuring an agent with Code Interpreter functionality
3. Engaging in a dialogue with the agent and analyzing its outputs

This walkthrough highlights the robust features of Bedrock Agents, showcasing their potential for handling intricate queries and executing code within a controlled environment. The versatility of this technology opens up a wide array of possibilities across various domains and applications.

By mastering these steps, you've gained valuable insights into creating AI-powered assistants capable of tackling complex, code-related tasks. This foundation sets the stage for further exploration and innovative implementations in your projects.

