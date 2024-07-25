import os
from typing import Dict
from boto3 import client
import json

bedrock_agent_runtime_client = client("bedrock-agent-runtime", region_name=os.environ["AWS_REGION"])

def lambda_handler(event, context):
    question = json.loads(event["body"])["question"]

    input_data = {
        "input": {
            "text": question
        },
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": os.environ["KNOWLEDGE_BASE_ID"],
                "modelArn": f"arn:aws:bedrock:{os.environ['AWS_REGION']}::foundation-model/anthropic.claude-v2"
            }
        }
    }

    command = bedrock_agent_runtime_client.RetrieveAndGenerateCommand(input_data)
    response = bedrock_agent_runtime_client.send(command)

    return {
        "response": response.output.text
    }

