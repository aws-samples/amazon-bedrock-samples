from aws_cdk import (
    Aws,
    CfnOutput,
    Duration,
    Stack,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_sns,
    aws_sns_subscriptions,
)
from constructs import Construct


class ProcessEmailBedrockStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create DynamoDB table
        table = aws_dynamodb.Table(
            self,
            "ProcessEmailBedrockTable",
            table_name="EmailOrders",
            partition_key=aws_dynamodb.Attribute(
                name="MessageId", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="Timestamp", type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # Need to use the newer boto3 version that has Bedrock
        # The layer zip is created by lambdas/build_lambda_layer.sh
        bedrock_boto3_layer = aws_lambda.LayerVersion(
            self,
            "ProcessEmailBedrockLayer",
            code=aws_lambda.Code.from_asset("lambdas/bedrock_boto3_layer.zip"),
            compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_12],
            description="A layer containing a more recent boto3 version that has Bedrock",
            layer_version_name="boto3-with-bedrock"
        )

        # lambda function that processes the emails and stores the information to dynamoDB
        lambda_function = aws_lambda.Function(
            self,
            "ProcessEmailBedrockFunction",
            function_name="emails-processing-with-bedrock",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler="lambda.lambda_handler",
            code=aws_lambda.Code.from_asset("lambdas/process_emails_with_bedrock"),
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": table.table_name,
            },
        )
        # Add the layer to the function
        lambda_function.add_layers(bedrock_boto3_layer)

        # grant permissions to the lambda function
        table.grant_write_data(lambda_function)
        lambda_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )
        lambda_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["dynamodb:*"],
                resources=["*"]
            )
        )

        sns_topic = aws_sns.Topic(
            self,
            "ProcessEmailsWithBedrockTopic",
        )
        sns_topic.add_subscription(
            aws_sns_subscriptions.LambdaSubscription(lambda_function)
        )

        sns_topic.add_to_resource_policy(
            aws_iam.PolicyStatement(
                actions=["SNS:Publish"],
                resources=[sns_topic.topic_arn],
                principals=[aws_iam.ServicePrincipal("ses.amazonaws.com")],
                conditions={
                    "StringEquals": {"AWS:SourceAccount": Aws.ACCOUNT_ID},
                    "StringLike": {"AWS:SourceArn": "arn:aws:ses:*"},
                },
            )
        )

        CfnOutput(
            self,
            "ProcessEmailsWithBedrockTopicName",
            value=sns_topic.topic_name,
            description="The name of the SNS topic",
        )
        CfnOutput(
            self,
            "ProcessEmailBedrockTableName",
            value=table.table_name,
            description="The name of the DynamoDB table",
        )
        CfnOutput(
            self,
            "ProcessEmailBedrockFunctionName",
            value=lambda_function.function_name,
            description="The name of the Lambda function",
        )
