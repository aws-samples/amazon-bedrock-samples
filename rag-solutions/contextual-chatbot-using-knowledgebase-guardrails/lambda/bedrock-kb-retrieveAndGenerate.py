import os
import boto3
import random
import string

boto3_session = boto3.session.Session()
region = boto3_session.region_name

# create a boto3 bedrock client
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

# get knowledge base id from environment variable
kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
guardrailId = os.environ.get("GUARDRAIL_ID")
guardrailVersion = os.environ.get("GUARDRAIL_VERSION")


# declare model id for calling RetrieveAndGenerate API
model_id = "anthropic.claude-instant-v1"
model_arn = f'arn:aws:bedrock:{region}::foundation-model/{model_id}'

def retrieveAndGenerate(input,enableGuardRails, kbId, model_arn, sessionId):
    #print(input, kbId, model_arn, sessionId)
    if sessionId != "":
        if enableGuardRails :
            return bedrock_agent_runtime_client.retrieve_and_generate(
                input={
                    'text': input
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'generationConfiguration': {
                            'guardrailConfiguration': { 
                                'guardrailId': guardrailId,
                                'guardrailVersion': guardrailVersion
                            }
                        },
                        'knowledgeBaseId': kbId,
                        'modelArn': model_arn
                    }
                },
                sessionId=sessionId
            )
        else:
          return bedrock_agent_runtime_client.retrieve_and_generate(
                input={
                    'text': input
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kbId,
                        'modelArn': model_arn
                    }
                },
                sessionId=sessionId
            ) 
    else:
        if enableGuardRails :
            return bedrock_agent_runtime_client.retrieve_and_generate(
                input={
                    'text': input
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'generationConfiguration': {
                            'guardrailConfiguration': { 
                                'guardrailId': guardrailId,
                                'guardrailVersion': guardrailVersion
                            }
                        },
                        'knowledgeBaseId': kbId,
                        'modelArn': model_arn
                    }
                }
            )
        else:
          return bedrock_agent_runtime_client.retrieve_and_generate(
                input={
                    'text': input
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kbId,
                        'modelArn': model_arn
                    }
                }
            )

def lambda_handler(event, context):
    query = event["question"]
    enableGuardRails = event["enableGuardRails"]
    sessionId = event["sessionId"]
    response = retrieveAndGenerate(query,enableGuardRails, kb_id, model_arn, sessionId)
    generated_text = response['output']['text']
    sessionId = response['sessionId']
    print (generated_text)
    print (sessionId)
    
    return {
        'statusCode': 200,
        'body': {"question": query.strip(), "answer": generated_text.strip(), "sessionId":sessionId}
    }
  
