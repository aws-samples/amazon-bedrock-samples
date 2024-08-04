from config import *


################################################
##### Create S3 bucket and upload API Schema
################################################
# Agents require an API Schema stored on s3. Let's create an S3 bucket to store the file and upload the file to the newly created bucket

# Create S3 bucket for Open API schema
s3bucket = s3_client.create_bucket(
    Bucket=bucket_name
)


# Upload Open API schema to this s3 bucket
s3_client.upload_file("./dependencies/" + schema_name, bucket_name, bucket_key)

sts_response = sts_client.get_caller_identity().get('Account')
print("AccountID: ", sts_response)

sts_response = sts_client.get_caller_identity().get('Arn')
print(sts_response)


################################################
##### Create Lambda function for Action Group
################################################

# Let's now create the lambda function required by the agent action group. 
# We first need to create the lambda IAM role and it's policy. 
# After that, we package the lambda function into a ZIP format to create the function


# Create IAM Role for the Lambda function

try:
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
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

aoss_api_access_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "aoss:APIAccessAll",
            "Resource": "*"
        }
    ]
}

s3_read_write_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                f"arn:aws:s3:::{bucket_name}/*"
            ]
        }
    ]
}

# add the AOSS access policy to the lambda function
iam_client.put_role_policy(
    RoleName=lambda_role_name,
    PolicyName='AOSSAPIAccessPolicy',
    PolicyDocument=json.dumps(aoss_api_access_policy)
)

# add the s3 read_write policy to the lambda function
iam_client.put_role_policy(
    RoleName=lambda_role_name,
    PolicyName='S3ReadWritePolicy',
    PolicyDocument=json.dumps(s3_read_write_policy)
)

# add the existing policy arns (These are AWS managed policies in IAM Policies)
policy_arns = [
    'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
]
for policy_arn in policy_arns:
    iam_client.attach_role_policy(
        RoleName=lambda_role_name,
        PolicyArn=policy_arn
    )

# Add the custom policy for Bedrock - to provide access to only the used Foundation Models.
bedrock_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-image-generator-v1",
                f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-image-v1"
            ]
        }
    ]
}
iam_client.put_role_policy(
    RoleName=lambda_role_name,
    PolicyName='BedrockInvokePolicy',
    PolicyDocument=json.dumps(bedrock_policy)
)


### Add layer for the lambda Function:
# Opensearch-py layer (stored as a zip file in dependencies folder)

response = lambda_client.list_layers(
    CompatibleRuntime='python3.11'
)

existing_layers = response['Layers']
layer_exists = False
layer_version_arn = None

for layer in existing_layers:
    if layer['LayerName'] == 'opensearch-py-layer':
        layer_exists = True
        layer_version_arn = layer['LatestMatchingVersion']['LayerVersionArn']
        print(f'Found existing layer: {layer_version_arn}')
        break

if not layer_exists:
    print("Create opensearch-py layer for Lambda Function")
    with open('./dependencies/opensearch-py-layer.zip', 'rb') as f:
        zip_file = f.read()
    response = lambda_client.publish_layer_version(
        LayerName='opensearch-py-layer',
        Content={
            'ZipFile': zip_file
        },
        CompatibleRuntimes=['python3.11']
    )
    layer_version_arn = response['LayerVersionArn']
    print("opensearch-py layer created!")

# Package up the lambda function code
s = BytesIO()
z = zipfile.ZipFile(s, 'w')
z.write(lambda_code_path)
z.close()
zip_content = s.getvalue()

# Check aoss_host variable
try:
    aoss_host
except NameError:
    aoss_host = ''
else:
    if not aoss_host:
        aoss_host = ''

# Create Lambda Function with the zip file content
lambda_function = lambda_client.create_function(
    FunctionName=lambda_name,
    Runtime='python3.11',
    Timeout=180,
    Role=lambda_iam_role['Role']['Arn'],
    Code={'ZipFile': zip_content},
    Handler='lambda_function.lambda_handler',
    Environment={'Variables': {'region_info': region, 's3_bucket': s3_bucket, 'index_name': index_name,
                               'embeddingSize': str(embeddingSize), 'aoss_host': aoss_host}},
    Layers=[
        layer_version_arn,
        f'arn:aws:lambda:{region}:770693421928:layer:Klayers-p311-Pillow:4',
        f'arn:aws:lambda:{region}:770693421928:layer:Klayers-p311-requests:7'
    ]
)
####################################################
######### Give permissions to the agent ############
####################################################

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
print(f"Bedrock Agent policy name for bedrock: {bedrock_agent_bedrock_allow_policy_name}")
agent_bedrock_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_bedrock_allow_policy_name,
    PolicyDocument=bedrock_policy_json
)
## for S3 
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


def update_access_policy(aoss_client, policy_name, lambda_role_arn):
    try:
        response = aoss_client.get_access_policy(name=policy_name, type='data')
        policy = response['accessPolicyDetail']['policy']
        policy_version = response['accessPolicyDetail']['policyVersion']

        policy[0]['Principal'].append(lambda_role_arn)

        updated_policy = json.dumps(policy)
        response = aoss_client.update_access_policy(
            name=policy_name,
            type='data',
            policy=updated_policy,
            policyVersion=policy_version
        )
        print(f'Access policy "{policy_name}" updated successfully')
    except Exception as e:
        print(f'Error updating access policy: {str(e)}')


if aoss_host:
    update_access_policy(aoss_client, '{}-policy'.format(collection_name), lambda_iam_role['Role']['Arn'])
    print("Lambda role added to AOSS data access policy")


#######################################
########### Create Agent ##############
#######################################

# Once the needed IAM role is created, we can use the bedrock agent client to create a new agent. To do so we use the `create_agent` function. 
# It requires an agent name, underline foundation model and instruction. You can also provide an agent description. Note that the agent created is not yet prepared.
# We will focus on preparing the agent and then using it to invoke actions and use other APIs

# Create Agent instruction
agent_instruction = """DO NOT RESPOND TO NON FASHION RELATED REQUESTS. CLASSIFY USER REQUEST AS FASHION RELATED OR NOT FIRST. You are a fashion designer that can help create images, find the weather at a location to customize the image, find images similar to an image given by the user in a knowledge base, and peform inpainting where a part of an image called a mask is specified and filled in with the background of the image. Do not make any assumptions about what to fill the masked section with. If no images are found in the knowledge base, create an image based on the input image from the user. Use the /weather api output as the input value for the weather parameter into the /imageGeneration api only if a location is mentioned in the user query. If the user makes a request about an image that is not fashion related do not do anything else or ask followup questions, immediately say "Sorry I am only a fashion expert, please try and ask a fashion related question." If a call to search for similar images is made but no input_location is provided, use a default value of "None" for the input value. FInd weather at location if user asks for a clothing for a location provided. When providing the weather as a parameter interpret the weather using the follwing example: 
 Interpret the temperature as very hot, hot, cold, very cold,or warm and add to this the weather conditions. Output should only be at most 1 sentence like the example below:

<example>
input weather: Temperature is 90 in Fahrenheit. It is a sunny day.
output: a very hot and sunny day.
</example>.

 If the output contains a S3 URI, return the S3 URI inside XML tag, in a format of "<generated_s3_uri>output_s3_uri</generated_s3_uri>"""

## NOTE: Disabling pre-processing can enhance the agent's response time, however, it may increase the risk of inaccuracies in SQL query generation or some sql ingestion. Careful consideration is advised when toggling this feature based on your use case requirements.


response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_role['Role']['Arn'],
    description="Agent for fashion related topics",
    idleSessionTTLInSeconds=idleSessionTTLInSeconds,
    foundationModel=foundation_Model,
    instruction=agent_instruction,
)

# Looking at the created agent, we can see its status and agent id

# Let's now store the agent id in a local variable to use it on the next steps


agent_id = response['agent']['agentId']
print(f"agent ID - {agent_id}")

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
    actionGroupName='imagevar',
    apiSchema={
        's3': {
            's3BucketName': bucket_name,
            's3ObjectKey': bucket_key
        }
    },
    description='Actions related to creating images and getting information to process images'
)

print(f"Action group created with response: {agent_action_group_response}")

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
print(f"{agent_prepare}")


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

print(f"Agent Alias created: {agent_alias}")