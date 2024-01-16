from constructs import Construct
from aws_cdk import (
    aws_iam as iam
)

class IAMLambda(Construct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            dependencies: list = []
    ):
        super().__init__(scope, id)

        self.id = id
        self.dependencies = dependencies

    def build(self):
        # ==================================================
        # ================= IAM ROLE =======================
        # ==================================================
        role = iam.Role(
            self,
            id=f"{self.id}_role",
            assumed_by=iam.ServicePrincipal(service="lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
            ],
        )

        s3_policy = iam.Policy(
            scope=self,
            id=f"{self.id}_policy_s3",
            policy_name="S3Policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:PutObject',
                        's3:DeleteObject',
                        's3:ListBucket'
                    ],
                    resources=["*"],
                )
            ],
        )

        dynamodb_policy = iam.Policy(
            scope=self,
            id=f"{self.id}_policy_dynamodb",
            policy_name="DynamoDBPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:BatchGetItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query"

                    ],
                    resources=["*"],
                )
            ],
        )

        dynamodb_policy.attach_to_role(role)
        s3_policy.attach_to_role(role)

        for el in self.dependencies:
            role.node.add_dependency(el)

        return role
