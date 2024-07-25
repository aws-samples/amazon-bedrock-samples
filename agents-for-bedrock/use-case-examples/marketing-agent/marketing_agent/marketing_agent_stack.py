from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_dynamodb as dynamodb,
    # aws_opensearchserverless as oss,
    aws_iam as iam,
    aws_lambda as lambda_,
    # aws_lambda_python_alpha as lambda_python,
    # aws_logs as logs,
    # custom_resources,
    # CustomResource,
)

from cdklabs.generative_ai_cdk_constructs import (
    bedrock,
    opensearchserverless,
    opensearch_vectorindex
)

from constructs import Construct

# import json

AGENT_NAME = "marketing-bedrock-agent"
KB_NAME = "marketing-agent-bedrock-kb"
ACTION_GROUP_NAME = "marketing-agent-action-group"
DATA_SOURCE_NAME = "marketing-agent-data-source"
COLLECTION_NAME = "marketing-agent-collection"
INDEX_NAME = "marketing-agent-index"
NETWORK_POLICY_NAME = "marketing-agent-network-policy"
ACCESS_POLICY_NAME = "marketing-agent-access-policy"
AGENT_FOUNDATION_MODEL_NAME = "anthropic.claude-3-haiku-20240307-v1:0"
AGENT_INSTRUCTION = "You are a professional marketing expert of social media marketing \
experience and facebook post writing experience. \
    You help customer generate marketing context in english through following steps:\
1. Search historical marketing text context from knowledgebase\
2. Get the merchandise information in detail\
3. Get the target audience for the merchandise in detail\
4. Assist user to generate the content for personalized marketing"

VECTOR_FIELD_NAME = "marketing-agent-bedrock-knowledge-base-vector"
VECTOR_INDEX_NAME = "marketing-agent-bedrock-knowledge-base-index"
TEXT_FIELD = "AMAZON_BEDROCK_TEXT_CHUNK"
METADATA_FIELD = "AMAZON_BEDROCK_METADATA"

# ITEM_TABLE_NAME = 'item-table'
# USER_TABLE_NAME = 'user-table'


class MarketingAgentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 Bucket for related data
        data_bucket = s3.Bucket(
            self, "data-bucket", 
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Upload Related Data to S3 Bucket
        s3_deployment.BucketDeployment(self, "deploy-data",
            sources=[s3_deployment.Source.asset("data/")],
            destination_bucket=data_bucket
        )

        # Create DynamoDB table for item data
        item_table = dynamodb.Table(
            self, "item-table",
            partition_key=dynamodb.Attribute(
                name="ITEM_ID",
                type=dynamodb.AttributeType.STRING
            ),
            import_source=dynamodb.ImportSourceSpecification(
                input_format=dynamodb.InputFormat.csv(),
                bucket=data_bucket,
                key_prefix="DynamoDB/items.csv"
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create DynamoDB table for user data
        user_table = dynamodb.Table(
            self, "user-table",
            partition_key=dynamodb.Attribute(
                name="USER_ID",
                type=dynamodb.AttributeType.NUMBER
            ),
            import_source=dynamodb.ImportSourceSpecification(
                input_format=dynamodb.InputFormat.csv(),
                bucket=data_bucket,
                key_prefix="DynamoDB/users.csv"
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        marketing_agent_vector = opensearchserverless.VectorCollection(
            self, "marketing-agent-vector",
            collection_name='marketing-agent'
        )

        # marketing_agent_vector_index = opensearch_vectorindex.VectorIndex(
        #     self, "marketing-agent-vector-index",
        #     vector_dimensions= 1536,
        #     collection=marketing_agent_vector,
        #     index_name=VECTOR_INDEX_NAME,
        #     vector_field=VECTOR_FIELD_NAME,
        #     mappings= [
        #         opensearch_vectorindex.MetadataManagementFieldProps(
        #             mapping_field='AMAZON_BEDROCK_TEXT_CHUNK',
        #             data_type='text',
        #             filterable=True
        #         ),
        #         opensearch_vectorindex.MetadataManagementFieldProps(
        #             mapping_field='AMAZON_BEDROCK_METADATA',
        #             data_type='text',
        #             filterable=False
        #         )
        #     ],
        #     analyzer=opensearch_vectorindex.Analyzer(
        #         character_filters=[opensearchserverless.CharacterFilterType.ICU_NORMALIZER],
        #         tokenizer=opensearchserverless.TokenizerType.KUROMOJI_TOKENIZER,
        #         token_filters=[
        #             opensearchserverless.TokenFilterType.KUROMOJI_BASEFORM,
        #             opensearchserverless.TokenFilterType.JA_STOP,
        #         ],
        #     )
        # )

        marketing_agent_kb = bedrock.KnowledgeBase(self, 'market-agent-kb', 
            embeddings_model= bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
            vector_store=marketing_agent_vector, 
            instruction='UNDEFINED',    
        )

        bedrock.S3DataSource(self, 'market-context-DataSource',
            bucket= data_bucket,
            knowledge_base=marketing_agent_kb,
            data_source_name='marketing-context',
            inclusion_prefixes=["context/"]
        )

        marketing_agent = bedrock.Agent(
            self,
            "marketing-agent",
            foundation_model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_HAIKU_V1_0,
            instruction=AGENT_INSTRUCTION,
            should_prepare_agent=True,
            enable_user_input=True,
        )

        marketing_agent.add_knowledge_base(marketing_agent_kb)

        # Lambda Agent IAM role
        # TODO least privage
        bedrock_agent_lambda_role = iam.Role(self, "BerockAgentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")]
        )

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
                'BUCKET_PERSONALIZE_DATA': data_bucket.bucket_name,
                'KEY_PERSONALIZE_DATA': 'personalize/item.json.out',
                'BUCKET_IMAGE': data_bucket.bucket_name,
                'PREFIX_IMAGE': 'image/',
                'ITEM_TABLE': item_table.table_name,
                'USER_TABLE': user_table.table_name,
            },
            role=bedrock_agent_lambda_role
        )

        marketing_agent_action_group = bedrock.AgentActionGroup(self,
            "marketing-agent-action-group",
            action_group_name="marketing-agent-action-group",
            action_group_executor= bedrock.ActionGroupExecutor(
                lambda_=agent_function
            ),
            action_group_state="ENABLED",
            api_schema=bedrock.ApiSchema.from_asset(
                "data/agent-schema/openapi.json")
        )

        marketing_agent.add_action_group(marketing_agent_action_group)

