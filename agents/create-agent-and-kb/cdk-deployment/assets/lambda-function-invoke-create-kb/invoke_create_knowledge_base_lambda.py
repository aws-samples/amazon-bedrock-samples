from datetime import datetime
import boto3
import json

event_client = boto3.client('events')

def lambda_handler(event, context):
    
    print("Event payload: " + json.dumps(event))
  
    response_code = 200

    event_client.put_events(
        Entries=[
            {
                'Time': datetime.now(),
                'Source': 'create-kb.event',
                'DetailType': 'event',
                'Detail': json.dumps(event),
                'EventBusName': 'BedrockKbEventBus'
            }
        ])
    
    response_body = {
      'application/json': {
        'body': f"""I sent your create knowledge base request to another Lambda function through AWS EventBridge. 
        This process will take somewhere from 10 to 15 minutes. You can check your Knowledge Base section after that. Have a good day!"""
      }
    }
    
    action_response = {
     'actionGroup': event['actionGroup'],
     'apiPath': event['apiPath'],
     'httpMethod': event['httpMethod'],
     'httpStatusCode': response_code,
     'responseBody': response_body
    }

    api_response = {
     'messageVersion': '1.0',
     'response': action_response
    }
  
    print("API response payload: " + json.dumps(api_response))
  
    return api_response 
    
    