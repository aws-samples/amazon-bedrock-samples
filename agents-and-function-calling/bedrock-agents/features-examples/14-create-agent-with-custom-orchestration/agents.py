import boto3
import json
import time
import zipfile
from io import BytesIO
import logging
import pprint
import os
import subprocess
from pathlib import Path

print(f"Boto3 version: {boto3.__version__}")

iam_client = boto3.client('iam')
sts_client = boto3.client('sts')
s3_client = boto3.client('s3')
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
dynamodb_client = boto3.client('dynamodb')
dynamodb_resource = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
# bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_client = boto3.client(
    'bedrock-agent',
    region_name=region
)

bedrock_agent_runtime_client = boto3.client(
    'bedrock-agent-runtime',
    region_name=region
)
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def create_dynamodb(table_name, attribute_name):
    try:
        table = dynamodb_resource.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': attribute_name,
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': attribute_name,
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # Use on-demand capacity mode
        )
        # Wait for the table to be created
        print(f'Creating table {table_name}...')
        table.wait_until_exists()
        print(f'Table {table_name} created successfully!')
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f'Table {table_name} already exists!')
        print('Deleting and recreating it!')
        dynamodb_client.delete_table(
            TableName=table_name
        )
        time.sleep(10)
        table = dynamodb_resource.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': attribute_name,
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': attribute_name,
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # Use on-demand capacity mode
        )
        # Wait for the table to be created
        print(f'Creating table {table_name}...')
        table.wait_until_exists()
        print(f'Table {table_name} created successfully!')


def create_lambda(
    lambda_function_name, lambda_file_path, lambda_iam_role, 
    layers=None, environment={}
):
    # Package up the lambda function code
    s = BytesIO()
    z = zipfile.ZipFile(s, 'w')
    z.write(lambda_file_path)
    z.close()
    zip_content = s.getvalue()
    handler = lambda_file_path.replace('.py', '')
    try:
        # Create Lambda Function
        lambda_function = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime='python3.11',
            Timeout=60,
            Role=lambda_iam_role['Role']['Arn'],
            Code={'ZipFile': zip_content},
            Handler=f'{handler}.lambda_handler',
            Layers=layers,
            Environment=environment
        )
    except lambda_client.exceptions.ResourceConflictException:
        print(f'{lambda_function_name} already exists, deleting it and recreating')
        lambda_client.delete_function(
            FunctionName=lambda_function_name
        )
        time.sleep(10)
        lambda_function = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime='python3.11',
            Timeout=60,
            Role=lambda_iam_role['Role']['Arn'],
            Code={'ZipFile': zip_content},
            Handler=f'{handler}.lambda_handler',
            Layers=layers,
            Environment=environment
        )
    return lambda_function


def create_lambda_role(agent_name):
    lambda_function_role = f'{agent_name}-lambda-role'
    lambda_basic_role = 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    dynamodb_role = 'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess'
    
    # Define the trust relationship policy
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

    try:
        # Delete existing role if it exists
        try:
            policies = iam_client.list_attached_role_policies(
                RoleName=lambda_function_role,
                MaxItems=100
            )
            for policy in policies['AttachedPolicies']:
                print(f"Detaching {policy['PolicyName']}")
                iam_client.detach_role_policy(
                    RoleName=lambda_function_role,
                    PolicyArn=policy['PolicyArn']
                )
            print(f"deleting {lambda_function_role}")
            iam_client.delete_role(
                RoleName=lambda_function_role
            )
        except iam_client.exceptions.NoSuchEntityException:
            pass  # Role doesn't exist, which is fine

        # Create the role
        print(f"Creating role: {lambda_function_role}")
        lambda_iam_role = iam_client.create_role(
            RoleName=lambda_function_role,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document)
        )

        # Wait for role to be created and available
        print("Waiting for role to be available...")
        waiter = iam_client.get_waiter('role_exists')
        waiter.wait(
            RoleName=lambda_function_role,
            WaiterConfig={'Delay': 5, 'MaxAttempts': 10}
        )

        # Attach policies
        print(f"Attaching basic lambda permissions to {lambda_function_role}")
        iam_client.attach_role_policy(
            RoleName=lambda_function_role,
            PolicyArn=lambda_basic_role
        )
        
        print(f"Attaching dynamodb permissions to {lambda_function_role}")
        iam_client.attach_role_policy(
            RoleName=lambda_function_role,
            PolicyArn=dynamodb_role
        )

        # Add additional delay to ensure permissions are propagated
        time.sleep(15)

        return lambda_iam_role

    except Exception as e:
        print(f"Error creating Lambda role: {str(e)}")
        raise e


def wait_agent_status_update(agent_id):
    response = bedrock_agent_client.get_agent(agentId=agent_id)
    agent_status = response['agent']['agentStatus']
    while agent_status.endswith('ING'):
        print(f'Waiting for agent status to change. Current status {agent_status}')
        time.sleep(5)
        try:
            response = bedrock_agent_client.get_agent(agentId=agent_id)
            agent_status = response['agent']['agentStatus']
        except bedrock_agent_client.exceptions.ResourceNotFoundException:
            agent_status = 'DELETED'
    print(f'Agent id {agent_id} current status: {agent_status}')


def create_agent_object(
    agent_name, agent_role, agent_description,
    idle_session_ttl_in_seconds, agent_foundation_model,
    agent_instruction, custom_orchestration_lambda, prompt_override_configuration
):
    try:
        if custom_orchestration_lambda is not None:
            response = bedrock_agent_client.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=agent_role['Role']['Arn'],
                description=agent_description,
                idleSessionTTLInSeconds=idle_session_ttl_in_seconds,
                foundationModel=agent_foundation_model,
                instruction=agent_instruction,
                customOrchestration={
                    "executor": {
                        "lambda": custom_orchestration_lambda['FunctionArn']
                    }
                },
                orchestrationType="CUSTOM_ORCHESTRATION"
                
            )
        else:
            response = bedrock_agent_client.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=agent_role['Role']['Arn'],
                description=agent_description,
                idleSessionTTLInSeconds=idle_session_ttl_in_seconds,
                foundationModel=agent_foundation_model,
                instruction=agent_instruction
            )
        agent_id = response['agent']['agentId']
        return agent_id
    except bedrock_agent_client.exceptions.ConflictException:
        agents = bedrock_agent_client.list_agents(
            maxResults=1000
        )
        agent_id = None
        for agent in agents['agentSummaries']:
            if agent['agentName'] == agent_name:
                agent_id = agent['agentId']
        agent_aliases = bedrock_agent_client.list_agent_aliases(
            agentId=agent_id,
            maxResults=100
        )
        for alias in agent_aliases['agentAliasSummaries']:
            alias_id = alias['agentAliasId']
            print(f'Deleting alias {alias_id} from agent {agent_id}')
            response = bedrock_agent_client.delete_agent_alias(
                agentAliasId=alias_id,
                agentId=agent_id
            )
        bedrock_agent_client.delete_agent(
            agentId=agent_id
        )
        wait_agent_status_update(agent_id)
        if custom_orchestration_lambda is not None:
            response = bedrock_agent_client.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=agent_role['Role']['Arn'],
                description=agent_description,
                idleSessionTTLInSeconds=idle_session_ttl_in_seconds,
                foundationModel=agent_foundation_model,
                instruction=agent_instruction, 
                customOrchestration={
                    "executor": {
                        "lambda": custom_orchestration_lambda['FunctionArn']
                    }
                },
                orchestrationType="CUSTOM_ORCHESTRATION"
                
            )
        else:
            response = bedrock_agent_client.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=agent_role['Role']['Arn'],
                description=agent_description,
                idleSessionTTLInSeconds=idle_session_ttl_in_seconds,
                foundationModel=agent_foundation_model,
                instruction=agent_instruction
            )
        agent_id = response['agent']['agentId']
        return agent_id


def create_agent(
    agent_name, agent_instruction,
    agent_foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
    idle_session_ttl_in_seconds=1800,
    agent_description="",
    action_group_config=None,
    kb_config=None,
    custom_orchestration_lambda=None,
    prompt_override_configuration={},
    create_alias=True
):
    print('creating agent')
    kb_id = None
    if kb_config:
        kb_id = kb_config['kb_id']

    if action_group_config and 'api_schema' in action_group_config:
        bucket_name = action_group_config['api_schema']['bucket_name']
        bucket_key = action_group_config['api_schema']['bucket_key']
        schema_arn = f'arn:aws:s3:::{bucket_name}/{bucket_key}'
    else:
        schema_arn = None
    agent_role = create_agent_role_and_policies(
        agent_name, agent_foundation_model, kb_id=kb_id,
        schema_arn=schema_arn
    )
    if custom_orchestration_lambda or action_group_config:
        lambda_iam_role = create_lambda_role(agent_name)
    else:
        lambda_iam_role = None
        
    if custom_orchestration_lambda:
        layers = []
        environment = {}
        if 'lambda_layers' in action_group_config:
            layers = action_group_config['lambda_layers']
        if 'environment' in action_group_config:
            environment = action_group_config['environment']
        custom_orchestration_lambda_function = create_lambda(
            custom_orchestration_lambda['lambda_function_name'],
            custom_orchestration_lambda['lambda_file_path'],
            lambda_iam_role,
            layers,
            environment
        )
    else:
        custom_orchestration_lambda_function = None
    agent_id = create_agent_object(
        agent_name, agent_role, agent_description,
        idle_session_ttl_in_seconds, agent_foundation_model,
        agent_instruction, custom_orchestration_lambda_function, 
        prompt_override_configuration
    )
    if custom_orchestration_lambda:
        lambda_client.add_permission(
            FunctionName=custom_orchestration_lambda['lambda_function_name'],
            StatementId='allow_bedrock_prod',
            Action='lambda:InvokeFunction',
            Principal='bedrock.amazonaws.com',
            SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}"
        )
    # if action group configuration is provided
    if action_group_config:
        print('creating and attaching action group')
        layers = []
        environment = {}
        if 'lambda_layers' in action_group_config:
            layers = action_group_config['lambda_layers']
        if 'environment' in action_group_config:
            environment = action_group_config['environment']
        lambda_function = create_lambda(
            action_group_config['lambda_function_name'],
            action_group_config['lambda_file_path'],
            lambda_iam_role,
            layers,
            environment
        )
        if 'dynamodb_table_name' in action_group_config:
            create_dynamodb(
                action_group_config['dynamodb_table_name'],
                action_group_config['dynamodb_attribute_name']
            )
        if 'functions' in action_group_config:
            agent_functions = action_group_config['functions']
            bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupExecutor={
                    'lambda': lambda_function['FunctionArn']
                },
                actionGroupName=action_group_config['name'],
                functionSchema={
                    'functions': agent_functions
                },
                description=action_group_config['description']
            )
        elif 'api_schema' in action_group_config:
            api_schema = action_group_config['api_schema']
            bedrock_agent_client.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupExecutor={
                    'lambda': lambda_function['FunctionArn']
                },
                actionGroupName=action_group_config['name'],
                apiSchema={
                    's3': {
                        's3BucketName': api_schema['bucket_name'],
                        's3ObjectKey': api_schema['bucket_key']
                    }
                },
                description=action_group_config['description']
            )
        else:
            raise ("functions or api_schema must be provided in action_group_config")
        lambda_client.add_permission(
            FunctionName=action_group_config['lambda_function_name'],
            StatementId='allow_bedrock_prod',
            Action='lambda:InvokeFunction',
            Principal='bedrock.amazonaws.com',
            SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}"
        )
    if kb_config:
        print('associating knowledge base')
        bedrock_agent_client.associate_agent_knowledge_base(
            agentId=agent_id,
            agentVersion='DRAFT',
            description=kb_config['kb_instruction'],
            knowledgeBaseId=kb_config['kb_id'],
            knowledgeBaseState='ENABLED'
        )


    if create_alias:
        wait_agent_status_update(agent_id)
        bedrock_agent_client.prepare_agent(
            agentId=agent_id
        )
        wait_agent_status_update(agent_id)
        agent_alias = bedrock_agent_client.create_agent_alias(
            agentAliasName='v1', agentId=agent_id
        )
        agent_alias_id = agent_alias['agentAlias']['agentAliasId']
        agent_alias_arn = agent_alias['agentAlias']['agentAliasArn']
        wait_agent_status_update(agent_id)
    else:
        wait_agent_status_update(agent_id)
        bedrock_agent_client.prepare_agent(
            agentId=agent_id
        )
        wait_agent_status_update(agent_id)
        agent_alias_id = 'TSTALIASID'
        agent_alias_arn = None
    return agent_id, agent_alias_id, agent_alias_arn, custom_orchestration_lambda_function



def create_agent_role_and_policies(
    agent_name, agent_foundation_model, schema_arn=None,
    kb_id=None
):
    agent_bedrock_allow_policy_name = f"{agent_name}-ba"
    agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{agent_name}'
    # Create IAM policies for agent
    statements = [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                f"arn:aws:bedrock:{region}::foundation-model/{agent_foundation_model}"
            ]
        }
    ]
    if schema_arn:
        statements.append(
            {
                "Sid": "AllowAgentAccessOpenAPISchema",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": [
                    schema_arn
                ]
            }
        )

    # add Knowledge Base retrieve and retrieve and generate permissions if agent has KB attached to it
    if kb_id:
        statements.append(
            {
                "Sid": "QueryKB",
                "Effect": "Allow",
                "Action": [
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}"
                ]
            }
        )

    bedrock_agent_bedrock_allow_policy_statement = {
        "Version": "2012-10-17",
        "Statement": statements
    }

    bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)
    try:
        agent_bedrock_policy = iam_client.create_policy(
            PolicyName=agent_bedrock_allow_policy_name,
            PolicyDocument=bedrock_policy_json
        )
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f'Policy {agent_bedrock_allow_policy_name} already exists')
        print(f'Checking if {agent_role_name} role also exists')
        response = iam_client.list_roles(
            MaxItems=1000
        )
        exists = False
        for role in response['Roles']:
            if role['RoleName'] == agent_role_name:
                exists = True
        if exists:
            policies = iam_client.list_attached_role_policies(
                RoleName=agent_role_name,
                MaxItems=1000
            )
            for policy in policies['AttachedPolicies']:
                print(f"Detaching and deleting {policy['PolicyName']}")
                iam_client.detach_role_policy(
                    RoleName=agent_role_name,
                    PolicyArn=policy['PolicyArn']
                )
                iam_client.delete_policy(
                    PolicyArn=policy['PolicyArn']
                )
            print(f"deleting {agent_role_name}")
            iam_client.delete_role(
                RoleName=agent_role_name
            )
        print(f'Recreating {agent_bedrock_allow_policy_name}')
        agent_bedrock_policy = iam_client.create_policy(
            PolicyName=agent_bedrock_allow_policy_name,
            PolicyDocument=bedrock_policy_json
        )
    # Create IAM Role for the agent and attach IAM policies
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
              "Effect": "Allow",
              "Principal": {
                "Service": "bedrock.amazonaws.com"
              },
              "Action": "sts:AssumeRole"
            }
        ]
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
    return agent_role


def clean_up_resources(
    agent_name,
    custom_orchestration_lambda_function_name=None,
    dynamodb_table=None
):
    agents_list = bedrock_agent_client.list_agents(maxResults=1000)['agentSummaries']
    # find agent id
    agent_id = None
    for agent in agents_list:
        if agent['agentName'] == agent_name:
            agent_id = agent['agentId']
            agent_details = bedrock_agent_client.get_agent(agentId=agent_id)['agent']
            agent_role_arn = agent_details['agentResourceRoleArn']
    
    if agent_id:
        # list agent versions
        agent_versions = bedrock_agent_client.list_agent_versions(agentId=agent_id, maxResults=1000)['agentVersionSummaries']
        for version in agent_versions:
            agent_v = version['agentVersion']
            agent_v_ags = bedrock_agent_client.list_agent_action_groups(
                agentId=agent_id, agentVersion=agent_v, maxResults=1000
            )['actionGroupSummaries']
            # interact through the action groups to disable them one by one
            for ag in agent_v_ags:
                ag_id = ag['actionGroupId']
                ag_details = bedrock_agent_client.get_agent_action_group(
                    actionGroupId=ag_id, agentId=agent_id, agentVersion=agent_v
                )['agentActionGroup']
                # disable action group
                bedrock_agent_client.update_agent_action_group(
                    agentId=agent_id,
                    agentVersion=agent_v,
                    actionGroupId=ag_id,
                    actionGroupName=ag_details['actionGroupName'],
                    actionGroupExecutor=ag_details['actionGroupExecutor'],
                    functionSchema=ag_details['functionSchema'],
                    actionGroupState='DISABLED',
                )
                agent_lambda_arn = ag_details['actionGroupExecutor']['lambda']
                ag_lambda_role = lambda_client.get_function(
                    FunctionName=agent_lambda_arn
                )['Configuration']['Role']
                lambda_client.delete_function(FunctionName=agent_lambda_arn)
                bedrock_agent_client.delete_agent_action_group(
                    agentId=agent_id,
                    agentVersion=agent_v,
                    actionGroupId=ag_id
                )
                # delete lambda role
                attached_policies = iam_client.list_attached_role_policies(
                    RoleName=ag_lambda_role.split('/')[1], MaxItems=1000
                )['AttachedPolicies']
                for policy in attached_policies:
                    iam_client.detach_role_policy(
                        RoleName=ag_lambda_role.split('/')[1],
                        PolicyArn=policy['PolicyArn']
                    )
                iam_client.delete_role(
                    RoleName=ag_lambda_role.split('/')[1]
                )


            agent_v_kbs = bedrock_agent_client.list_agent_knowledge_bases(
                agentId=agent_id, agentVersion=agent_v, maxResults=1000
            )['agentKnowledgeBaseSummaries']
            for agent_kb in agent_v_kbs:
                kb_id = agent_kb['knowledgeBaseId']
                bedrock_agent_client.disassociate_agent_knowledge_base(
                    agentId=agent_id,
                    agentVersion=agent_v,
                    knowledgeBaseId=kb_id
                )
            if agent_v != "DRAFT":
                bedrock_agent_client.delete_agent_version(
                    agentId=agent_id,
                    agentVersion=agent_v,
                    skipResourceInUseCheck=False
                )
        bedrock_agent_client.delete_agent(agentId=agent_id)
        print(
            f"Agent {agent_name} and its associated versions and action groups have been deleted."
        )
    if custom_orchestration_lambda_function_name:
        orchestration_lambda_role = lambda_client.get_function(
            FunctionName=custom_orchestration_lambda_function_name
        )['Configuration']['Role']
        try:
            attached_policies = iam_client.list_attached_role_policies(
                RoleName=orchestration_lambda_role.split('/')[1], MaxItems=1000
            )['AttachedPolicies']
            for policy in attached_policies:
                iam_client.detach_role_policy(
                    RoleName=orchestration_lambda_role.split('/')[1],
                    PolicyArn=policy['PolicyArn']
                )
            iam_client.delete_role(
                RoleName=orchestration_lambda_role.split('/')[1]
            )
            
            lambda_client.delete_function(FunctionName=custom_orchestration_lambda_function_name)
            print(f"Orchestration lambda {custom_orchestration_lambda_function_name} deleted together with its roles and policies")
        except:
            lambda_client.delete_function(FunctionName=custom_orchestration_lambda_function_name)
            print("Orchestration role could not be found. Orchestration lambda was deleted without its roles")
    
    if dynamodb_table:
        dynamodb_client.delete_table(TableName=dynamodb_table)
        print(f"Table {dynamodb_table} is being deleted...")
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(TableName=dynamodb_table)
        print(f"Table {dynamodb_table} has been deleted.")

    else:
        raise Exception("Agent not found! Check your agent id and make sure it exists to be deleted")


def invoke_agent_helper(
    query, session_id, agent_id, alias_id, enable_trace=False, session_state=None
):
    end_session: bool = False
    if not session_state:
        session_state = {}

    # invoke the agent API
    agent_response = bedrock_agent_runtime_client.invoke_agent(
        inputText=query,
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        enableTrace=enable_trace,
        endSession=end_session,
        sessionState=session_state
    )

    if enable_trace:
        logger.info(pprint.pprint(agent_response))

    event_stream = agent_response['completion']
    try:
        for event in event_stream:
            if 'chunk' in event:
                data = event['chunk']['bytes']
                if enable_trace:
                    logger.info(f"Final answer ->\n{data.decode('utf8')}")
                    for key in event['chunk']:
                        if key != 'bytes':
                            logger.info(f"Chunck {key}:\n")
                            logger.info(json.dumps(event['chunk'][key], indent=3))
                agent_answer = data.decode('utf8')
                return agent_answer
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                if enable_trace:
                    logger.info(json.dumps(event['trace'], indent=2))
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)


def create_lambda_layer(agent_name, requirements):
    # Create directory structure
    Path("layer/python").mkdir(parents=True, exist_ok=True)

    # Install packages
    subprocess.check_call([
        "pip",
        "install",
        "-r",
        requirements,
        "-t",
        "layer/python"
    ])

    # Install zip
    subprocess.check_call([
        "sudo",
        "apt",
        "install",
        "zip"
    ])

    # Create ZIP file
    subprocess.check_call([
        "zip",
        "-r",
        "layer.zip",
        "python"
    ], cwd="layer")

    # Create Lambda layer
    lambda_client = boto3.client('lambda')

    try:
        with open("layer/layer.zip", 'rb') as zip_file:
            response = lambda_client.publish_layer_version(
                LayerName=f'{agent_name}-layer',
                Description='Action group lambda layer',
                Content={
                    'ZipFile': zip_file.read()
                },
                CompatibleRuntimes=[
                    'python3.7', 'python3.8', 'python3.9', 'python3.10', 'python3.11', 'python3.12'
                ],
                CompatibleArchitectures=['x86_64']
            )

        print(f"Layer created successfully. Version: {response['Version']}")
        print(f"Layer ARN: {response['LayerVersionArn']}")

        # Clean up
        os.system("rm -rf layer")

        return response['LayerVersionArn']

    except Exception as e:
        print(f"Error creating layer: {str(e)}")
        return None


def upload_api_schema(agent_name, api_schema_path):
    bucket_name = f'{agent_name}-{account_id}-{region}'
    # Create S3 bucket for Open API schema
    if region == "us-east-1":
        s3_client.create_bucket(
            Bucket=bucket_name
        )
    else:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': region
            }
        )
    print(bucket_name)
    # Upload Open API schema to this s3 bucket
    s3_client.upload_file(api_schema_path, bucket_name, api_schema_path)
    return bucket_name, api_schema_path
