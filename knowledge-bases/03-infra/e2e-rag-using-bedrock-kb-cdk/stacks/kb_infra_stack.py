from constructs import Construct

import aws_cdk as core
from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_lambda as lambda_,
    aws_sns_subscriptions as subs,
    aws_logs as logs,
    aws_ssm as ssm,
    aws_events as events,
    # aws_bedrock as bedrock
)

from aws_cdk import aws_bedrock as bedrock

from aws_cdk.aws_bedrock import (
  CfnKnowledgeBase,
  CfnDataSource
)

from config import EnvSettings, KbConfig, DsConfig, OpenSearchServerlessConfig

region = EnvSettings.ACCOUNT_REGION
account_id = EnvSettings.ACCOUNT_ID

collectionName= OpenSearchServerlessConfig.COLLECTION_NAME
indexName= OpenSearchServerlessConfig.INDEX_NAME

import json 
embeddingModelId= KbConfig.EMBEDDING_MODEL_ID
max_tokens = KbConfig.MAX_TOKENS
overlap_percentage = KbConfig.OVERLAP_PERCENTAGE

embeddingModelArn = f"arn:aws:bedrock:{region}::foundation-model/{embeddingModelId}"
bucket = DsConfig.S3_BUCKET_NAME
s3_bucket_arn = f"arn:aws:s3:::{bucket}"

class KbInfraStack(Stack):

  def __init__(self, scope: Construct, construct_id: str)-> None:
      super().__init__(scope, construct_id)

      self.kbRoleArn = ssm.StringParameter.from_string_parameter_attributes(self, "kbRoleArn",
                        parameter_name="/e2e-rag/kbRoleArn").string_value
      print("kbRoleArn: " + self.kbRoleArn)
      self.collectionArn = ssm.StringParameter.from_string_parameter_attributes(self, "collectionArn",
                        parameter_name="/e2e-rag/collectionArn").string_value
      print("collectionArn: " + self.collectionArn)
    #   Create Knowledgebase
      self.knowledge_base = self.create_knowledge_base()
      self.data_source = self.create_data_source(self.knowledge_base)
    #   self.ingest_lambda =self.create_ingest_lambda(self.knowledge_base, self.data_source)
    #   self.add_eventbridge_rule(self, bucket, self.ingest_lambda)
    #   self.query_lambda=self.create_query_lambda(self.knowledge_base)
    
  def create_knowledge_base(self) -> CfnKnowledgeBase:
    return CfnKnowledgeBase(
        self, 
        'e2eRagKB',
        knowledge_base_configuration=CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
        type="VECTOR",
        vector_knowledge_base_configuration=CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
            embedding_model_arn=embeddingModelArn
        )
        ),
        name='docKnowledgeBase',
        role_arn=self.kbRoleArn,
        # the properties below are optional
        description='e2eRAG Knowledge base',
        storage_configuration=CfnKnowledgeBase.StorageConfigurationProperty(
          type="OPENSEARCH_SERVERLESS",
          # the properties below are optional
            opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                collection_arn=self.collectionArn,
                field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                    metadata_field="AMAZON_BEDROCK_METADATA",
                    text_field="AMAZON_BEDROCK_TEXT_CHUNK",
                    vector_field="bedrock-knowledge-base-default-vector"
                ),
                vector_index_name=indexName
            )
        )
      )
  
  def create_data_source(self, knowledge_base) -> CfnDataSource:
    kbid = knowledge_base.attr_knowledge_base_id
    return CfnDataSource(self, "e2eRagDataSource",
    data_source_configuration=CfnDataSource.DataSourceConfigurationProperty(
        s3_configuration=CfnDataSource.S3DataSourceConfigurationProperty(
            bucket_arn=s3_bucket_arn,

            # the properties below are optional
            # inclusion_prefixes=["inclusionPrefixes"]
        ),
        type="S3"
    ),
    knowledge_base_id= kbid,
    name="e2eRAGDataSource",

    # the properties below are optional
    description="e2eRAG DataSource",
    
    vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
        chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
            chunking_strategy="FIXED_SIZE",
            # the properties below are optional
            fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                max_tokens=max_tokens,
                overlap_percentage=overlap_percentage
            )
        )
    )
)
  
  def create_ingest_lambda(self, knowledge_base, data_source) -> lambda_:
    ingest_lambda= lambda_.Function(
        self,
        "IngestionJob",
        runtime=lambda_.Runtime.PYTHON_3_10,
        handler="ingestJobLambda.lambda_handler",
        code=lambda_.Code.from_asset("./src/IngestJob"),
        timeout=Duration.minutes(5),
        environment=dict(
            KNOWLEDGE_BASE_ID=knowledge_base.attr_knowledge_base_id,
            DATA_SOURCE_ID=data_source.attr_data_source_id,
        )
    )
    # lambda_ingestion_job.add_event_source(s3_put_event_source)

    ingest_lambda.add_to_role_policy(iam.PolicyStatement(
        actions=["bedrock:StartIngestionJob"],
        resources=[knowledge_base.knowledge_base_arn]
    ))
    return ingest_lambda

  def create_query_lambda(self, knowledge_base) -> lambda_:
    query_lambda = lambda_.Function(
        self, "Query",
        runtime=lambda_.Runtime.PYTHON_3_10,
        handler="queryKBLambda.handler",
        code=lambda_.Code.from_asset("./src/queryKnowledgeBase"),
        timeout=Duration.minutes(5),
        environment={
            "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id
        }
    )
    fn_url = query_lambda.add_function_url(
        auth_type=lambda_.FunctionUrlAuthType.NONE,
        invoke_mode=lambda_.InvokeMode.BUFFERED,
        cors={
            "allowed_origins": ["*"],
            "allowed_methods": [lambda_.HttpMethod.POST]
        }
    )

    query_lambda.add_to_role_policy(iam.PolicyStatement(
        actions=["bedrock:RetrieveAndGenerate",
                "bedrock:Retrieve",
                "bedrock:InvokeModel", ],
        resources=["*"]
    ))

    return query_lambda
  
  def add_eventbridge_rule(self, bucket, lambda_function):
    # Create an EventBridge rule.
    rule = events.Rule(self, "MyRule",
        event_pattern=events.EventPattern(
            source=["aws.s3"],
            detail_type=["Object Created"],
        )
    )
    # Add a target to the rule.
    rule.add_target(lambda_function)

    # Grant the Lambda function permission to access the S3 bucket.
    bucket.grant_read(lambda_function)