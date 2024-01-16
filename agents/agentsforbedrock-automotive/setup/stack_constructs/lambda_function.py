from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    Duration,
)

class LambdaFunction(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        role: str,
        provisioned_concurrency: int = None,
        dependencies: list = []
    ):
        super().__init__(scope, id)

        self.id = id
        self.role = role
        self.provisioned_concurrency = provisioned_concurrency
        self.dependencies = dependencies

    def build(
            self,
            function_name: str,
            code_dir: str,
            environment: dict,
            memory: int,
            timeout: int,
            vpc: ec2.Vpc = [],
            subnets: list = [],
            security_groups: list = [],
            layers: list = []
    ):
        if vpc is not None and len(subnets) > 0 and len(security_groups) > 0:
            fn = lambda_.Function(
                self,
                id=f"{self.id}_{function_name}_function",
                function_name=function_name,
                runtime=lambda_.Runtime.PYTHON_3_10,
                handler="index.lambda_handler",
                code=lambda_.Code.from_asset(code_dir),
                timeout=Duration.seconds(timeout),
                memory_size=memory,
                environment=environment,
                layers=layers,
                role=iam.Role.from_role_name(self, f"{self.id}_{function_name}_role", self.role),
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnets=subnets),
                security_groups=security_groups
            )
        else:
            fn = lambda_.Function(
                self,
                id=f"{self.id}_{function_name}_function",
                function_name=function_name,
                runtime=lambda_.Runtime.PYTHON_3_10,
                handler="index.lambda_handler",
                code=lambda_.Code.from_asset(code_dir),
                timeout=Duration.seconds(timeout),
                memory_size=memory,
                environment=environment,
                layers=layers,
                role=iam.Role.from_role_name(self, f"{self.id}_{function_name}_role", self.role)
            )

        for el in self.dependencies:
            fn.node.add_dependency(el)

        return fn