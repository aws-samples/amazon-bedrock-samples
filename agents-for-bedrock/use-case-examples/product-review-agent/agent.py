import boto3
import uuid
import logging
import json

bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
agent_id = '<your agent id>'
agent_alias_id = '<your agent alias>'
enable_trace = False
end_session = False
session_id = str(uuid.uuid4())

def invoke_agent(input_text):
# invoke the agent API
    response = bedrock_agent_runtime_client.invoke_agent(
        inputText=input_text,
        agentId=agent_id,
        agentAliasId=agent_alias_id, 
        sessionId=session_id,
        enableTrace=enable_trace, 
        endSession= end_session
    )
    
    try:
        for event in response['completion']:        
            if 'chunk' in event:
                data = event['chunk']['bytes']
                yield data.decode('utf8')
    except Exception as e:
        raise Exception("unexpected event.", e)
