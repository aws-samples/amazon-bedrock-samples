---
tags:
    - Use cases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/use-case-examples/agentsforbedrock-retailagent/workshop/test_retailagent_agentsforbedrock.ipynb){:target="_blank"}"

```python
#Needs awscli-1.29.73-py3-none-any.whl, boto3-1.28.73-py3-none-any.whl, botocore-1.31.73-py3-none-any.whl
```


```python
import uuid

import pprint
import botocore
import logging
import sys
import boto3
import botocore

!{sys.executable} -m pip install boto3-1.28.73-py3-none-any.whl
!{sys.executable} -m pip install botocore-1.31.73-py3-none-any.whl
!{sys.executable} -m pip install awscli-1.29.54-py3-none-any.whl

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

```


```python


```


```python
<h2>exit out if the Boto23 (Python) SDK versions are not correct</h2>
assert boto3.__version__ == "1.28.73"
assert botocore.__version__ == "1.31.73"

```


```python
input_text:str = "I am looking to buy running shoes?" # replace this with a prompt relevant to your agent
agent_id:str = '#####' # note this from the agent console on Bedrock
agent_alias_id:str = 'TSTALIASID' # fixed for draft version of the agent
session_id:str = str(uuid.uuid1()) # random identifier
enable_trace:bool = True

```


```python
<h2>create an boto3 bedrock agent client</h2>
client = boto3.client("bedrock-agent-runtime")
logger.info(client)

```


```python

<h2>invoke the agent API</h2>
response = client.invoke_agent(inputText=input_text,
    agentId=agent_id,
    agentAliasId=agent_alias_id,
    sessionId=session_id,
    enableTrace=enable_trace
)

logger.info(pprint.pprint(response))

```


```python
%%time
import json
event_stream = response['completion']
try:
    for event in event_stream:        
        if 'chunk' in event:
            data = event['chunk']['bytes']
            logger.info(f"Final answer ->\n{data.decode('utf8')}") 
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

```
