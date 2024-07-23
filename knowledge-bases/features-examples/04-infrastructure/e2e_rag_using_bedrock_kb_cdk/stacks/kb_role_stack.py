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

class KbRoleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Create KB Role
        self.kbrole = iam.Role(
          self,
          "KB_Role",
          role_name=kb_role_name,
          assumed_by=iam.ServicePrincipal(
              "bedrock.amazonaws.com",
              conditions={
                  "StringEquals": {"aws:SourceAccount": account_id},
                  "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/*"},
              },
          ),
          inline_policies={
              "FoundationModelPolicy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="BedrockInvokeModelStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["bedrock:InvokeModel"],
                          resources=[f"arn:aws:bedrock:{region}::foundation-model/*"],
                      )
                  ]
              ),
              "OSSPolicy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="OpenSearchServerlessAPIAccessAllStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["aoss:APIAccessAll"],
                          resources=[f"arn:aws:aoss:{region}:{account_id}:collection/*"],
                      )
                  ]
              ),
              "S3Policy": iam.PolicyDocument(
                  statements=[
                      iam.PolicyStatement(
                          sid="S3ListBucketStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["s3:ListBucket"],
                          resources=[f"arn:aws:s3:::{bucket_name}"],
                      ),
                      iam.PolicyStatement(
                          sid="S3GetObjectStatement",
                          effect=iam.Effect.ALLOW,
                          actions=["s3:GetObject"],
                          resources=[f"arn:aws:s3:::{bucket_name}/*"],
                      ),
                  ]
              ),
              
          },
        )
        
        # create an SSM parameters which store export values
        ssm.StringParameter(self, 'kbRoleArn',
                            parameter_name="/e2e-rag/kbRoleArn",
                            string_value=self.kbrole.role_arn)
       