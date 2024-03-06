from aws_cdk import (
    App,
    CfnOutput,
    RemovalPolicy,
    Stack,
    Tags,
    aws_iam as iam,
    aws_s3,
    aws_s3_deployment as s3_deployment
)
from constructs import Construct
import json
import os
from stack_constructs.dynamodb import DynamoDB
from stack_constructs.iam_bedrock_agents import IAMBedrockAgents
from stack_constructs.iam_bedrock_kb import IAMBedrockKB
from stack_constructs.iam_lambda import IAMLambda
from stack_constructs.lambda_function import LambdaFunction
from stack_constructs.lambda_layer import LambdaLayer
from stack_constructs.lambda_populate_dynamodb import LambdaPopulateDynamoDB
import traceback

abs_path = os.path.abspath(__file__)
parent_dir = os.path.dirname(abs_path)
grandparent_dir = os.path.dirname(parent_dir)

def _load_configs(filename):
    """
    Loads config from file
    """

    with open(filename, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config

class BedrockAPIStack(Stack):
    def __init__(
            self, scope:
            Construct, id: str,
            config: dict,
            **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # ==================================================
        # ============== STATIC PARAMETERS =================
        # ==================================================
        self.id = id
        self.lambdas_directory = os.path.join(grandparent_dir, "lambdas")
        self.data_directory = os.path.join(grandparent_dir, "data")
        self.open_api_spec_directory = os.path.join(grandparent_dir, "open-api-spec")
        self.prefix_id = config.get("STACK_PREFIX", None)

        # ==================================================
        # ================= PARAMETERS =====================
        # ==================================================
        self.boto3_requirements = config.get("BOTO3_REQUIREMENTS", None)

        if self.prefix_id is None:
            raise Exception("STACK_PREFIX not defined")

    def build(self):
        # ==================================================
        # ================== IAM ROLE ======================
        # ==================================================
        iam_bedrock_kb = IAMBedrockKB(
            scope=self,
            id="iam_role_bedrock_kb"
        )

        iam_bedrock_kb_role = iam_bedrock_kb.build()

        iam_bedrock_agents = IAMBedrockAgents(
            scope=self,
            id="iam_role_bedrock_agents"
        )

        iam_bedrock_agents_role = iam_bedrock_agents.build()

        iam_lambda = IAMLambda(
            scope=self,
            id="iam_role_lambda"
        )

        iam_lambda_role = iam_lambda.build()

        # ==================================================
        # =================== DYNAMODB =====================
        # ==================================================

        dynamodb_class = DynamoDB(
            scope=self,
            id="dynamodb_stack",
        )

        table = dynamodb_class.build()

        # ==================================================
        # ================== S3 BUCKET =====================
        # ==================================================

        s3_bucket_data = aws_s3.Bucket(
            self,
            f"{self.prefix_id}_s3_bucket_data",
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        s3_bucket_layer = aws_s3.Bucket(
            self,
            f"{self.prefix_id}_s3_bucket_layer",
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # ==================================================
        # ================== COPY DATA =====================
        # ==================================================

        s3_add_pricing_data = s3_deployment.BucketDeployment(
            self,
            id=f"{self.prefix_id}_add_pricing_data",
            sources=[s3_deployment.Source.asset(f"{self.data_directory}/pricing")],
            destination_bucket=s3_bucket_layer,
            destination_key_prefix="data/pricing"
        )

        s3_add_knowledge_base_data = s3_deployment.BucketDeployment(
            self,
            id=f"{self.prefix_id}_add_knowledge_base_data",
            sources=[s3_deployment.Source.asset(f"{self.data_directory}/docs")],
            destination_bucket=s3_bucket_data,
            destination_key_prefix=""
        )

        s3_add_api_schema = s3_deployment.BucketDeployment(
            self,
            id=f"{self.prefix_id}_add_api_schema",
            sources=[s3_deployment.Source.asset(f"{self.open_api_spec_directory}")],
            destination_bucket=s3_bucket_layer,
            destination_key_prefix="openapi-spec"
        )

        # ==================================================
        # =============== LAMBDA LAYERS ====================
        # ==================================================

        lambda_layer = LambdaLayer(
            scope=self,
            id=f"{self.prefix_id}_lambda_layer",
            s3_bucket=s3_bucket_layer.bucket_name,
            role=iam_lambda_role.role_name,
            dependencies=[s3_add_pricing_data, s3_add_knowledge_base_data]
        )

        boto3_layer = lambda_layer.build(
            layer_name=f"{self.prefix_id}_boto3_sdk_layer",
            code_dir=f"{self.lambdas_directory}/lambda_layer_requirements",
            environments={
                "REQUIREMENTS": self.boto3_requirements,
                "S3_BUCKET": s3_bucket_layer.bucket_name
            }
        )

        # ==================================================
        # ============== LAMBDA FUNCTIONS ==================
        # ==================================================

        lambda_function = LambdaFunction(
            scope=self,
            id=f"{self.prefix_id}_lambda_function",
            role=iam_lambda_role.role_name,
            dependencies=[s3_add_pricing_data, s3_add_knowledge_base_data, s3_add_api_schema]
        )

        lambda_populate_dynamodb = LambdaPopulateDynamoDB(
            scope=self,
            id=f"{self.prefix_id}_custom_resource",
            s3_bucket=s3_bucket_layer.bucket_name,
            role=iam_lambda_role.role_name,
            dependencies=[s3_add_pricing_data, s3_add_knowledge_base_data, s3_add_api_schema]
        )

        lambda_populate_dynamodb.build(
            function_name=f"{self.prefix_id}_populate_dynamodb",
            code_dir=f"{self.lambdas_directory}/lambda_populate_dynamodb",
            environments={
                "DATA_PATH": "data/pricing/index.json",
                "S3_BUCKET": s3_bucket_layer.bucket_name,
                "TABLE_NAME": table.table_name
            }
        )

        lambda_bedrock_agent = lambda_function.build(
            function_name=f"{self.prefix_id}_bedrock_bot_agent",
            code_dir=f"{self.lambdas_directory}/lambda_bot_agent",
            memory=512,
            timeout=900,
            environment={
                "TABLE_NAME": table.table_name
            },
            layers=[boto3_layer]
        )

        lambda_bedrock_agent.add_permission(
            id=f"{self.prefix_id}_bedrock_bot_agent_permission",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
            source_account=self.account
        )

        CfnOutput(self, f"{self.prefix_id}_s3_bucket_api_spec", export_name=f"{self.prefix_id}S3BucketAPISpec", value=s3_bucket_layer.bucket_name)

# ==================================================
# ============== STACK WITH COST CENTER ============
# ==================================================

app = App()

configs = _load_configs("./configs.json")

for config in configs:
    api_stack = BedrockAPIStack(
        scope=app,
        id=f"{config['STACK_PREFIX']}-bedrock-agent-auto",
        config=config
    )

    api_stack.build()

    # Add a cost tag to all constructs in the stack
    Tags.of(api_stack).add("Tenant", api_stack.prefix_id)

try:
    app.synth()
except Exception as e:
    stacktrace = traceback.format_exc()
    print(stacktrace)

    raise e
