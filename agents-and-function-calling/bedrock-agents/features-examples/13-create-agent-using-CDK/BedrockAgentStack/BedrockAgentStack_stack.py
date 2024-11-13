from typing_extensions import runtime
import os
from aws_cdk import (
    Duration,
    CustomResource,
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3_deploy,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_s3_notifications as s3n,
    aws_opensearchserverless as os_serverless,
    aws_iam as iam,
    CfnOutput,
    aws_bedrock as bedrock, aws_ecr_assets,
    custom_resources,
    CfnParameter,
    # aws_sqs as sqs,
)
import json
from constructs import Construct


class BedrockAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        account_id = os.environ["CDK_DEFAULT_ACCOUNT"]
        region = os.environ["CDK_DEFAULT_REGION"]
        suffix = f"{region}-{account_id}"

        # Load configuration
        with open('./BedrockAgentStack/config.json', 'r') as config_file:
            config = json.load(config_file)

        # Define parameters
        agent_name = config['agentName']
        agent_alias_name = config['agentAliasName']
        knowledge_base_name = config['knowledgeBaseName']
        knowledge_base_description = config['knowledgeBaseDescription']
        s3_bucket_name = config['s3BucketName']+region+"-"+account_id
        agent_model_id = config['agentModelId']
        agent_model_arn = bedrock.FoundationModel.from_foundation_model_id(
            scope=self,
            _id='AgentModel',
            foundation_model_id=bedrock.FoundationModelIdentifier(agent_model_id)).model_arn

        # Bedrock embedding model Amazon Titan Text v2
        embedding_model_id = config['embeddingModelId']
        embedding_model_arn = bedrock.FoundationModel.from_foundation_model_id(
            scope=self,
            _id='EmbeddingsModel',
            foundation_model_id=bedrock.FoundationModelIdentifier(embedding_model_id)).model_arn

        agent_description = config['agentDescription']
        agent_instruction = config['agentInstruction']
        agent_action_group_description = config['agentActionGroupDescription']
        agent_action_group_name = config['agentActionGroupName']
        table_name = config['dynamodbTableName']

        # Role that will be used by the KB
        kb_role = iam.Role(
            scope=self,
            id='AgentKBRole',
            assumed_by=iam.ServicePrincipal('bedrock.amazonaws.com'))
        # The name for this role is a requirement for Bedrock
        agent_role = iam.Role(
            scope=self,
            id='AgentRole',
            role_name='AmazonBedrockExecutionRoleForAgents-HotelGenAI',
            assumed_by=iam.ServicePrincipal('bedrock.amazonaws.com'))

        base_lambda_policy = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='service-role/AWSLambdaBasicExecutionRole')
        index_lambda_role = iam.Role(
            scope=self,
            id='IndexCreatorLambdaRole',
            assumed_by=iam.ServicePrincipal(
                'lambda.amazonaws.com'),
            managed_policies=[base_lambda_policy])

        kb_lambda_role = iam.Role(
            scope=self,
            id='KBSyncLambdaRole',
            assumed_by=iam.ServicePrincipal(
                'lambda.amazonaws.com'),
            managed_policies=[base_lambda_policy])

        # Upload the dataset to Amazon S3
        s3Bucket = s3.Bucket(
            self, 'kbs3bucket',
            bucket_name=s3_bucket_name,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            event_bridge_enabled=True)
        bucket_deployment = s3_deploy.BucketDeployment(
            self, "Deploycontent",
            sources=[
                s3_deploy.Source.asset("./dataset")],
            destination_bucket=s3Bucket)

        # OpenSearch Serverless collection
        collection = os_serverless.CfnCollection(
            scope=self,
            id='AgentCollection',
            name='assistant-collection',
            # the properties below are optional
            description='Restaurant assistant Embeddings Store',
            standby_replicas='DISABLED',
            type='VECTORSEARCH')
        encryption_policy_document = json.dumps(
            {'Rules': [{'ResourceType': 'collection',
                        'Resource': [f'collection/{collection.name}']}],
             'AWSOwnedKey': True},
            separators=(',', ':'))
        encryption_policy = os_serverless.CfnSecurityPolicy(
            scope=self,
            id='CollectionEncryptionPolicy',
            name='assistant-col-encryption-policy',
            type='encryption',
            policy=encryption_policy_document)
        collection.add_dependency(encryption_policy)

        network_policy_document = json.dumps(
            [{'Rules': [{'Resource': [f'collection/{collection.name}'],
                         'ResourceType': 'dashboard'},
                        {'Resource': [f'collection/{collection.name}'],
                         'ResourceType': 'collection'}],
              'AllowFromPublic': True}], separators=(',', ':'))
        network_policy = os_serverless.CfnSecurityPolicy(
            scope=self,
            id='CollectionNetworkPolicy',
            name='assistant-col-network-policy',
            type='network',
            policy=network_policy_document)
        collection.add_dependency(network_policy)

        lambda_layer_request_path = "lambda/collections/layer_request.zip"
        lambda_layer_request = lambda_.LayerVersion(
            self, "LambdaLayer",
            code=lambda_.Code.from_asset(lambda_layer_request_path),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12]
        )

        # Create Lambda function
        cust_res_lambda = lambda_.Function(
            self,
            id='CollectionIndexCreator',
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset('lambda/collections'),
            handler='index.handler',
            timeout=Duration.seconds(300),
            role=index_lambda_role,
            layers=[lambda_layer_request],
        )

        res_provider = custom_resources.Provider(
            scope=self,
            id='CustomResourceIndexCreator',
            on_event_handler=cust_res_lambda)

        # Index creator for CustomResouce for Amazon Titan for amazon.titan-embed-text-v1 model
        index_creator = CustomResource(
            scope=self,
            id='CustomCollectionIndexCreator',
            service_token=res_provider.service_token,
            properties={'collection': collection.name,
                        'endpoint': collection.attr_collection_endpoint,
                        'vector_index_name': 'bedrock-knowledge-base-default-index',
                        'vector_size': 1024,   # Depends on embeddings model
                        'metadata_field': 'AMAZON_BEDROCK_METADATA',
                        'text_field': 'AMAZON_BEDROCK_TEXT_CHUNK',
                        'vector_field': 'bedrock-knowledge-base-default-vector'})

        index_creator.node.add_dependency(collection)

        # Create the role that the Bedrock Agent will use
        s3Bucket.grant_read(kb_role)
        kb_role.add_to_policy(iam.PolicyStatement(
            sid='OpenSearchServerlessAPIAccessAllStatement',
            effect=iam.Effect.ALLOW,
            resources=[
                collection.attr_arn],
            actions=['aoss:APIAccessAll']))
        kb_role.add_to_policy(iam.PolicyStatement(
            sid='BedrockInvokeModelStatement',
            effect=iam.Effect.ALLOW,
            resources=[
                embedding_model_arn],
            actions=['bedrock:InvokeModel']))

        # Opensearch data access policy
        policy = json.dumps(
            [{'Rules':
              [{'Resource': [f'collection/{collection.name}'],
                'Permission': ['aoss:CreateCollectionItems',
                               'aoss:DeleteCollectionItems',
                               'aoss:UpdateCollectionItems',
                               'aoss:DescribeCollectionItems'],
                'ResourceType': 'collection'},
               {'Resource': [f'index/{collection.name}/*'],
                'Permission': ['aoss:CreateIndex',
                               'aoss:DeleteIndex',
                               'aoss:UpdateIndex',
                               'aoss:DescribeIndex',
                               'aoss:ReadDocument',
                               'aoss:WriteDocument'],
                'ResourceType': 'index'}],
              'Principal': [kb_role.role_arn, index_lambda_role.role_arn, ],
              'Description': 'Agent data policy'}], separators=(',', ':'))
        data_access_policy = os_serverless.CfnAccessPolicy(
            scope=self,
            id='DataAccessPolicy',
            name='assistant-col-access-policy',
            type='data',
            policy=policy)
        collection.add_dependency(data_access_policy)

        # Give permissions to the Lambda Role to execute the AWS API operations
        index_lambda_role.add_to_policy(iam.PolicyStatement(
            sid='IndexCreationLambdaAccessPolicy',
            effect=iam.Effect.ALLOW,
            resources=[
                collection.attr_arn],
            actions=['aoss:APIAccessAll']))

        # Create the knowledge base in the collection using the provided FM model & role
        # wait for 5 minutes for the collection to be created
        index_creator.node.add_dependency(collection)

        knowledge_base = bedrock.CfnKnowledgeBase(
            scope=self,
            id='KBforAgent',
            name=knowledge_base_name,
            description=knowledge_base_description,
            role_arn=kb_role.role_arn,
            knowledge_base_configuration={'type': 'VECTOR',
                                          'vectorKnowledgeBaseConfiguration': {
                                              'embeddingModelArn': embedding_model_arn}},
            storage_configuration={'type': 'OPENSEARCH_SERVERLESS',
                                   'opensearchServerlessConfiguration': {
                                       'collectionArn': collection.attr_arn,
                                       'vectorIndexName': 'bedrock-knowledge-base-default-index',
                                       'fieldMapping': {
                                           'metadataField': 'AMAZON_BEDROCK_METADATA',
                                           'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                                           'vectorField': 'bedrock-knowledge-base-default-vector'
                                       },
                                       'vector_size': 1024
                                   }})
        knowledge_base.node.add_dependency(index_creator)

        # Create Knowlegebase datasource for provisioned S3 bucket
        datasource = bedrock.CfnDataSource(
            scope=self,
            id=config['knowledgeBaseDataSourceId'],
            name=config['knowledgeBaseDataSourceName'],
            knowledge_base_id=knowledge_base.attr_knowledge_base_id,
            data_source_configuration={'s3Configuration':
                                       {'bucketArn': s3Bucket.bucket_arn},
                                       'type': 'S3'},
            data_deletion_policy='RETAIN')

        # Create Lambda role to acess KB
        base_lambda_policy = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='service-role/AWSLambdaBasicExecutionRole')
        kb_lambda_role.add_to_policy(iam.PolicyStatement(
            sid='SyncKBPolicy',
            effect=iam.Effect.ALLOW,
            resources=[
                knowledge_base.attr_knowledge_base_arn],
            actions=['bedrock:StartIngestionJob']))
        kb_sync_lambda = lambda_.Function(
            scope=self,
            id='SyncKB',
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset(
                'lambda/kb_sync'),
            handler='lambda_function.handler',
            timeout=Duration.seconds(300),
            role=kb_lambda_role,
            environment={'KNOWLEDGE_BASE_ID': knowledge_base.attr_knowledge_base_id,
                         'DATA_SOURCE_ID': datasource.attr_data_source_id}
        )
        s3Bucket.add_event_notification(s3.EventType.OBJECT_CREATED,
                                        s3n.LambdaDestination(kb_sync_lambda))
        s3Bucket.add_event_notification(s3.EventType.OBJECT_REMOVED,
                                        s3n.LambdaDestination(kb_sync_lambda))

        # Add an explicit dependency on the lambda, so that the bucket
        # deployment is started after the lambda is in place

        bucket_deployment.node.add_dependency(kb_sync_lambda)

        # Create the DynamoDB table
        dynamodbable = dynamodb.Table(self, config['dynamodbTableId'],
                                      partition_key=dynamodb.Attribute(
            name=config['dynamodbPartitionKeyId'],
            type=dynamodb.AttributeType.STRING
        ),
            table_name=table_name,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        agent_role.add_to_policy(iam.PolicyStatement(
            sid='InvokeBedrockLambda',
            effect=iam.Effect.ALLOW,
            resources=[
                agent_model_arn],
            actions=['bedrock:InvokeModel', 'lambda:InvokeFunction']))
        agent_role.add_to_policy(iam.PolicyStatement(
            sid='RetrieveKBStatement',
            effect=iam.Effect.ALLOW,
            resources=[
                knowledge_base.attr_knowledge_base_arn],
            actions=['bedrock:Retrieve']))
        # Create the lambda function for the Agent Action Group
        action_group_function = lambda_.Function(
            self, "BedrockAgentActionGroupExecutor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            code=lambda_.Code.from_asset(
                'lambda/actiongroup'),
            handler='lambda_function.lambda_handler',
            timeout=Duration.seconds(300)
        )
        action_group_function.add_to_role_policy(iam.PolicyStatement(
            sid="UpdateDynamoDB",
            effect=iam.Effect.ALLOW,
            resources=[
                dynamodbable.table_arn],
            actions=['dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:DeleteItem']))

        # Create the Agent
        cfn_agent = bedrock.CfnAgent(
            self, "CfnAgent",
            agent_name=agent_name,
            agent_resource_role_arn=agent_role.role_arn,
            auto_prepare=True,
            description=agent_description,
            foundation_model=agent_model_id,
            instruction=agent_instruction,
            idle_session_ttl_in_seconds=1800,
            knowledge_bases=[{'description': knowledge_base_description,
                              'knowledgeBaseId': knowledge_base.attr_knowledge_base_id}],

            action_groups=[bedrock.CfnAgent.AgentActionGroupProperty(
                action_group_name=agent_action_group_name,
                description=agent_action_group_description,

                # the properties below are optional
                action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                    lambda_=action_group_function.function_arn
                ),

                function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                    functions=[bedrock.CfnAgent.FunctionProperty(
                        name=config['func_getbooking_name'],
                        # the properties below are optional
                        description=config['func_getbooking_description'],
                        parameters={
                            config['func_getbooking_id']: bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="The ID of the booking to retrieve",
                                required=True
                            )
                        }
                    ),
                        # create_booking
                        bedrock.CfnAgent.FunctionProperty(
                        name=config['func_createbooking_name'],
                        # the properties below are optional
                        description=config['func_createbooking_description'],
                        parameters={
                            config['func_createbooking_date']: bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="The date of the booking",
                                required=True
                            ),
                            config['func_createbooking_person_name']: bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="The name of the booking",
                                required=True
                            ),
                            config['func_createbooking_hour']: bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="The hour of the booking",
                                required=True
                            ),
                            config['func_createbooking_num_guests']: bedrock.CfnAgent.ParameterDetailProperty(
                                type="integer",

                                # the properties below are optional
                                description="The number of guests in the booking",
                                required=True
                            )}
                    ),
                        # delete_booking
                        bedrock.CfnAgent.FunctionProperty(
                        name=config['func_deletebooking_name'],
                        # the properties below are optional
                        description=config['func_deletebooking_description'],
                        parameters={
                            config['func_deletebooking_id']: bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",

                                # the properties below are optional
                                description="The ID of the booking to delete",
                                required=True
                            )
                        })
                    ]
                ),
            )])

        cfn_agent_alias = bedrock.CfnAgentAlias(
            self, "MyCfnAgentAlias",
            agent_alias_name=agent_alias_name,
            agent_id=cfn_agent.attr_agent_id)

        lambda_.CfnPermission(
            self,
            "BedrockInvocationPermission",
            action="lambda:InvokeFunction",
            function_name=action_group_function.function_name,
            principal="bedrock.amazonaws.com",
            source_arn=cfn_agent.attr_agent_arn
        )

        # Agent is created with booking-agent-alias and prepared, so it shoudld be ready to test #

        # Declare the stack outputs
        CfnOutput(scope=self, id='S3_bucket', value=s3Bucket.bucket_name)
        CfnOutput(scope=self, id='Datasource_id',
                  value=datasource.attr_data_source_id)
        CfnOutput(scope=self, id='Knowedgebase_name',
                  value=knowledge_base.name)
        CfnOutput(scope=self, id='Knowedgebase_id',
                  value=knowledge_base.attr_knowledge_base_id)
        CfnOutput(scope=self, id='Agent_name', value=cfn_agent.agent_name)
        CfnOutput(scope=self, id='Agent_id', value=cfn_agent.attr_agent_id)
