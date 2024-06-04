import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import os
vector_db_idx = os.environ.get('VECTOR_DB_INDEX')
aoss_collection_id = os.environ.get('AOSS_COLLECTION_ID')
region = os.environ.get('REGION')
knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')

def get_named_parameter(event, name):
    return next(item for item in event['parameters'] if item['name'] == name)['value']

def lambda_handler(event, context):
    function_name = event['function']
    
    host = f'{aoss_collection_id}.{region}.aoss.amazonaws.com'
    service = 'aoss'
    index = vector_db_idx
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, service)
    print('host',host)
    ospy_client = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection,
        pool_maxsize = 20
    )
    
    results = []
    # query opensearch directly
    if function_name == 'retrieve-reviews-opensearch':
        count = get_named_parameter(event, "count")
        start_date = get_named_parameter(event, "start_date")
        end_date = get_named_parameter(event, "end_date")
        query = {
            "from": 0,
            "size": int(count),
            "sort" : [
                { "rating" : {"order" : "desc"}
                }
            ],
            "fields": [
                "bedrock-knowledge-base-text",
                "rating",
                "timestamp"
            ],
            "query": {
                "range":{
                    "timestamp": {
                    "gte":float(start_date),
                    "lte":float(end_date)
                    }
                }
            },
            "_source": False
        }

        response = ospy_client.search(
            body = query,
            index = index
        )
        
        for hit in response['hits']['hits']:
            fields = hit['fields']
            res = {'review':fields['bedrock-knowledge-base-text'][0],'rating':fields['rating'][0],'timestamp':fields['timestamp']}
            results.append(res)
    # query knowledge base directly - hybrid (filter + semantic)
    elif function_name == 'retrieve-reviews-hybrid':
        count = get_named_parameter(event, "count")
        start_date = get_named_parameter(event, "start_date")
        end_date = get_named_parameter(event, "end_date")
        description = get_named_parameter(event, "description")
        reviewer = get_named_parameter(event, "reviewer")
        bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
        response = bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': description
            },
            retrieveAndGenerateConfiguration={
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': f'arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'filter': {
                                'andAll':[
                                    {
                                        'greaterThan': {
                                            'key': 'timestamp',
                                            'value': float(start_date)
                                        }
                                    },
                                    {
                                        'lessThan': {
                                            'key': 'timestamp',
                                            'value': float(end_date)
                                        }
                                    },
                                    {
                                        'in': {
                                            'key': 'reviewers',
                                            'value': [reviewer]
                                        }
                                    }
                                ],
                            },
                            'numberOfResults': int(count),
                            'overrideSearchType': 'HYBRID'
                        }
                    }
                },
                'type': 'KNOWLEDGE_BASE'
            }
        )
        
        generated_text = response['output']['text']
        citations = response["citations"]
        reviews = []
        for citation in citations:
            retrievedReferences = citation["retrievedReferences"]
            for reference in retrievedReferences:
                reviews.append({'review':reference['content']['text'],'rating':reference['metadata']['rating'],'timestamp':reference['metadata']['timestamp']})
        results = {'generated_text':generated_text,'reviews':reviews}
    response_body = {
        'TEXT':{
            'body': json.dumps(results)
        }
    }
    action_response = {
        'actionGroup': event['actionGroup'],
        'function': function_name,
        'functionResponse':{
            'responseBody': response_body
        }
    }
    return {
        'messageVersion': '1.0',
        "response": action_response
    }

if __name__ == '__main__':
    event = {'actionGroup':'action-group','function':'retrieve-reviews-opensearch',
            'parameters':[
                {'name':'count','value':2},
                {'name':'start_date','value':1577808000000},
                {'name':'end_date','value':1609430400000}]}
    # event = {'actionGroup':'action-group','function':'retrieve-reviews-hybrid',
    #         'parameters':[
    #             {'name':'count','value':2},
    #             {'name':'start_date','value':'1577808000000'},
    #             {'name':'end_date','value':'1609430400000'},
    #             {'name':'reviewer','value':'curry'},
    #             {'name':'description','value':'hair spray'}]}
    lambda_handler(event,None)