import os
import re
import json
import time
import boto3
import base64

from requests import request
from sigv4 import SigV4HttpRequester

def bedrock_agent(intent_request):
    query = intent_request["inputTranscript"].title()
    print("bedrock_agent query: " + query)
    
    if not query:
        message = {
            'contentType': 'PlainText',
            'content': 'utterance is empty, try again please'
        }
       
        intent_request['sessionState']['intent']['state'] = "Fulfilled"
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'ElicitIntent'
                },
                'intent': intent_request['sessionState']['intent']
            },
            'messages': [message],
            'sessionId': intent_request['sessionId'],
            'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
        }

    # Define Bedrock parameters
    agentId = "OXI4KB2UUM"
    agentAliasId = "D4VLKHAEJ5"
    sessionId = intent_request["sessionId"]
    knowledgeBaseId = "QOQG1W8FUH"
    dataSourceId = "K3W6CCI9Q0"

    # agents = bedrock-agent-runtime.us-east-1.amazonaws.com
    # knowledgebases = bedrock-agent.us-east-1.amazonaws.com
    url = f'https://bedrock-agent-runtime.us-east-1.amazonaws.com/agents/{agentId}/agentAliases/{agentAliasId}/sessions/{sessionId}/text'

    myobj = {
        "inputText": query,   
        "enableTrace": True,
    }

    # send request
    print("Calling sigv4_request")
    requester = SigV4HttpRequester()
    response = requester.send_signed_request(
        url=url,
        method='POST',
        service='bedrock',
        headers={
            'content-type': 'application/json', 
            'accept': 'application/json',
        },
        region='us-east-1',
        body=json.dumps(myobj)
    )

    print("sig4_request response = " + response.text)
    
    # do something with response
    string = ""
    for line in response.iter_content():
        try:
            string += line.decode(encoding='utf-8')
        except:
            continue
    print("Decoded response", string)

    split_response = string.split(":message-type")
    last_response = split_response[-1]
    if "bytes" in last_response:
        encoded_last_response = last_response.split("\"")[3]
        decoded = base64.b64decode(encoded_last_response)
        final_response = decoded.decode('utf-8')
    else:
        part1 = string[string.find('finalResponse')+len('finalResponse":'):] 
        part2 = part1[:part1.find('"}')+2]
        final_response = json.loads(part2)['text']

    final_response = final_response.replace("\"", "")
    final_response = final_response.replace("{input:{value:", "")
    final_response = final_response.replace(",source:null}}", "")
    llm_response = final_response
    print("llm_response:: " + llm_response)

    message = {
        'contentType': 'PlainText',
        'content': llm_response
    }
   
    intent_request['sessionState']['intent']['state'] = "Fulfilled"
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitIntent'
            },
            'intent': intent_request['sessionState']['intent']
        },
        'messages': [message],
        'sessionId': intent_request['sessionId'],
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }

def dispatch(intent_request):
    #Routes the incoming request based on intent.
    slots = intent_request['sessionState']['intent']['slots']
    username = slots['UserName'] if 'UserName' in slots else None
    intent_name = intent_request['sessionState']['intent']['name']

    if intent_name == 'WelcomeIntent':
        return
    else:
        return bedrock_agent(intent_request)

# --- Main handler ---

def lambda_handler(event, context):
    """
    Invoked when the user provides an utterance that maps to a Lex bot intent.
    The JSON body of the user request is provided in the event slot.
    """
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    return dispatch(event)
