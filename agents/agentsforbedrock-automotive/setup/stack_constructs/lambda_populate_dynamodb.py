from constructs import Construct
from aws_cdk import (
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    CustomResource,
    Duration
)
from typing import Optional, List

class LambdaPopulateDynamoDB(Construct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            s3_bucket: str,
            role: str,
            dependencies: list = []
    ) -> None:
        super().__init__(scope, id)

        self.id = id
        self.s3_bucket = s3_bucket
        self.role = role
        self.dependencies = dependencies

    def build(
            self,
            function_name: str,
            code_dir: str,
            environments: dict
    ):
        fn = lambda_.Function(
            self,
            id=f"{self.id}_{function_name}_function",
            function_name=f"{self.id}_{function_name}_function",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(code_dir),
            timeout=Duration.seconds(300),
            memory_size=512,
            environment=environments,
            role=iam.Role.from_role_name(self, f"{self.id}_{function_name}_role", self.role)
        )

        custom = CustomResource(
            self,
            id=f"{self.id}_{function_name}_custom_resource",
            service_token=fn.function_arn,
            properties=environments
        )

        for el in self.dependencies:
            fn.node.add_dependency(el)

        for el in self.dependencies:
            custom.node.add_dependency(el)
