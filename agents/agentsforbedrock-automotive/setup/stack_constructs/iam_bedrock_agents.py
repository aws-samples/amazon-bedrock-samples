from constructs import Construct
from aws_cdk import (
    aws_iam as iam
)

class IAMBedrockAgents(Construct):
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
            assumed_by=iam.ServicePrincipal(service="bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
            ],
            role_name=f"AmazonBedrockExecutionRoleForAgents_{self.id}"
        )

        bedrock_policy = iam.Policy(
            scope=self,
            id=f"{self.id}_policy_bedrock",
            policy_name="BedrockPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sts:AssumeRole"
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "bedrock:*",
                    ],
                    resources=["*"],
                )
            ],
        )

        bedrock_policy.attach_to_role(role)

        for el in self.dependencies:
            role.node.add_dependency(el)

        return role
