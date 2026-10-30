from config import *
from security_config import (
    build_athena_workgroup_configuration,
    build_glue_data_policy,
    build_lambda_query_policy,
)


# ### Create S3 bucket and upload API Schema
# 
# Agents require an API Schema stored on s3. Let's create an S3 bucket to store the file and upload the file to the newly created bucket



# Create S3 bucket for Open API schema
create_bucket_request = {"Bucket": bucket_name}
if region != "us-east-1":
    create_bucket_request["CreateBucketConfiguration"] = {
        "LocationConstraint": region
    }
s3bucket = s3_client.create_bucket(**create_bucket_request)
s3_client.put_public_access_block(
    Bucket=bucket_name,
    PublicAccessBlockConfiguration={
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    },
)
s3_client.put_bucket_encryption(
    Bucket=bucket_name,
    ServerSideEncryptionConfiguration={
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                },
                "BucketKeyEnabled": False,
            }
        ]
    },
)

athena.create_work_group(
    Name=athena_workgroup_name,
    Description="Enforced workgroup for the text-to-SQL sample",
    Configuration=build_athena_workgroup_configuration(
        account_id=account_id,
        output_location=athena_result_loc,
        bytes_scanned_cutoff=athena_bytes_scanned_cutoff,
    ),
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

glue_assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "glue.amazonaws.com"},
        }
    ],
}

try:
    glue_iam_role = iam_client.create_role(
        RoleName=glue_role_name,
        AssumeRolePolicyDocument=json.dumps(glue_assume_role_policy),
    )
    time.sleep(10)
except iam_client.exceptions.EntityAlreadyExistsException:
    glue_iam_role = iam_client.get_role(RoleName=glue_role_name)

glue_service_policy_arn = (
    "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
)
for attached_policy in iam_client.list_attached_role_policies(
    RoleName=glue_role_name
)["AttachedPolicies"]:
    if attached_policy["PolicyArn"] != glue_service_policy_arn:
        iam_client.detach_role_policy(
            RoleName=glue_role_name,
            PolicyArn=attached_policy["PolicyArn"],
        )
for inline_policy_name in iam_client.list_role_policies(
    RoleName=glue_role_name
)["PolicyNames"]:
    if inline_policy_name != glue_data_policy_name:
        iam_client.delete_role_policy(
            RoleName=glue_role_name,
            PolicyName=inline_policy_name,
        )

iam_client.attach_role_policy(
    RoleName=glue_role_name,
    PolicyArn=glue_service_policy_arn,
)
iam_client.put_role_policy(
    RoleName=glue_role_name,
    PolicyName=glue_data_policy_name,
    PolicyDocument=json.dumps(build_glue_data_policy(bucket_name)),
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
    

def upload_data(s3_bucket, s3_prefix, extracted_data):
    """Upload extracted sample files without invoking an external shell."""
    for root, _, file_names in os.walk(extracted_data):
        for file_name in file_names:
            local_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(local_path, extracted_data)
            object_key = f"{s3_prefix}/{relative_path}".replace(os.sep, "/")
            s3_client.upload_file(local_path, s3_bucket, object_key)

    print("upload_data() ... finished")


unzip_data(zip_data, ext_data)
upload_data(s3_bucket, s3_prefix, ext_data)





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

lambda_assume_role_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

try:
    lambda_iam_role = iam_client.create_role(
        RoleName=lambda_role_name,
        AssumeRolePolicyDocument=json.dumps(lambda_assume_role_policy),
    )
    time.sleep(10)
except iam_client.exceptions.EntityAlreadyExistsException:
    lambda_iam_role = iam_client.get_role(RoleName=lambda_role_name)

    
lambda_logging_policy_arn = (
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)
attached_lambda_policies = iam_client.list_attached_role_policies(
    RoleName=lambda_role_name
)["AttachedPolicies"]
for attached_policy in attached_lambda_policies:
    if attached_policy["PolicyArn"] != lambda_logging_policy_arn:
        iam_client.detach_role_policy(
            RoleName=lambda_role_name,
            PolicyArn=attached_policy["PolicyArn"],
        )
for inline_policy_name in iam_client.list_role_policies(
    RoleName=lambda_role_name
)["PolicyNames"]:
    if inline_policy_name != lambda_query_policy_name:
        iam_client.delete_role_policy(
            RoleName=lambda_role_name,
            PolicyName=inline_policy_name,
        )

iam_client.attach_role_policy(
    RoleName=lambda_role_name,
    PolicyArn=lambda_logging_policy_arn,
)
iam_client.put_role_policy(
    RoleName=lambda_role_name,
    PolicyName=lambda_query_policy_name,
    PolicyDocument=json.dumps(
        build_lambda_query_policy(
            region=region,
            account_id=account_id,
            bucket_name=bucket_name,
            database_name=glue_database_name,
            workgroup_name=athena_workgroup_name,
        )
    ),
)
time.sleep(10)







# Package the handler and its dependency-free query guard.
s = BytesIO()
with zipfile.ZipFile(s, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(lambda_code_path, arcname=os.path.basename(lambda_code_path))
    archive.write(query_guard_path, arcname=os.path.basename(query_guard_path))
zip_content = s.getvalue()


# Create Lambda Function
lambda_function = lambda_client.create_function(
    FunctionName=lambda_name,
    Runtime="python3.12",
    Timeout=180,
    Role=lambda_iam_role["Role"]["Arn"],
    Code={"ZipFile": zip_content},
    Handler="lambda_function.lambda_handler",
    Environment={
        "Variables": {
            "ATHENA_WORKGROUP": athena_workgroup_name,
            "DATABASE_NAME": glue_database_name,
            "QUERY_TIMEOUT_SECONDS": str(query_timeout_seconds),
            "MAX_RESULT_ROWS": str(max_result_rows),
        }
    },
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
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": account_id},
                "ArnLike": {
                    "aws:SourceArn": (
                        f"arn:aws:bedrock:{region}:{account_id}:agent/*"
                    )
                },
            },
        }
    ],
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
agent_instruction = """You are an expert database querying assistant that answers questions about baseball players. First use the getschema tool to understand the available tables and columns. Then call querydatabase with exactly one read-only SELECT statement against those tables. Do not generate DDL, DML mutations, UNLOAD, comments, common table expressions, quoted identifiers, or multiple statements. Always include a reasonable LIMIT for row-returning queries. Here is an example: <example>SELECT * FROM thehistoryofbaseball.players LIMIT 10</example>. Return the answer and the SELECT statement in plain English."""


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
    SourceAccount=account_id,
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
