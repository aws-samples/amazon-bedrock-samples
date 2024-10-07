from constructs import Construct

import aws_cdk as core
from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_lambda as _lambda,
    aws_sns_subscriptions as subs,
    aws_logs as logs,
    aws_ssm as ssm,
    aws_cloudformation as cfn
)
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import (
  ManagedPolicy,
  Role,
  ServicePrincipal,
)
from aws_cdk.aws_lambda import (
  Code,
  Function,
  Runtime,
  Tracing,
)
from aws_cdk.aws_logs import RetentionDays, LogGroup
from aws_cdk.aws_opensearchserverless import (
  CfnAccessPolicy,
  CfnCollection,
  CfnSecurityPolicy,
)

from aws_cdk import (
  custom_resources,
  Duration,
  RemovalPolicy,
)
from config import EnvSettings, KbConfig, OpenSearchServerlessConfig

region = EnvSettings.ACCOUNT_REGION
account_id = EnvSettings.ACCOUNT_ID
kb_role_name = KbConfig.KB_ROLE_NAME

import json 
collectionName= OpenSearchServerlessConfig.COLLECTION_NAME
indexName= OpenSearchServerlessConfig.INDEX_NAME
embeddingModelId= KbConfig.EMBEDDING_MODEL_ID


class SecurityPolicyType(str):
  ENCRYPTION = "encryption"
  NETWORK = "network"

class StandByReplicas(str):
  ENABLED = "ENABLED"
  DISABLED = "DISABLED"

class CollectionType(str):
  VECTORSEARCH = "VECTORSEARCH"
  SEARCH = "SEARCH"
  TIMESERIES = "TIMESERIES"

class AccessPolicyType(str):
  DATA = "data"

  
class OpenSearchServerlessInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str)-> None:
        super().__init__(scope, construct_id)

        # The code that defines your stack goes here
        self.encryptionPolicy = self.create_encryption_policy()
        self.networkPolicy = self.create_network_policy()
        self.dataAccessPolicy = self.create_data_access_policy()
        self.collection = self.create_collection()

        # Create all policies before creating the collection
        self.networkPolicy.node.add_dependency(self.encryptionPolicy)
        self.dataAccessPolicy.node.add_dependency(self.networkPolicy)
        self.collection.node.add_dependency(self.encryptionPolicy)

        # # create an SSM parameters which store export values
        ssm.StringParameter(self, 'collectionArn',
                            parameter_name="/e2e-rag/collectionArn",
                            string_value=self.collection.attr_arn)

        self.create_oss_index()

    def create_encryption_policy(self) -> CfnSecurityPolicy:
      return CfnSecurityPolicy(
          self, 
          "EncryptionPolicy",
          name=f"{collectionName}-enc",
          type=SecurityPolicyType.ENCRYPTION,
          policy=json.dumps({"Rules": [{"ResourceType": "collection", "Resource": [f"collection/{collectionName}"]}], "AWSOwnedKey": True}),
      )
    
    def create_network_policy(self) -> CfnSecurityPolicy:
      return CfnSecurityPolicy(
          self,
          "NetworkPolicy",
          name=f"{collectionName}-net",
          type=SecurityPolicyType.NETWORK,
          policy=json.dumps([
              {
                  "Description": "Public access for ct-kb-aoss-collection collection",
                  "Rules": [
                      {"ResourceType": "dashboard", "Resource": [f"collection/{collectionName}"]},
                      {"ResourceType": "collection", "Resource": [f"collection/{collectionName}"]},
                  ],
                  "AllowFromPublic": True,
              }
          ]),
      )

    def create_collection(self) -> CfnCollection:
      return CfnCollection(
          self,
          "Collection",
          name=collectionName,
          description=f"{collectionName}-e2eRAG-collection",
        #   standbyReplicas=StandByReplicas.DISABLED,
          type=CollectionType.VECTORSEARCH,
      )

    def create_data_access_policy(self) -> CfnAccessPolicy:
      kbRoleArn = ssm.StringParameter.from_string_parameter_attributes(self, "kbRoleArn",
                        parameter_name="/e2e-rag/kbRoleArn").string_value
      return CfnAccessPolicy(
          self,
          "DataAccessPolicy",
          name=f"{collectionName}-access",
          type=AccessPolicyType.DATA,
          policy=json.dumps([
              {
                  "Rules": [
                      {
                          "Resource": [f"collection/{collectionName}"],
                          "Permission": [
                              "aoss:CreateCollectionItems",
                              "aoss:UpdateCollectionItems",
                              "aoss:DescribeCollectionItems",
                          ],
                          "ResourceType": "collection",
                      },
                      {
                          "ResourceType": "index",
                          "Resource": [f"index/{collectionName}/*"],
                          "Permission": [
                              "aoss:CreateIndex",
                              "aoss:DescribeIndex",
                              "aoss:ReadDocument",
                              "aoss:WriteDocument",
                              "aoss:UpdateIndex",
                              "aoss:DeleteIndex",
                          ],
                      },
                  ],
                  "Principal": [kbRoleArn],
              }
          ]),
      )

    def create_oss_index(self):
      # dependency layer (includes requests, requests-aws4auth,opensearch-py, aws-lambda-powertools)
      dependency_layer = _lambda.LayerVersion(self, 'dependency_layer',
                                          code=_lambda.Code.from_asset('resources/dependency_layer.zip'),
                                          compatible_runtimes=[_lambda.Runtime.PYTHON_3_8,_lambda.Runtime.PYTHON_3_9,_lambda.Runtime.PYTHON_3_10],
                                          license='Apache-2.0',
                                          description='dependency_layer including requests, requests-aws4auth, aws-lambda-powertools, opensearch-py')
      
      oss_lambda_role = iam.Role(
              self,
              "OSSLambdaRole",
              assumed_by=ServicePrincipal("lambda.amazonaws.com"),
          )
      
      oss_lambda_role.add_to_policy(iam.PolicyStatement(actions=[
        "aoss:APIAccessAll",
        "aoss:List*",
        "aoss:Get*",
        "aoss:Create*",
        "aoss:Update*",
        "aoss:Delete*"
      ],
      resources=["*"]))

      oss_index_creation_lambda = _lambda.Function(
          self,
          "BKB-OSS-InfraSetupLambda",
          function_name=f"BKB-OSS-{indexName}-InfraSetupLambda",
          code=Code.from_asset("src/amazon_bedrock_knowledge_base_infra_setup_lambda"),
          handler="oss_handler.lambda_handler",
          role=oss_lambda_role,
          memory_size=1024,
          timeout=Duration.minutes(14),
          runtime=Runtime.PYTHON_3_8,
          tracing=Tracing.ACTIVE,
          current_version_options={"removal_policy": RemovalPolicy.DESTROY},
          layers = [dependency_layer],
          environment={
              "POWERTOOLS_SERVICE_NAME": "InfraSetupLambda",
              "POWERTOOLS_METRICS_NAMESPACE": "InfraSetupLambda-NameSpace",
              "POWERTOOLS_LOG_LEVEL": "INFO",
          },
      )

      # Create a custom resource provider which wraps around the lambda above

      oss_provider_role = iam.Role(
              self,
              "OSSProviderRole",
              assumed_by=ServicePrincipal("lambda.amazonaws.com"),
          )
      oss_provider_role.add_to_policy(iam.PolicyStatement(actions=[
        "aoss:APIAccessAll",
        "aoss:List*",
        "aoss:Get*",
        "aoss:Create*",
        "aoss:Update*",
        "aoss:Delete*"
      ],
      resources=["*"]))
      
      oss_index_creation_provider  = cr.Provider(self, 'OSSProvider',
            on_event_handler=oss_index_creation_lambda,
            log_group=LogGroup(self, 
                          'OSSIndexCreationProviderLogs',
                          retention=RetentionDays.ONE_DAY),
            role=oss_provider_role,
        )
      
      # Create a new custom resource consumer
      index_creation_custom_resource = core.CustomResource(self, "OSSIndexCreationCustomResource",
            service_token=oss_index_creation_provider.service_token,
            properties={
                "collection_endpoint": self.collection.attr_collection_endpoint,
                "data_access_policy_name": self.dataAccessPolicy.name,
                "index_name": indexName,
                "embedding_model_id": embeddingModelId,
            }
        )
      
      index_creation_custom_resource.node.add_dependency(oss_index_creation_provider)