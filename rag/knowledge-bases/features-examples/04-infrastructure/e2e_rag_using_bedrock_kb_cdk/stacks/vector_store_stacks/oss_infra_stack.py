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
from aws_cdk import custom_resources 

from aws_cdk.aws_opensearchserverless import (
  CfnAccessPolicy,
  CfnCollection,
  CfnSecurityPolicy,
)
from aws_cdk import aws_opensearchserverless as opensearchserverless

from config import EnvSettings, KbConfig, OpenSearchServerlessConfig

region = EnvSettings.ACCOUNT_REGION
account_id = EnvSettings.ACCOUNT_ID
kb_role_name = KbConfig.KB_ROLE_NAME

import json 
collectionName= OpenSearchServerlessConfig.COLLECTION_NAME
indexName= OpenSearchServerlessConfig.INDEX_NAME
embeddingModelId= KbConfig.EMBEDDING_MODEL_ID
indexMapping = OpenSearchServerlessConfig.INDEX_MAPPING


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
    def __init__(self, scope: Construct, construct_id: str)-> None:
        super().__init__(scope, construct_id)

        # Create policies and collection
        self.encryptionPolicy = self.create_encryption_policy()
        self.networkPolicy = self.create_network_policy()
        self.collection = self.create_collection()
        
        # Wait for encryption and network policies to be created
        self.networkPolicy.node.add_dependency(self.encryptionPolicy)
        self.collection.node.add_dependency(self.networkPolicy)

        # Create data access policy after collection is created
        self.dataAccessPolicy = self.create_data_access_policy()
        self.dataAccessPolicy.node.add_dependency(self.collection)

        # Store collection ARN in SSM
        self.collection_arn_param = ssm.StringParameter(
            self, 
            'collectionArn',
            parameter_name="/e2e-rag/collectionArn",
            string_value=self.collection.attr_arn
        )

        # Create index after all other resources
        self.create_oss_index()

    def create_encryption_policy(self) -> CfnSecurityPolicy:
        return CfnSecurityPolicy(
            self, 
            "EncryptionPolicy",
            name=f"{collectionName}-enc",
            type=SecurityPolicyType.ENCRYPTION,
            policy=json.dumps({
                "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{collectionName}"]}],
                "AWSOwnedKey": True
            }),
        )
    
    def create_network_policy(self) -> CfnSecurityPolicy:
        return CfnSecurityPolicy(
            self,
            "NetworkPolicy",
            name=f"{collectionName}-net",
            type=SecurityPolicyType.NETWORK,
            policy=json.dumps([{
                "Description": f"Public access for {collectionName} collection",
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/{collectionName}"]},
                    {"ResourceType": "dashboard", "Resource": [f"collection/{collectionName}"]}
                ],
                "AllowFromPublic": True
            }]),
        )

    def create_collection(self) -> CfnCollection:
        return CfnCollection(
            self,
            "Collection",
            name=collectionName,
            description=f"{collectionName}-e2eRAG-collection",
            type=CollectionType.VECTORSEARCH,
        )

    def create_data_access_policy(self) -> CfnAccessPolicy:
      kbRoleArn = ssm.StringParameter.from_string_parameter_attributes(
          self, 
          "kbRoleArn",
          parameter_name="/e2e-rag/kbRoleArn"
      ).string_value
      
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
                              "aoss:DeleteCollectionItems",
                              "aoss:UpdateCollectionItems",
                              "aoss:DescribeCollectionItems",
                              "aoss:*"
                          ],
                          "ResourceType": "collection"
                      },
                      {
                          "Resource": [f"index/{collectionName}/*"],
                          "Permission": [
                              "aoss:ReadDocument",
                              "aoss:WriteDocument",
                              "aoss:CreateIndex",
                              "aoss:DeleteIndex",
                              "aoss:UpdateIndex",
                              "aoss:DescribeIndex",
                              "aoss:*"
                          ],
                          "ResourceType": "index"
                      }
                  ],
                  "Principal": [
                      kbRoleArn,
                      f"arn:aws:iam::{account_id}:root"
                  ]
              }
          ]),
      )


    def create_oss_index(self):
        # Add a wait condition to ensure collection is active
        wait_condition = custom_resources.AwsCustomResource(
            self,
            "WaitForCollection",
            on_create=custom_resources.AwsSdkCall(
                service="OpenSearchServerless",
                action="listCollections",
                parameters={},
                physical_resource_id=custom_resources.PhysicalResourceId.of("WaitForCollection")
            ),
            policy=custom_resources.AwsCustomResourcePolicy.from_sdk_calls(
                resources=custom_resources.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )
        wait_condition.node.add_dependency(self.collection)
        wait_condition.node.add_dependency(self.dataAccessPolicy)

        base_mapping = indexMapping
        cdk_mapping = {
            "mappings": opensearchserverless.CfnIndex.MappingsProperty(
                properties={
                    "bedrock-knowledge-base-default-vector": opensearchserverless.CfnIndex.PropertyMappingProperty(
                        type=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["type"],
                        dimension=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["dimension"],
                        method=opensearchserverless.CfnIndex.MethodProperty(
                            engine=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["method"]["engine"],
                            name=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["method"]["name"],
                            parameters=opensearchserverless.CfnIndex.ParametersProperty(
                                ef_construction=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["method"]["parameters"]["ef_construction"],
                                m=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["method"]["parameters"]["m"]
                            ),
                            space_type=base_mapping["mappings"]["properties"]["bedrock-knowledge-base-default-vector"]["method"]["space_type"]
                        )
                    ),
                    "AMAZON_BEDROCK_METADATA": opensearchserverless.CfnIndex.PropertyMappingProperty(
                        type=base_mapping["mappings"]["properties"]["AMAZON_BEDROCK_METADATA"]["type"],
                        index=base_mapping["mappings"]["properties"]["AMAZON_BEDROCK_METADATA"]["index"]
                    ),
                    "AMAZON_BEDROCK_TEXT_CHUNK": opensearchserverless.CfnIndex.PropertyMappingProperty(
                        type=base_mapping["mappings"]["properties"]["AMAZON_BEDROCK_TEXT_CHUNK"]["type"],
                        index=base_mapping["mappings"]["properties"]["AMAZON_BEDROCK_TEXT_CHUNK"]["index"]
                    )
                }
            ),
            "settings": opensearchserverless.CfnIndex.IndexSettingsProperty(
                index=opensearchserverless.CfnIndex.IndexProperty(
                    knn=base_mapping["settings"]["index"]["knn"],
                    knn_algo_param_ef_search=base_mapping["settings"]["index"]["knn.algo_param.ef_search"]
                )
            )
        }
        
        oss_index = opensearchserverless.CfnIndex(
            self,
            'OSSCfnIndex',
            collection_endpoint=self.collection.attr_collection_endpoint,
            index_name=indexName,
            mappings=cdk_mapping["mappings"],
            settings=cdk_mapping["settings"]
        )
        oss_index.node.add_dependency(self.dataAccessPolicy)
        oss_index.node.add_dependency(self.collection)
