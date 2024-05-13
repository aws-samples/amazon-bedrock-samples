from constructs import Construct

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_lambda as _lambda,
    aws_sns_subscriptions as subs,
    aws_logs as logs,
    aws_ssm as ssm
)

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
import json

# set the variables
region = EnvSettings.ACCOUNT_REGION
account_id = EnvSettings.ACCOUNT_ID
proj_name = EnvSettings.RAG_PROJ_NAME

kb_role_name = KbConfig.KB_ROLE_NAME
kbRoleArn= KbConfig.KB_ROLE_ARN
embeddingModelId= KbConfig.EMBEDDING_MODEL_ID

collectionName= OpenSearchServerlessConfig.COLLECTION_NAME
collectionDescription= "test bedrock KB cdk"
indexName= OpenSearchServerlessConfig.INDEX_NAME

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

  
class OpenSearchServerlessStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        self.encryptionPolicy = self.create_encryption_policy()
        self.networkPolicy = self.create_network_policy()
        self.dataAccessPolicy = self.create_data_access_policy()
        self.collection = self.create_collection()

        # Create all policies before creating the collection
        self.networkPolicy.node.add_dependency(self.encryptionPolicy)
        self.dataAccessPolicy.node.add_dependency(self.networkPolicy)
        self.collection.node.add_dependency(self.encryptionPolicy)

        self.create_oss_index()

        # create an SSM parameters which store export values
        ssm.StringParameter(self, 'collectionArn',
                            parameter_name="/e2e-rag/collectionArn",
                            string_value=self.collection.attr_arn)

        # # Export the output of the resource you want to store in a variable
        # cdk.CfnOutput(self, "kbRoleArn", value=kbRoleArn)
        # cdk.CfnOutput(self, "collectionName", value=collectionName)
        # cdk.CfnOutput(self, "collectionArn", value=self.collection.attr_arn)
        # cdk.CfnOutput(self, "indexName", value=indexName)

       

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
          description=collectionDescription,
        #   standbyReplicas=StandByReplicas.DISABLED,
          type=CollectionType.VECTORSEARCH,
      )

    def create_data_access_policy(self) -> CfnAccessPolicy:
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
      powertools_layer = _lambda.LayerVersion.from_layer_version_arn(self, "powertools",
                                                    f"arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:68")
    
      # opensearchpy layer (includes requests, requests-aws4auth,opensearch-py and boto3-1.34.82)
      opensearchpy_layer = _lambda.LayerVersion(self, 'opensearchpy',
                                          code=_lambda.Code.from_asset('src/opensearchpylayer'),
                                          compatible_runtimes=[_lambda.Runtime.PYTHON_3_8,_lambda.Runtime.PYTHON_3_9,_lambda.Runtime.PYTHON_3_10],
                                          license='Apache-2.0',
                                          description='opensearchpy layer including requests, requests-aws4auth, and boto3-1.34.82')
      
      oss_index_creation_lambda = _lambda.Function(
          self,
          "BKB-OSS-InfraSetupLambda",
          function_name=f"{proj_name}-BKB-OSS-InfraSetupLambda",
          code=Code.from_asset("src"),
          handler="oss_handler.lambda_handler",
          role=iam.Role(
              self,
              "OSSLambdaRole",
              assumed_by=ServicePrincipal("lambda.amazonaws.com"),
              managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")],
          ),
          memory_size=1024,
          timeout=Duration.minutes(14),
          runtime=Runtime.PYTHON_3_8,
          tracing=Tracing.ACTIVE,
          current_version_options={"removal_policy": RemovalPolicy.DESTROY},
          layers = [powertools_layer,opensearchpy_layer],
          environment={
              "POWERTOOLS_SERVICE_NAME": "InfraSetupLambda",
              "POWERTOOLS_METRICS_NAMESPACE": "InfraSetupLambda-NameSpace",
              "POWERTOOLS_LOG_LEVEL": "INFO",
          },
      )

      oss_index_creation_provider = custom_resources.Provider(
          self,
          "OSSIndexCreationProvider",
          on_event_handler=oss_index_creation_lambda,
          # log_group=logs.LogGroup(self, "OSSIndexCreationProviderLogs", retention=logs.RetentionDays.ONE_DAY),
          role=iam.Role(
              self,
              "OSSProviderRole",
              assumed_by=ServicePrincipal("lambda.amazonaws.com"),
              managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")],
          ),
      )

      index_creation_custom_resource = cdk.CustomResource(
          self,
          "OSSIndexCreationCustomResource",
          service_token=oss_index_creation_provider.service_token,
          properties={
              "collection_endpoint": self.collection.attr_collection_endpoint,
              "data_access_policy_name": self.dataAccessPolicy.name,
              "index_name": indexName,
              "embedding_model_id": embeddingModelId,
          },
      )
      index_creation_custom_resource.node.add_dependency(oss_index_creation_provider)

      

