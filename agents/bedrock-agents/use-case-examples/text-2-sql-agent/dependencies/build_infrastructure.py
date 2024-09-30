from config import *


# ### Create S3 bucket and upload API Schema
# 
# Agents require an API Schema stored on s3. Let's create an S3 bucket to store the file and upload the file to the newly created bucket



# Create S3 bucket for Open API schema
s3bucket = s3_client.create_bucket(
    Bucket=bucket_name
)




# Upload Open API schema to this s3 bucket
s3_client.upload_file("./dependencies/"+schema_name, bucket_name, bucket_key)




sts_response = sts.get_caller_identity().get('Account')
print("AccountID: ", sts_response)


glue.create_database(
    CatalogId=sts_response,
    DatabaseInput={
        'Name':glue_database_name,
    }
)





sts_response = sts.get_caller_identity().get('Arn')
print(sts_response)

try:
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Principal": {
                        "Service": "glue.amazonaws.com"
                    }
                }
            ]
        }

        assume_role_policy_document_json = json.dumps(assume_role_policy_document)

        print(glue_role_name) 

        glue_iam_role = iam_client.create_role(
            RoleName=glue_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

        # Pause to make sure role is created
        time.sleep(10)
except:
    glue_iam_role = iam_client.get_role(RoleName=glue_role_name)

policy_arns = [
    'arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess',
    'arn:aws:iam::aws:policy/AmazonS3FullAccess',
]

for policy_arn in policy_arns:
    iam_client.attach_role_policy(
        RoleName=glue_role_name,
        PolicyArn=policy_arn
    )
  

    #crawler = glue.get_crawler(
# )
# pprint.pprint(crawler)
print(s3_target)
glue.create_crawler(
        Name=glue_crawler_name,
        Role=glue_role_name,
        DatabaseName='thehistoryofbaseball',
        Targets={'CatalogTargets': [],
                 'DeltaTargets': [],
                 'DynamoDBTargets': [],
                 'HudiTargets': [],
                 'IcebergTargets': [],
                 'JdbcTargets': [],
                 'MongoDBTargets': [],
                 'S3Targets': [{'Exclusions': [],
                                'Path': s3_target }]},
        Classifiers= [],
        Configuration= '{"Version":1.0,"CreatePartitionIndex":true}',
        LakeFormationConfiguration= {'AccountId': '',
                                    'UseLakeFormationCredentials': False},
        RecrawlPolicy= {'RecrawlBehavior': 'CRAWL_EVERYTHING'},
        LineageConfiguration= {'CrawlerLineageSettings': 'DISABLE'},  
    )





def unzip_data(zip_data, ext_data):
    print("unzip_data()... finished")
    
    ## The below works to extract all data in subfolders also
    
    with zipfile.ZipFile(zip_data, 'r') as zip_ref:
        zip_ref.extractall(ext_data)
    

def upload_data(s3_bucket,s3_prefix,ext_data):
    
    s3_path = "s3://" + s3_bucket + "/" +s3_prefix
    print("upload_data() ... finished")
    cmd = f"aws s3 sync {ext_data} {s3_path}"
    print(cmd)
    os.system(cmd)
unzip_data(zip_data, ext_data)
upload_data(s3_bucket,s3_prefix,ext_data)





crawler = glue.get_crawler(
        Name=glue_crawler_name
    )
if crawler['Crawler']['State'] == 'READY':
    print('Crawling data source...')
    glue.start_crawler(
       Name=glue_crawler_name
    )
    time.sleep(120)
    print("Crawl should be complete.")
else:
    time.sleep(10)

pprint.pprint(crawler)




# ### Create Lambda function for Action Group
# Let's now create the lambda function required by the agent action group. We first need to create the lambda IAM role and it's policy. After that, we package the lambda function into a ZIP format to create the function




# Create IAM Role for the Lambda function

try:
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "bedrock:InvokeModel",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)

    lambda_iam_role = iam_client.create_role(
        RoleName=lambda_role_name,
        AssumeRolePolicyDocument=assume_role_policy_document_json
    )

    # Pause to make sure role is created
    time.sleep(10)
except:
    lambda_iam_role = iam_client.get_role(RoleName=lambda_role_name)

    
policy_arns = [
    'arn:aws:iam::aws:policy/AmazonAthenaFullAccess',
    'arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess',
    'arn:aws:iam::aws:policy/AmazonS3FullAccess',
    'arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole',
    'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
]  
for policy_arn in policy_arns:
    iam_client.attach_role_policy(
        RoleName=lambda_role_name,
        PolicyArn=policy_arn
    )







# Package up the lambda function code
s = BytesIO()
z = zipfile.ZipFile(s, 'w')
z.write(lambda_code_path)
z.close()
zip_content = s.getvalue()


# Create Lambda Function
lambda_function = lambda_client.create_function(
    FunctionName=lambda_name,
    Runtime='python3.12',
    Timeout=180,
    Role=lambda_iam_role['Role']['Arn'],
    Code={'ZipFile': zip_content},
    Handler='lambda_function.lambda_handler',
    Environment = {'Variables':{'outputLocation':athena_result_loc}}
    
)


# ### Create Agent
# We will now create our agent. To do so, we first need to create the agent policies that allow bedrock model invocation  and s3 bucket access. 




# Create IAM policies for agent
bedrock_agent_bedrock_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                f"arn:aws:bedrock:{region}::foundation-model/{foundation_Model}"
            ]
        }
    ]
}

bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)
bedrock_agent_bedrock_allow_policy_name
agent_bedrock_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_bedrock_allow_policy_name,
    PolicyDocument=bedrock_policy_json
)






bedrock_agent_s3_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAgentAccessOpenAPISchema",
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": [
                schema_arn
            ]
        }
    ]
}


bedrock_agent_s3_json = json.dumps(bedrock_agent_s3_allow_policy_statement)
agent_s3_schema_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_s3_allow_policy_name,
    Description=f"Policy to allow invoke Lambda that was provisioned for it.",
    PolicyDocument=bedrock_agent_s3_json
)





# Create IAM Role for the agent and attach IAM policies
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": "bedrock.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
    }]
}

assume_role_policy_document_json = json.dumps(assume_role_policy_document)
agent_role = iam_client.create_role(
    RoleName=agent_role_name,
    AssumeRolePolicyDocument=assume_role_policy_document_json
)

# Pause to make sure role is created
time.sleep(10)
    
iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_bedrock_policy['Policy']['Arn']
)

iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_s3_schema_policy['Policy']['Arn']
)


# #### Creating Agent
# Once the needed IAM role is created, we can use the bedrock agent client to create a new agent. To do so we use the `create_agent` function. It requires an agent name, underline foundation model and instruction. You can also provide an agent description. Note that the agent created is not yet prepared. We will focus on preparing the agent and then using it to invoke actions and use other APIs




# Create Agent
agent_instruction = """You are an expert database querying assistant that can create simple and complex SQL queries to get 
the answers to questions about baseball players that you are asked. You first need to get the schemas for the table in the database to then query the 
database tables using a sql statement then respond to the user with the answer to their question and
the sql statement used to answer the question. Use the getschema tool first to understand the schema
of the table then create a sql query to answer the users question.
Here is an example to query the table <example>SELECT * FROM thehistoryofbaseball.players LIMIT 10;</example> Do not use 
quotes for the table name. Your final answer should be in plain english."""


##PLEASE Note
###Disabling pre-processing can enhance the agent's response time, however, it may increase the risk of inaccuracies in SQL query generation or some sql ingestion. Careful consideration is advised when toggling this feature based on your use case requirements.


response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_role['Role']['Arn'],
    description="Agent for performing sql queries.",
    idleSessionTTLInSeconds=idleSessionTTLInSeconds,
    foundationModel=foundation_Model,
    instruction=agent_instruction,
    promptOverrideConfiguration={
    #Disable preprocessing prompt
        'promptConfigurations': [
            {
                'promptType': 'PRE_PROCESSING',
                'promptCreationMode': 'OVERRIDDEN',
                'promptState': 'DISABLED',
                'basePromptTemplate':' ',
                 'inferenceConfiguration': {
                    'temperature': 0,
                    'topP': 1,
                    'topK': 123,
                    'maximumLength': 2048,
                    'stopSequences': [
                        'Human',
                    ]
                },
                
            }
        ]
    }
)
    


# Looking at the created agent, we can see its status and agent id






# Let's now store the agent id in a local variable to use it on the next steps




agent_id = response['agent']['agentId']
agent_id


# ### Create Agent Action Group
# We will now create and agent action group that uses the lambda function and API schema files created before.
# The `create_agent_action_group` function provides this functionality. We will use `DRAFT` as the agent version since we haven't yet create an agent version or alias. To inform the agent about the action group functionalities, we will provide an action group description containing the functionalities of the action group.




# Pause to make sure agent is created
time.sleep(30)
# Now, we can configure and create an action group here:
agent_action_group_response = bedrock_agent_client.create_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupExecutor={
        'lambda': lambda_function['FunctionArn']
    },
    actionGroupName='QueryAthenaActionGroup',
    apiSchema={
        's3': {
            's3BucketName': bucket_name,
            's3ObjectKey': bucket_key
        }
    },
    description='Actions for getting the database schema and querying the Athena database'
)





agent_action_group_response


# ### Allowing Agent to invoke Action Group Lambda
# Before using our action group, we need to allow our agent to invoke the lambda function associated to the action group. This is done via resource-based policy. Let's add the resource-based policy to the lambda function created




# Create allow invoke permission on lambda
response = lambda_client.add_permission(
    FunctionName=lambda_name,
    StatementId='allow_bedrock',
    Action='lambda:InvokeFunction',
    Principal='bedrock.amazonaws.com',
    SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}",
)


# ### Preparing Agent
# Let's create a DRAFT version of the agent that can be used for internal testing.




agent_prepare = bedrock_agent_client.prepare_agent(agentId=agent_id)
agent_prepare


# ### Create Agent alias
# We will now create an alias of the agent that can be used to deploy the agent.




# Pause to make sure agent is prepared
time.sleep(30)
agent_alias = bedrock_agent_client.create_agent_alias(
    agentId=agent_id,
    agentAliasName=agent_alias_name
)




# Pause to make sure agent alias is ready
time.sleep(30)

agent_alias

print(agent_alias)
