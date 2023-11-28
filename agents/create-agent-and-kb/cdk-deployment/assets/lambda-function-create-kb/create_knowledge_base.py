from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import botocore
import time
import json
import os

opensearch_serverless_client = boto3.client('opensearchserverless')
agent_client = boto3.client("bedrock-agent")
lambda_client = boto3.client('lambda')
iam = boto3.client('iam')
s3 = boto3.client('s3')


def get_agent_id_and_s3_bucket_name_from_payload(props):
    
    print(f'Properties: {props}')
    agent_id = ''
    s3_bucket_name = ''
    
    for prop in props:
        print(prop)
        if prop['name'] == 'agentId':
            agent_id = prop['value']
        elif prop['name'] == 's3KnowledgeBaseBucketName':
            s3_bucket_name = prop['value']
            
    return s3_bucket_name, agent_id


def create_encryption_policy(agent_id):
    """Creates an encryption policy that matches all collections beginning with collection-""" + agent_id + """"""
    try:
        response = opensearch_serverless_client.create_security_policy(
            description=f'Encryption policy created by an agent with id {agent_id}.',
            name=f'agent-{agent_id}-policy',
            policy="""
                {
                    \"Rules\":[
                        {
                            \"ResourceType\":\"collection\",
                            \"Resource\":[
                                \"collection\/collection-""" + agent_id + """*\"
                            ]
                        }
                    ],
                    \"AWSOwnedKey\":true
                }
                """,
            type='encryption'
        )
        print('\nEncryption policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] The policy name or rules conflict with an existing policy.')
        else:
            raise error


def create_network_policy(agent_id):
    """Creates a network policy that matches all collections beginning with collection-""" + agent_id + """"""
    try:
        response = opensearch_serverless_client.create_security_policy(
            description=f'Network policy created by an agent with id {agent_id}.',
            name=f'agent-{agent_id}-policy',
            policy="""
                [{
                    \"Description\":\"Public access for the collection created by an agent with id """ + agent_id +""".\",
                    \"Rules\":[
                        {
                            \"ResourceType\":\"dashboard\",
                            \"Resource\":[\"collection\/collection-""" + agent_id + """*\"]
                        },
                        {
                            \"ResourceType\":\"collection\",
                            \"Resource\":[\"collection\/collection-""" + agent_id + """*\"]
                        }
                    ],
                    \"AllowFromPublic\":true
                }]
                """,
            type='network'
        )
        print('\nNetwork policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] A network policy with this name already exists.')
        else:
            raise error


def create_access_policy(account_id,
                         agent_id,
                         lambda_role_arn, 
                         knowledge_base_role_arn,
                         account_iam_role):
    """Creates a data access policy that matches all collections beginning with agent-""" + agent_id + """"""
    try:
        response = opensearch_serverless_client.create_access_policy(
            description=f'Data access policy for collections created by an agent with id {agent_id}.',
            name=f'agent-{agent_id}-policy',
            policy="""
                [{
                    \"Rules\":[
                        {
                            \"Resource\":[
                                \"index\/collection-""" + agent_id + """*\/*\"
                            ],
                            \"Permission\":[
                                \"aoss:CreateIndex\",
                                \"aoss:DeleteIndex\",
                                \"aoss:UpdateIndex\",
                                \"aoss:DescribeIndex\",
                                \"aoss:ReadDocument\",
                                \"aoss:WriteDocument\"
                            ],
                            \"ResourceType\": \"index\"
                        },
                        {
                            \"Resource\":[
                                \"collection\/collection-""" + agent_id + """*\"
                            ],
                            \"Permission\":[
                                \"aoss:CreateCollectionItems\",
                                \"aoss:DescribeCollectionItems\",
                                \"aoss:DeleteCollectionItems\",
                                \"aoss:UpdateCollectionItems\"
                            ],
                            \"ResourceType\": \"collection\"
                        }
                    ],
                    \"Principal\": [
                        \"""" + knowledge_base_role_arn + """\", 
                        \"""" + lambda_role_arn + """\",
                        \"""" + account_iam_role + """\"
                    ]
                }]
                """,
            type='data'
        )
        print('\nAccess policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] An access policy with this name already exists.')
        else:
            raise error


def create_collection(agent_id):
    """Creates a collection"""
    try:
        response = opensearch_serverless_client.create_collection(
            name=f'collection-{agent_id}',
            description=f'Collection created by an agent with id {agent_id}.',
            type='VECTORSEARCH'
        )
        return(response['createCollectionDetail']['arn'])
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] A collection with this name already exists. Try another name.')
        else:
            raise error


def wait_for_collection_creation(awsauth,
                                 agent_id,
                                 vector_index_name, 
                                 text_field, 
                                 bedrock_metadata_field,
                                 vector_field_name):
    """Waits for the collection to become active"""
    response = opensearch_serverless_client.batch_get_collection(
        names=[f'collection-{agent_id}'])
    # Periodically check collection status
    while (response['collectionDetails'][0]['status']) == 'CREATING':
        print('Creating collection...')
        time.sleep(30)
        response = opensearch_serverless_client.batch_get_collection(
            names=[f'collection-{agent_id}'])
    print('\nCollection successfully created:')
    print(response["collectionDetails"])
    # Extract the collection endpoint from the response
    host = (response['collectionDetails'][0]['collectionEndpoint'])
    final_host = host.replace("https://", "")
    index_data(host=final_host, 
               awsauth=awsauth, 
               vector_index_name=vector_index_name,
               bedrock_metadata_field=bedrock_metadata_field,
               text_field=text_field,
               vector_field_name=vector_field_name)


def index_data(host, awsauth, vector_index_name, text_field, 
               bedrock_metadata_field, vector_field_name):
    """Create an index"""
    # Build the OpenSearch client
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )
    # It can take up to a minute for data access rules to be enforced
    time.sleep(45)
    
    # Create index
    body = {
      "mappings": {
        "properties": {
          f"{bedrock_metadata_field}": {
            "type": "text",
            "index": False
          },
          "id": {
            "type": "text",
            "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
              }
            }
          },
          f"{text_field}": {
            "type": "text",
            "index": False
          },
          f"{vector_field_name}": {
            "type": "knn_vector",
            "dimension": 1536,
            "method": {
              "engine": "nmslib",
              "space_type": "cosinesimil",
              "name": "hnsw"
            }
          }
        }
      },
      "settings": {
        "index": {
          "number_of_shards": 2,
          "knn.algo_param": {
            "ef_search": 512
          },
          "knn": True,
        }
      }
    }

    response = client.indices.create(index=vector_index_name, body=body)
    print('\nCreating index:')
    print(response)
    

def create_allow_bedrock_iam_policy(policy_name, agent_id):
    
    bedrock_allow_models_policy = """{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock:InvokeModel",
          "bedrock:ListCustomModels",
          "bedrock:ListFoundationModels"
        ],
        "Resource": "*"
      }
    ]
    }"""
    
    policy = iam.create_policy(
            PolicyName=policy_name,
            Description=f"Policy for Bedrock Invoke Model, List Models and ListFoundationModels create by an agent with id {agent_id}.",
            PolicyDocument=bedrock_allow_models_policy,
        )
        
    return policy['Policy']['Arn']
    
    
def create_allow_collection_access(policy_name, collection_arn, agent_id):
    
    collection_allow_access_policy = """{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "aoss:APIAccessAll"
         ],
         "Resource": [
           \"""" + collection_arn + """\"
         ]
      }
    ]
    }"""
    
    policy = iam.create_policy(
            PolicyName=policy_name,
            Description=f"Policy for access to the Opensearch by the Knowledge Base created by an agent with id {agent_id}.",
            PolicyDocument=collection_allow_access_policy,
        )
        
    return policy['Policy']['Arn']

    
def create_knowledge_base_iam_role(role_name, account_id, region):
  
    basic_role = """{
    "Version": "2012-10-17",
    "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": \"""" + account_id + """\"
        },
        "ArnLike": {
          "AWS:SourceArn": \"arn:aws:bedrock:""" + region + """:""" + account_id + """:knowledge-base/*\"
        }
      }
    }
    ]
    }"""
  
    iam.create_role(RoleName=role_name, 
      AssumeRolePolicyDocument=basic_role)

    # This role has the AmazonOpenSearchServiceReadOnlyAccess managed policy.
    iam.attach_role_policy(RoleName=role_name, 
      PolicyArn='arn:aws:iam::aws:policy/AmazonOpenSearchServiceReadOnlyAccess')
    # This role has the AmazonS3ReadOnlyAccess managed policy.
    iam.attach_role_policy(RoleName=role_name,
      PolicyArn='arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess')
      
    return iam.get_role(RoleName=role_name)['Role']['Arn']
    
    
def attach_bedrock_and_collection_policies(role_name,
                                           bedrock_policy_arn,
                                           collection_policy_arn):
    
    iam.attach_role_policy(RoleName=role_name,
      PolicyArn=bedrock_policy_arn)
    iam.attach_role_policy(RoleName=role_name,
      PolicyArn=collection_policy_arn)
      
    return
    
    
def create_knowledge_base(collection_arn, 
                          vector_field_name,
                          vector_index_name,
                          knowledge_base_role_arn,
                          text_field,
                          bedrock_metadata_field,
                          agent_id):
    
    knowledge_base_config = {
      "type": "VECTOR",
      "vectorKnowledgeBaseConfiguration": {
        "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
      }
    }

    storage_config = {
      "opensearchServerlessConfiguration": {
        "collectionArn": collection_arn, 
        "fieldMapping": {
          "metadataField": bedrock_metadata_field,
          "textField": text_field,  
          "vectorField": vector_field_name
        },
        "vectorIndexName": vector_index_name
      },
      "type": "OPENSEARCH_SERVERLESS" 
    }

    response = agent_client.create_knowledge_base(
        name=f'Agent-{agent_id}-KnowledgeBase-Opensearch',
        description=f'Knowledge base created by an agent with id {agent_id}.',
        roleArn=knowledge_base_role_arn,
        knowledgeBaseConfiguration=knowledge_base_config,
        storageConfiguration=storage_config)
        
    return(response['knowledgeBase']['knowledgeBaseId'])


def create_data_source(knowledge_base_id, s3_bucket_name, agent_id):
    
    # Set up bucket arn from user's 's3_bucket_name'
    s3_bucket_arn = f'arn:aws:s3:::{s3_bucket_name}'
    
    data_source_configuration = {
      "s3Configuration": {
        "bucketArn": s3_bucket_arn
      },
        "type": "S3"
    }
    
    response = agent_client.create_data_source(
        knowledgeBaseId=knowledge_base_id,
        name=f'Agent-{agent_id}-DataSource',
        dataSourceConfiguration=data_source_configuration)
        
    return response
    
    
def associate_knowledge_base(agent_id, knowledge_base_id):
    
    agent_kb_description = agent_client.associate_agent_knowledge_base(
    agentId=agent_id,
    agentVersion='DRAFT',
    description='Modify this instruction as needed.',
    knowledgeBaseId=knowledge_base_id
)
    
    return agent_kb_description

def lambda_handler(event, context):
    
    print("Event payload: " + json.dumps(event))
  
    response_code = 200
    props = event['detail']['requestBody']['content']['application/json']['properties']
    
    # Get current role to attach to Opensearch allow list
    role_response = (lambda_client.get_function_configuration(
      FunctionName = os.environ['AWS_LAMBDA_FUNCTION_NAME'])
    )
    lambda_role_arn = role_response['Role']
    
    # Get account id and current region
    account_id = context.invoked_function_arn.split(":")[4]
    region = os.environ['AWS_REGION']
    
    # Set up auth for Opensearch client
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                   region, service, session_token=credentials.token)
    
    # Change this IAM role for the one you want to give access to opensearch collection.
    # Admin by default.
    account_iam_role = f"arn:aws:iam::{account_id}:role/Admin"
    
    s3_bucket_name, agent_id = get_agent_id_and_s3_bucket_name_from_payload(props)
    agent_id_lowercase = agent_id.lower() # To satisfy collection policy name constraints
    bedrock_policy_name = f"bedrock-policy-name-created-by-agent-{agent_id}"
    collection_policy_name = f"collection-policy-name-created-by-agent-{agent_id}"
    knowledge_base_role_name = f"AmazonBedrockExecutionRoleForKnowledgeBase_{agent_id}"
    vector_field_name = f"embeddings-{agent_id_lowercase}"
    vector_index_name = f"vector-{agent_id_lowercase}"
    text_field = "text-field"
    bedrock_metadata_field = "bedrock-managed-metadata-field"
    
                   
    ##### Start of function calls
    knowledge_base_role_arn = create_knowledge_base_iam_role(role_name=knowledge_base_role_name,
                                                             account_id=account_id,
                                                             region=region)
    
    # Pause to make sure iam role is created                           
    time.sleep(10)
    
    create_encryption_policy(agent_id=agent_id_lowercase)
    create_network_policy(agent_id=agent_id_lowercase)
    # Attached is 'max-role' or 'Admin', make sure change it later
    create_access_policy(account_id=account_id,
                         agent_id=agent_id_lowercase,
                         lambda_role_arn=lambda_role_arn, 
                         knowledge_base_role_arn=knowledge_base_role_arn,
                         account_iam_role=account_iam_role)
    collection_arn = create_collection(agent_id=agent_id_lowercase)
    wait_for_collection_creation(awsauth=awsauth, 
                                 agent_id=agent_id_lowercase,
                                 vector_index_name=vector_index_name,
                                 text_field=text_field,
                                 bedrock_metadata_field=bedrock_metadata_field,
                                 vector_field_name=vector_field_name)
    
    bedrock_policy_arn = create_allow_bedrock_iam_policy(policy_name=bedrock_policy_name,
                                                         agent_id=agent_id)
    collection_policy_arn = create_allow_collection_access(policy_name=collection_policy_name, 
                                                           collection_arn=collection_arn,
                                                           agent_id=agent_id)
                                                           
    # Pause to make sure iam policies are created                           
    time.sleep(10)                                                       
                                                             
    attach_bedrock_and_collection_policies(role_name=knowledge_base_role_name,
                                           collection_policy_arn=collection_policy_arn,
                                           bedrock_policy_arn=bedrock_policy_arn)
                                           
    # Pause to make sure iam policies are attached                           
    time.sleep(10) 
                                           
    knowledge_base_id = create_knowledge_base(collection_arn=collection_arn, 
                                              vector_field_name=vector_field_name,
                                              vector_index_name=vector_index_name,
                                              knowledge_base_role_arn=knowledge_base_role_arn,
                                              text_field=text_field,
                                              bedrock_metadata_field=bedrock_metadata_field,
                                              agent_id=agent_id)
    create_data_source(knowledge_base_id=knowledge_base_id,
                       s3_bucket_name=s3_bucket_name,
                       agent_id=agent_id)
    associate_knowledge_base(agent_id=agent_id, knowledge_base_id=knowledge_base_id)
   
    ##### End of function calls
    
    response_body = {
      'application/json': {
        'body': f"""I successfully created and assocaited a knowledge base. Created knowledge base id is {knowledge_base_id}. Just to confirm, I used {s3_bucket_name} as a data source.
To create and associate a knowledge base I needed to create an Opensearch serverless collection with the following ARN - {collection_policy_arn}.
I also create {knowledge_base_role_name} role, {bedrock_policy_name} and {collection_policy_name} policies.
Please make sure you check all of the IAM roles and attach appropriate policies based on your needs.
Make sure you double check if everything was provisioned as expected."""
      }
    }
  
    print("Response: " + json.dumps(response_body))
  
    return response_body 
    
    
