"""
CDK Stack for Bedrock Managed Knowledge Base with S3 data source.

Creates:
  - S3 bucket for documents
  - IAM execution role with S3, CloudWatch, and FM policies
  - Managed Knowledge Base (Type: MANAGED)
  - S3 Data Source (MANAGED_KNOWLEDGE_BASE_CONNECTOR)

No vector store infrastructure needed — Bedrock manages everything.
"""

import json
from constructs import Construct

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_iam as iam,
)
from aws_cdk.aws_bedrock import CfnKnowledgeBase, CfnDataSource

from config import EnvSettings, KbConfig, DsConfig

region = EnvSettings.ACCOUNT_REGION
account_id = EnvSettings.ACCOUNT_ID


class ManagedKbStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        partition = Stack.of(self).partition

        # ── S3 Bucket ─────────────────────────────────────────────────
        if DsConfig.S3_BUCKET_NAME:
            # Use existing bucket
            self.bucket = s3.Bucket.from_bucket_name(
                self, "DocsBucket", DsConfig.S3_BUCKET_NAME
            )
            bucket_name = DsConfig.S3_BUCKET_NAME
        else:
            # Create new bucket
            self.bucket = s3.Bucket(
                self,
                "DocsBucket",
                bucket_name=f"{EnvSettings.PROJECT_NAME}-docs-{account_id}-{region}",
                encryption=s3.BucketEncryption.S3_MANAGED,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=RemovalPolicy.RETAIN,
            )
            bucket_name = self.bucket.bucket_name

        # ── IAM Role ──────────────────────────────────────────────────
        self.kb_role = iam.Role(
            self,
            "KbExecutionRole",
            role_name=f"AmazonBedrockExecutionRoleForKB_{EnvSettings.PROJECT_NAME}",
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {
                        "AWS:SourceArn": f"arn:{partition}:bedrock:{region}:{account_id}:knowledge-base/*"
                    },
                },
            ),
            max_session_duration=cdk.Duration.hours(1),
        )

        # S3 access
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ListBucket",
                actions=["s3:ListBucket"],
                resources=[self.bucket.bucket_arn],
                conditions={"StringEquals": {"aws:ResourceAccount": [account_id]}},
            )
        )
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3GetObject",
                actions=["s3:GetObject"],
                resources=[f"{self.bucket.bucket_arn}/*"],
                conditions={"StringEquals": {"aws:ResourceAccount": [account_id]}},
            )
        )

        # CloudWatch metrics
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchWrite",
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {"cloudwatch:namespace": "AWS/Bedrock/KnowledgeBases"}
                },
            )
        )

        # Foundation model access (only for custom embedding)
        if KbConfig.EMBEDDING_MODEL_ID != "MANAGED":
            embedding_model_arn = (
                f"arn:{partition}:bedrock:{region}::foundation-model/{KbConfig.EMBEDDING_MODEL_ID}"
            )
            self.kb_role.add_to_policy(
                iam.PolicyStatement(
                    sid="InvokeModel",
                    actions=["bedrock:InvokeModel"],
                    resources=[embedding_model_arn],
                )
            )
            self.kb_role.add_to_policy(
                iam.PolicyStatement(
                    sid="ListModels",
                    actions=["bedrock:ListFoundationModels", "bedrock:ListCustomModels"],
                    resources=["*"],
                )
            )

        # ── Managed Knowledge Base ────────────────────────────────────
        # CDK requires embeddingModelArn in the typed property, but CFN allows
        # an empty ManagedKnowledgeBaseConfiguration for free managed embedding.
        # Use a placeholder and override to bypass CDK validation.
        if KbConfig.EMBEDDING_MODEL_ID == "MANAGED":
            placeholder_arn = f"arn:{partition}:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
            kb_config = CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="MANAGED",
                managed_knowledge_base_configuration=CfnKnowledgeBase.ManagedKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=placeholder_arn,
                ),
            )
        else:
            kb_config = CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="MANAGED",
                managed_knowledge_base_configuration=CfnKnowledgeBase.ManagedKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=embedding_model_arn,
                    embedding_model_configuration=CfnKnowledgeBase.EmbeddingModelConfigurationProperty(
                        bedrock_embedding_model_configuration=CfnKnowledgeBase.BedrockEmbeddingModelConfigurationProperty(
                            embedding_data_type="FLOAT32"
                        )
                    ),
                ),
            )

        self.knowledge_base = CfnKnowledgeBase(
            self,
            "ManagedKB",
            name=KbConfig.KB_NAME,
            description=KbConfig.KB_DESCRIPTION,
            role_arn=self.kb_role.role_arn,
            knowledge_base_configuration=kb_config,
        )
        self.knowledge_base.node.add_dependency(self.kb_role)

        # Override to remove the placeholder ARN — CFN accepts empty config for managed embedding
        if KbConfig.EMBEDDING_MODEL_ID == "MANAGED":
            self.knowledge_base.add_property_override(
                "KnowledgeBaseConfiguration.ManagedKnowledgeBaseConfiguration.EmbeddingModelArn", None
            )
            self.knowledge_base.add_deletion_override(
                "KnowledgeBaseConfiguration.ManagedKnowledgeBaseConfiguration.EmbeddingModelArn"
            )

        # ── S3 Data Source (Managed KB Connector) ─────────────────────
        # CDK doesn't have typed properties for MANAGED_KNOWLEDGE_BASE_CONNECTOR yet.
        # We create the resource with a minimal config and override the properties.
        self.data_source = CfnDataSource(
            self,
            "S3DataSource",
            name=f"{EnvSettings.PROJECT_NAME}-s3-source",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            data_source_configuration={"type": "MANAGED_KNOWLEDGE_BASE_CONNECTOR"},
            vector_ingestion_configuration=self._build_vector_ingestion_config(),
        )

        # Override with the full connector config (camelCase for free-form connectorParameters)
        self.data_source.add_property_override(
            "DataSourceConfiguration.ManagedKnowledgeBaseConnectorConfiguration",
            {
                "ConnectorParameters": {
                    "type": "S3",
                    "version": "1",
                    "connectionConfiguration": {
                        "bucketName": bucket_name,
                        "bucketOwnerAccountId": account_id,
                    },
                    "filterConfiguration": {
                        "inclusionPrefixes": [DsConfig.S3_PREFIX]
                    },
                    "deletionProtectionConfiguration": {
                        "enableDeletionProtection": False
                    },
                },
                "DeletionProtectionConfiguration": {
                    "DeletionProtectionStatus": "DISABLED"
                },
            },
        )

        # ── Outputs ───────────────────────────────────────────────────
        CfnOutput(self, "KnowledgeBaseId",
                  value=self.knowledge_base.attr_knowledge_base_id,
                  description="Managed Knowledge Base ID")

        CfnOutput(self, "DataSourceId",
                  value=self.data_source.attr_data_source_id,
                  description="S3 Data Source ID")

        CfnOutput(self, "S3BucketName",
                  value=bucket_name,
                  description="S3 bucket for documents")

        CfnOutput(self, "UploadPath",
                  value=f"s3://{bucket_name}/{DsConfig.S3_PREFIX}",
                  description="Upload documents here")

        CfnOutput(self, "NextSteps", value=(
            f"1. Upload docs: aws s3 cp file.pdf s3://{bucket_name}/{DsConfig.S3_PREFIX}\n"
            f"2. Ingest: aws bedrock-agent start-ingestion-job "
            f"--knowledge-base-id <KB_ID> --data-source-id <DS_ID>"
        ))

    def _build_vector_ingestion_config(self):
        """Build the VectorIngestionConfiguration based on chunking strategy."""
        strategy = KbConfig.CHUNKING_STRATEGY

        if strategy == "FIXED_SIZE":
            return {
                "chunkingConfiguration": {
                    "chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {
                        "maxTokens": KbConfig.MAX_TOKENS,
                        "overlapPercentage": KbConfig.OVERLAP_PERCENTAGE,
                    },
                },
                "parsingConfiguration": {"parsingStrategy": "SMART_PARSING"},
            }
        elif strategy == "NONE":
            return {
                "chunkingConfiguration": {"chunkingStrategy": "NONE"},
                "parsingConfiguration": {"parsingStrategy": "SMART_PARSING"},
            }
        else:
            # DEFAULT — let service handle chunking
            return {
                "parsingConfiguration": {"parsingStrategy": "SMART_PARSING"},
            }
