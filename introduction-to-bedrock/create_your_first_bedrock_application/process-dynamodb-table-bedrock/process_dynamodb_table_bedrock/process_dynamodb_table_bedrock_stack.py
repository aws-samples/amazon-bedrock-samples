from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    Duration,
    triggers as triggers
)
from constructs import Construct


class ProcessDynamoDBTableBedrockStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create dynamoDB table for the emails data
        email_data_table_partition_key = "email_id"
        emails_data_table = dynamodb.Table(
            self,
            "EmailDataTable",
            partition_key=dynamodb.Attribute(
                name=email_data_table_partition_key,
                type=dynamodb.AttributeType.NUMBER
            ),
            table_name="EmailsData"
        )
        # create dynamoDB table for the information extracted
        information_extracted_table_partition_key = "thread_id"
        information_extracted_table = dynamodb.Table(
            self,
            "EmailInformationTable",
            partition_key=dynamodb.Attribute(
                name=information_extracted_table_partition_key,
                type=dynamodb.AttributeType.NUMBER
            ),
            table_name="EmailsInformationExtracted"
        )

        lambda_name_emails_processing = "emails-processing-app"
        lambda_name_populate_dynamodb = "populate-dynamodb-table"

        # create lambda function that handles Emails Processing requests
        emails_processing_lambda = _lambda.Function(
            self,
            "EmailsProcessingLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("process_dynamodb_table_bedrock/process_dynamodb_table_bedrock_lambda"),
            function_name=lambda_name_emails_processing,
            timeout=Duration.minutes(10),
        )

        # create lambda function that populates emails dynamodb
        populate_data = triggers.TriggerFunction(
            self,
            "PopulateEmailsLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("process_dynamodb_table_bedrock/populate_dynamodb_table"),
            # layers=[layer],
            function_name=lambda_name_populate_dynamodb,
            timeout=Duration.minutes(10),
        )

        populate_data.add_environment(
            key="emails_data_table",
            value=emails_data_table.table_name
        )

        emails_processing_lambda.add_environment(
            key="emails_data_table",
            value=emails_data_table.table_name
        )

        populate_data.add_environment(
            key="region",
            value=self.region
        )

        emails_processing_lambda.add_environment(
            key="region",
            value=self.region
        )

        emails_processing_lambda.add_environment(
            key="information_extracted_table",
            value=information_extracted_table.table_name
        )

        emails_processing_lambda.add_environment(
            key="information_extracted_table_partition_key",
            value=information_extracted_table_partition_key
        )
        populate_data.add_environment(
            key="emails_data_table_partition_key",
            value=email_data_table_partition_key
        )

        # add bedrock and dynamoDB permissions to lambda function
        emails_processing_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'bedrock:*',
                    'dynamodb:*'
                ],
                resources=[
                    '*',
                ],
            )
        )

        # add dynamoDB permissions to lambda function
        populate_data.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    'dynamodb:*'
                ],
                resources=[
                    '*',
                ],
            )
        )
