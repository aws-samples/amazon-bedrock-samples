from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    CfnOutput,
    Size,
)

from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
)

from constructs import Construct


AGENT_FOUNDATION_MODEL_NAME = "anthropic.claude-3-haiku-20240307-v1:0"
AGENT_INSTRUCTION = "You are a professional marketing expert of social media marketing \
experience and facebook post writing experience. \
    You help customer generate marketing context in english through following steps:\
1. Search historical marketing text context from knowledgebase\
2. Get the merchandise information in detail\
3. Get the target audience for the merchandise in detail\
4. Assist user to generate the content for personalized marketing"

class MarketingAgentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 Bucket for related data
        _data_bucket = s3.Bucket(
            self, "data-bucket", 
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Upload Related Data to S3 Bucket
        _deploy_data = s3_deployment.BucketDeployment(self, "deploy-data",
            sources=[s3_deployment.Source.asset("data/")],
            destination_bucket=_data_bucket,
            exclude=[".DS_Store"],
            ephemeral_storage_size=Size.mebibytes(1024),
            memory_limit=1024
        )

        # Create DynamoDB table for item data
        _item_table = dynamodb.Table(
            self, "item-table",
            partition_key=dynamodb.Attribute(
                name="ITEM_ID",
                type=dynamodb.AttributeType.STRING
            ),
            import_source=dynamodb.ImportSourceSpecification(
                input_format=dynamodb.InputFormat.csv(),
                bucket=_data_bucket,
                key_prefix="DynamoDB/items.csv"
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        _item_table.node.add_dependency(_deploy_data)

        
        # Create DynamoDB table for user data
        _user_table = dynamodb.Table(
            self, "user-table",
            partition_key=dynamodb.Attribute(
                name="USER_ID",
                type=dynamodb.AttributeType.NUMBER
            ),
            import_source=dynamodb.ImportSourceSpecification(
                input_format=dynamodb.InputFormat.csv(),
                bucket=_data_bucket,
                key_prefix="DynamoDB/users.csv"
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        _user_table.node.add_dependency(_deploy_data)

        _marketing_agent_kb = bedrock.KnowledgeBase(self, 'market-agent-kb', 
            embeddings_model= bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
            instruction='UNDEFINED',    
        )

        _kb_s3_datasource = bedrock.S3DataSource(self, 'market-context-DataSource',
            bucket= _data_bucket,
            knowledge_base=_marketing_agent_kb,
            data_source_name='marketing-context',
            inclusion_prefixes=["context/"]
        )
        _kb_s3_datasource.node.add_dependency(_deploy_data)

        # Lambda Agent IAM role
        bedrock_agent_lambda_role = iam.Role(self, "BerockAgentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                ),
            ]
        )
        _data_bucket.grant_read(bedrock_agent_lambda_role)
        _item_table.grant_read_data(bedrock_agent_lambda_role)
        _user_table.grant_read_data(bedrock_agent_lambda_role)


        # Pandas Lambda layer
        pandas_layer_arn = lambda_.LayerVersion.from_layer_version_arn(
            self, 
            "PandasLayer",
            layer_version_arn="arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312:9"
        )

        # Lambda function for Agent Group
        agent_function = lambda_.Function(self, "market-agent-function",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda/"),
            layers=[pandas_layer_arn],
            timeout=Duration.seconds(600),
            environment={
                'BUCKET_PERSONALIZE_DATA': _data_bucket.bucket_name,
                'KEY_PERSONALIZE_DATA': 'personalize/item.json.out',
                'BUCKET_IMAGE': _data_bucket.bucket_name,
                'ITEM_TABLE_NAME': _item_table.table_name,
                'USER_TABLE_NAME': _user_table.table_name,
            },
            role=bedrock_agent_lambda_role
        )
        _action_group = bedrock.AgentActionGroup(self,
                    "marketing-agent-action-group",
                    action_group_name="marketing-agent-action-group",
                    action_group_executor= bedrock.ActionGroupExecutor(
                        lambda_=agent_function
                    ),
                    action_group_state="ENABLED",
                    api_schema=bedrock.ApiSchema.from_asset(
                        "data/agent-schema/openapi.json")
        )
        _marketing_agent = bedrock.Agent(
            self,
            "marketing-agent",
            foundation_model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_HAIKU_V1_0,
            instruction=AGENT_INSTRUCTION,
            should_prepare_agent=True,
            enable_user_input=True,
            knowledge_bases=[_marketing_agent_kb],
        )
        _marketing_agent.add_action_group(_action_group)

        CfnOutput(
            self, 'agent-name', 
            value=_marketing_agent.name,
            key='BedrockAgentName'
        )
        
        CfnOutput(
            self, 's3-bucket-name', 
            value=_data_bucket.bucket_name,
            key='s3DataBucketName'
        )
