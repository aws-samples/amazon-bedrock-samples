from datetime import datetime

# from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from cdklabs.generative_ai_cdk_constructs import bedrock

# from aws_cdk import aws_s3_notifications as s3n
from constructs import Construct


class PiiRedactionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # region = Stack.of(self).region
        account = Stack.of(self).account

        # Retrieve and log the stack properties
        print(f"Stack Name: {self.stack_name}")

        # Step 1: Create S3 buckets
        source_bucket = s3.Bucket(
            self,
            "SourceBucket",
            bucket_name=f"scenario1-{account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        safe_bucket = s3.Bucket(
            self,
            "PIISafeBucket",
            bucket_name=f"scenario1-redacted-{account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        safe_bucket.node.add_dependency(source_bucket)

        # Create DynamoDB table for job tracking
        job_table = dynamodb.Table(
            self,
            "JobTrackingTable",
            table_name="pii_scenario1_tracking",
            partition_key=dynamodb.Attribute(
                name="comprehend_job_id", type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )
        job_table.node.add_dependency(safe_bucket)

        # Create IAM role for Lambda function
        comprehend_role = self.create_comprehed_iam_role(source_bucket)

        # Create Comprehend Processing Lambda
        processing_lambda = self.create_processing_lambda(
            source_bucket, safe_bucket, job_table, comprehend_role
        )
        processing_lambda.node.add_dependency(comprehend_role)

        # Create Amazon Bedrock Guardrail
        guardrails = self.create_bedrock_guardrails()

        # Create Amazon Bedrock KnowledgeBase
        knowledge_base, data_source = self.create_bedrock_kb(safe_bucket)
        knowledge_base.node.add_dependency(guardrails)

        # Create Macie Processing Lambda
        macie_lambda = self.create_macie_lambda(
            source_bucket,
            safe_bucket,
            job_table,
            knowledge_base.knowledge_base_id,
            data_source.data_source_id,
        )
        macie_lambda.node.add_dependency(knowledge_base)

        # Create Authorization layer. APIGW, Cognito
        bedrock_lambda, apigw, user_pool, client = self.create_authz_layer(
            knowledge_base.knowledge_base_id, guardrails.guardrail_id
        )
        bedrock_lambda.node.add_dependency(knowledge_base)

        # Create EventBridge rule for Comprehend job completion
        self.create_event_rules(processing_lambda, macie_lambda)

        # print outputs
        CfnOutput(
            self,
            "SourceBucketName",
            value=source_bucket.bucket_name,
            description="Source Bucket name for dropping sensitive data files",
            export_name="piiSourceBucket",
        )

        CfnOutput(
            self,
            "SafeBucketName",
            value=source_bucket.bucket_name,
            description="Source Bucket name for dropping sensitive data files",
            export_name="piiSafeBucket",
        )

        CfnOutput(
            self,
            "ComprehendLambdaFunction",
            value=processing_lambda.function_name,
            description="Comprehend Processing Lambda Function Name",
            export_name="ComprehendProcessingLambda",
        )

        CfnOutput(
            self,
            "MacieLambdaFunction",
            value=macie_lambda.function_name,
            description="Macie Processing Lambda Function Name",
            export_name="MacieProcessingLambda",
        )

        CfnOutput(
            self,
            "DynamoDBTrackingTable",
            value=job_table.table_name,
            description="DynamoDB Tracking Table Name",
            export_name="DynamoDBTrackingTable",
        )

        CfnOutput(
            self,
            "GuardrailsId",
            value=guardrails.guardrail_id,
            description="Amazon Bedrock Guardrails ID",
            export_name="GuardrailsID",
        )

        CfnOutput(
            self,
            "BedrockKBId",
            value=knowledge_base.knowledge_base_id,
            description="The ID of the Bedrock Knowledge Base",
            export_name="KnowledgeBaseId",
        )

        CfnOutput(
            self,
            "BedrockKBDataSourceID",
            value=data_source.data_source_id,
            description="The ID of the Bedrock Knowledge Base Data Source",
            export_name="KBDataSourceID",
        )

        CfnOutput(
            self,
            "BedrockLambda",
            value=bedrock_lambda.function_name,
            description="The name of the Bedrock Knowledge Base Data Source",
            export_name="BedrockAPIGWLambda",
        )

        CfnOutput(
            self,
            "APIGatewayURL",
            value=apigw.url,
            description="The URL of the API Gateway",
            export_name="APIGatewayURL",
        )

        CfnOutput(
            self,
            "UserPoolId",
            value=user_pool.user_pool_id,
            description="The ID of the User Pool",
            export_name="UserPoolId",
        )

        CfnOutput(
            self,
            "CognitoClientId",
            value=client.user_pool_client_id,
            description="The ID of the Cognito User Pool Client",
            export_name="CognitoClientId",
        )

    def create_processing_lambda(
        self, source_bucket, safe_bucket, job_table, comprehend_role
    ):
        """Create Comprehend processing Lambda"""
        processing_lambda = lambda_.Function(
            self,
            "ComprehendProcessingLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="comprehend_lambda.handler",
            code=lambda_.Code.from_asset("cdk_pii_scenario1/lambda/comprehend"),
            timeout=Duration.minutes(15),
            environment={
                "SOURCE_BUCKET": source_bucket.bucket_name,
                "SAFE_BUCKET": safe_bucket.bucket_name,
                "COMPREHEND_ROLE_ARN": comprehend_role.role_arn,
                "JOB_TABLE_NAME": job_table.table_name,
            },
        )

        # Grant S3 permissions
        source_bucket.grant_read_write(processing_lambda)
        safe_bucket.grant_write(processing_lambda)

        # Grant Comprehend permissions
        processing_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "comprehend:StartPiiEntitiesDetectionJob",
                    "comprehend:DescribePiiEntitiesDetectionJob",
                ],
                resources=["*"],
            )
        )

        # Add iam:PassRole permission
        processing_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[comprehend_role.role_arn],
            )
        )

        # Grant DynamoDB permissions
        job_table.grant_read_write_data(processing_lambda)

        # Add STS permissions
        processing_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["sts:GetCallerIdentity"], resources=["*"])
        )

        return processing_lambda

    def create_macie_lambda(
        self, source_bucket, safe_bucket, job_table, kb_id, datasource_id
    ):
        """Create Macie processing Lambda with required permissions"""
        macie_lambda = lambda_.Function(
            self,
            "MacieProcessingLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="macie_lambda.handler",
            code=lambda_.Code.from_asset("cdk_pii_scenario1/lambda/macie"),
            timeout=Duration.minutes(15),
            environment={
                "SOURCE_BUCKET": source_bucket.bucket_name,
                "SAFE_BUCKET": safe_bucket.bucket_name,
                "JOB_TABLE_NAME": job_table.table_name,
                "KNOWLEDGE_BASE_ID": kb_id,
                "DATASOURCE_ID": datasource_id,
            },
        )

        # Grant S3 permissions
        source_bucket.grant_read_write(macie_lambda)
        safe_bucket.grant_write(macie_lambda)

        # Grant DynamoDB permissions
        job_table.grant_read_write_data(macie_lambda)

        # Grant Macie permissions
        macie_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "macie2:CreateClassificationJob",
                    "macie2:DescribeClassificationJob",
                    "macie2:ListFindings",
                    "macie2:GetFindings",
                ],
                resources=["*"],
            )
        )

        # Grant Bedrock Start Ingestion Job permissions
        macie_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:StartIngestionJob",
                    "bedrock:ListIngestionJob",
                    "bedrock:GetIngestionJob",
                ],
                resources=["*"],
            )
        )

        # Grant STS permissions
        macie_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sts:GetCallerIdentity"],
                resources=["*"],
            )
        )

        return macie_lambda

    def create_event_rules(self, processing_lambda, macie_lambda):
        """Create EventBridge rules"""
        # Rule for periodic processing
        processing_rule = events.Rule(
            self,
            "PIIComprehendScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )
        processing_rule.add_target(targets.LambdaFunction(processing_lambda))
        processing_rule.node.add_dependency(processing_lambda)

        # Rule for Comprehend job completion
        macie_rule = events.Rule(
            self,
            "PIIMacieScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )
        macie_rule.add_target(targets.LambdaFunction(macie_lambda))
        macie_rule.node.add_dependency(macie_lambda)

    def create_comprehed_iam_role(self, source_bucket):
        # Create Comprehend IAM Role
        comprehend_role_name = (
            f"ComprehendPIIRole-{datetime.today().strftime('%d%b%Y')}"
        )

        # Create Comprehend IAM role
        comprehend_role = iam.Role(
            self,
            "ComprehendPIIRole",
            assumed_by=iam.ServicePrincipal("comprehend.amazonaws.com"),
            description="Comprehend IAM role for PII redaction",
            role_name=comprehend_role_name,
        )

        # Add S3 Permissions to Comprehend role
        comprehend_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket"],
                resources=[source_bucket.bucket_arn],
                conditions={
                    "StringLike": {
                        "s3:prefix": [
                            "processing/*",
                            "processing/",
                            "processed/*",
                            "processed/",
                        ]
                    }
                },
            )
        )

        comprehend_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                resources=[f"{source_bucket.bucket_arn}/processing/*"],
            )
        )

        comprehend_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                resources=[f"{source_bucket.bucket_arn}/processed/*"],
            )
        )
        return comprehend_role

    def create_macie_iam_role(self, source_bucket, safe_bucket):
        """Create Macie IAM role"""
        macie_role = iam.Role(
            self,
            "MacieRole",
            assumed_by=iam.ServicePrincipal("macie.amazonaws.com"),
            description="Macie IAM role for sensitive data discovery",
        )

        # Add S3 permissions for source bucket
        macie_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[source_bucket.bucket_arn, f"{source_bucket.bucket_arn}/*"],
            )
        )

        # Add S3 permissions for safe bucket
        macie_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject", "s3:ListBucket"],
                resources=[safe_bucket.bucket_arn, f"{safe_bucket.bucket_arn}/*"],
            )
        )

        return macie_role

    def create_bedrock_kb(self, safe_bucket):
        # Create Bedrock Knowledgebase
        kb = bedrock.KnowledgeBase(
            self,
            "BedrockPIIKnowledgeBase",
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_512,
            instruction="Bedrock Knowledge Base for testing PII data",
        )

        # Add S3 bucket as datasource to KB
        dataSource = bedrock.S3DataSource(
            self,
            "BedrockS3DataSource",
            bucket=safe_bucket,
            knowledge_base=kb,
            data_source_name="pii-redact-before-ingest",
            chunking_strategy=bedrock.ChunkingStrategy.FIXED_SIZE,
        )

        return kb, dataSource

    def create_bedrock_guardrails(self):
        # Ref: https://github.com/awslabs/generative-ai-cdk-constructs/blob/f6f1e37b3d4c102da720ea53b619a7a31093e071/src/cdk-lib/bedrock/README.md#bedrock-guardrails
        guardrail = bedrock.Guardrail(
            self,
            "MyGuardrail",
            name="PIIGuardrail",
            description="Guardrail to protect sensitive data",
        )
        # PII Filter: Entities to Mask
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.NAME, action=bedrock.GuardrailAction.ANONYMIZE
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.AGE, action=bedrock.GuardrailAction.ANONYMIZE
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.EMAIL,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.PHONE,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.DRIVER_ID,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.LICENSE_PLATE,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        # PII Filter: Entities to Block
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.ADDRESS, action=bedrock.GuardrailAction.BLOCK
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.USERNAME, action=bedrock.GuardrailAction.BLOCK
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.PASSWORD, action=bedrock.GuardrailAction.BLOCK
        )

        # Add contextual grounding
        guardrail.add_contextual_grounding_filter(
            type=bedrock.ContextualGroundingFilterType.GROUNDING,
            threshold=0.75,
        )

        # Add denied topic filter
        guardrail.add_denied_topic_filter(
            bedrock.Topic.custom(
                name="PII_Extraction",
                definition="Requesting PII information unless it's about a Person's name.",
                examples=[
                    "What is the email address of John Doe?",
                    "Get me home address for Johnny Appleseed.",
                ],
            )
        )

        # Add profanity filter
        guardrail.add_managed_word_list_filter(bedrock.ManagedWordFilterType.PROFANITY)

        return guardrail

    def create_authz_layer(self, kb_id, guardrail_id):
        region = Stack.of(self).region
        account = Stack.of(self).account

        # Lambda function to retrieve Bedrock KB
        bedrock_lambda = lambda_.Function(
            self,
            "BedrockLambdaFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="bedrock_apigw.handler",
            code=lambda_.Code.from_asset("cdk_pii_scenario1/lambda/bedrock"),
            timeout=Duration.minutes(15),
            environment={
                "CFN_STACK_NAME": self.stack_name,
            },
        )

        # Create Cognito User Pool
        user_pool = cognito.UserPool(
            self,
            "BedrockAPIUserPool",
            user_pool_name="scenario1-api-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases={"email": True},
            auto_verify={"email": True},
            standard_attributes={"email": {"required": True, "mutable": True}},
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create User Pool Client
        client = user_pool.add_client(
            "BedrockCognitoClient",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(admin_user_password=True, user_password=True),
        )
        client.node.add_dependency(user_pool)

        # Create Admin Group
        admin_group = cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Admins",
            description="Administrator group"
        )
        admin_group.node.add_dependency(user_pool)

        # Create Admin user
        admin_user = cognito.CfnUserPoolUser(
            self,
            "Jane",
            user_pool_id=user_pool.user_pool_id,
            username="jane@example.com",
            desired_delivery_mediums=["EMAIL"],
            force_alias_creation=True,
            user_attributes=[
                {"name": "email", "value": "jane@example.com"},
                {"name": "email_verified", "value": "true"},
            ],
        )
        admin_user.node.add_dependency(admin_group)

        # Add Admin User to Admin Group
        admin_user_to_group = cognito.CfnUserPoolUserToGroupAttachment(
            self,
            "AdminUserToGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Admins",
            username=str(admin_user.username),
        )
        admin_user_to_group.node.add_dependency(admin_user)

        # Create Cognito Authorizer
        auth = apigw.CognitoUserPoolsAuthorizer(
            self, "BedrockAPIAuthorizer", cognito_user_pools=[user_pool]
        )
        auth.node.add_dependency(user_pool)

        # Create API Gateway
        api = apigw.RestApi(
            self, "Scenario1_APIGW", rest_api_name="Scenario1_APIGW_to_Bedrock"
        )

        # Create API Gateway endpoint for Bedrock
        bedrock_resource = api.root.add_resource("bedrock")
        bedrock_resource.add_method(
            "POST",
            apigw.LambdaIntegration(bedrock_lambda),
            authorizer=auth,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # IAM policy to allow KB access to Lambda
        lambda_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:RetrieveAndGenerate",
                "bedrock:Retrieve",
                "bedrock:GetKnowledgeBase",
                "cloudformation:DescribeStacks",
                "bedrock:InvokeModel",
                "bedrock:ApplyGuardrail",
            ],
            resources=[
                f"arn:aws:bedrock:{region}:{account}:knowledge-base/{kb_id}",
                Stack.of(self).stack_id,
                f"arn:aws:bedrock:{region}::foundation-model/*",
                f"arn:aws:bedrock:{region}:{account}:guardrail/{guardrail_id}",
            ],
        )

        bedrock_lambda.add_to_role_policy(lambda_policy)

        return bedrock_lambda, api, user_pool, client
