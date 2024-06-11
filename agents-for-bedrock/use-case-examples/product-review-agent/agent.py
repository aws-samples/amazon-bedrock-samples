import boto3
import uuid
import logging
import json

class ProductReviewAgent():
    def __init__(self,args):
        self.bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
        self.agent_id = args.id
        self.agent_alias_id = args.alias
        self.enable_trace = False
        self.end_session = False
        self.session_id = str(uuid.uuid4())

    def invoke_agent(self,input_text):
    # invoke the agent API
        response = self.bedrock_agent_runtime_client.invoke_agent(
            inputText=input_text,
            agentId=self.agent_id,
            agentAliasId=self.agent_alias_id, 
            sessionId=self.session_id,
            enableTrace=self.enable_trace, 
            endSession=self.end_session
        )
        
        try:
            for event in response['completion']:        
                if 'chunk' in event:
                    data = event['chunk']['bytes']
                    yield data.decode('utf8')
        except Exception as e:
            raise Exception("unexpected event.", e)
