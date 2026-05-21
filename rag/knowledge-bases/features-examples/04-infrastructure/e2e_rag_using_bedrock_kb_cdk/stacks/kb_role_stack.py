from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_ssm as ssm
)
import aws_cdk as cdk
from config import EnvSettings, KbConfig, DsConfig

region = EnvSettings.ACCOUNT_REGION
account_id = EnvSettings.ACCOUNT_ID
kb_role_name = KbConfig.KB_ROLE_NAME
bucket_name = DsConfig.S3_BUCKET_NAME
interim_bucket_name = DsConfig.MM_STORAGE_S3
multi_modal = bool(KbConfig.MULTI_MODAL and KbConfig.OVERLAP_PERCENTAGE)

class KbRoleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the partition dynamically - will be 'aws-us-gov' in GovCloud
        partition = Stack.of(self).partition

        # Create KB Role with partition-aware ARNs
        self.kbrole = iam.Role(
          self,
          "KB_Role",
          role_name=kb_role_name,
          assumed_by=iam.ServicePrincipal(
              "bedrock.amazonaws.com",
              conditions={
                  "StringEquals": {"aws:SourceAccount": account_id},
                  "ArnLike": {
                      "aws:SourceArn": f"arn:{partition}:bedrock:{region}:{account_id}:knowledge-base/*"
                  },
              },
          ),
          inline_policies={
              "FoundationModelPolicy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="BedrockInvokeModelStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["bedrock:InvokeModel"],
                          resources=[f"arn:{partition}:bedrock:{region}::foundation-model/*"],
                      )
                  ]
              ),
              "OSSPolicy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="OpenSearchServerlessAPIAccessAllStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["aoss:APIAccessAll"],
                          resources=[f"arn:{partition}:aoss:{region}:{account_id}:collection/*"],
                      )
                  ]
              ),
              "S3Policy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="S3ListBucketStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["s3:ListBucket"],
                          resources=[f"arn:{partition}:s3:::{bucket_name}", f"arn:{partition}:s3:::{interim_bucket_name}"],
                      ),
                      iam.PolicyStatement(
                          sid="S3GetObjectStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["s3:GetObject"],
                          resources=[f"arn:{partition}:s3:::{bucket_name}", f"arn:{partition}:s3:::{bucket_name}/*", f"arn:{partition}:s3:::{interim_bucket_name}", f"arn:{partition}:s3:::{interim_bucket_name}/*" ],
                      ),
                       iam.PolicyStatement(
                          sid="S3PutObjectStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["s3:PutObject"],
                          resources=[f"arn:{partition}:s3:::{interim_bucket_name}/*" ],
                      ),
                      iam.PolicyStatement(
                          sid="S3DeleteObjectStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["s3:DeleteObject"],
                          resources=[f"arn:{partition}:s3:::{interim_bucket_name}/*" ],
                      ),
                  ]
              ),
            
              "BDAPolicy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="BDAGetStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["bedrock:GetDataAutomationStatus"],
                          resources=[f"arn:{partition}:bedrock:{region}:{account_id}:data-automation-invocation/*"]
                      ),
                      iam.PolicyStatement(
                          sid="BDAInvokeStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["bedrock:InvokeDataAutomationAsync"],
                          resources=[f"arn:{partition}:bedrock:{region}:aws:data-automation-project/public-rag-default",
                                     f"arn:{partition}:bedrock:us-east-1:{account_id}:data-automation-profile/us.data-automation-v1",
                                     f"arn:{partition}:bedrock:us-east-2:{account_id}:data-automation-profile/us.data-automation-v1",
                                     f"arn:{partition}:bedrock:us-west-1:{account_id}:data-automation-profile/us.data-automation-v1",
                                     f"arn:{partition}:bedrock:us-west-2:{account_id}:data-automation-profile/us.data-automation-v1"]
                      ),
                  ]
              ),
              "RDSDataPolicy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="RDSDataPolicyStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["rds-data:ExecuteStatement"],
                          resources=["*"],
                      ),
                      iam.PolicyStatement(
                          sid="RDSPolicyStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["rds:*"],
                          resources=["*"],
                      ),
                      iam.PolicyStatement(
                          sid="SecretsPolicyStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["secretsmanager:*"],
                          resources=["*"],
                      ),
                  ]
              ),
          },
        )
        
        # Create an SSM parameter which stores export values
        ssm.StringParameter(self, 'kbRoleArn',
                          parameter_name="/e2e-rag/kbRoleArn",
                          string_value=self.kbrole.role_arn)
