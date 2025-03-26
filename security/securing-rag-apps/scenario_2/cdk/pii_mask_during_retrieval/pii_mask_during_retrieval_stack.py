from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_bedrock
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from cdklabs.generative_ai_cdk_constructs import bedrock
from constructs import Construct


class PiiMaskDuringRetrievalStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region
        account = Stack.of(self).account

        # Lambda function to retrieve Bedrock KB
        bedrock_lambda = _lambda.Function(
            self,
            "BedrockLambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            timeout=Duration.seconds(30),
            code=_lambda.Code.from_inline(
                """
import boto3
import json

def handler(event, context):
    try:
        claims = event['requestContext']['authorizer']['claims']
        body = json.loads(event["body"])

        cfn_client = boto3.client('cloudformation')
        response = cfn_client.describe_stacks(StackName="PiiMaskDuringRetrievalStack")

        # Create a dictionary of all outputs
        outputs = {}
        if 'Stacks' in response and len(response['Stacks']) > 0:
            if 'Outputs' in response['Stacks'][0]:
                for output in response['Stacks'][0]['Outputs']:
                    outputs[output['OutputKey']] = output['OutputValue']

        metadata_filters = { "notEquals": { "key": "accessType", "value": "admin" }}

        guardrailID = outputs["NonAdminGuardrailIDS2"]
        if (claims['cognito:groups'] == "Admins"):
            guardrailID = outputs["AdminGuardrailIDS2"]
            metadata_filters = {"orAll" :[ { "notEquals": { "key": "accessType", "value": "admin" }}, { "equals": { "key": "accessType", "value": "admin" }}] }

        client = boto3.client('bedrock-agent-runtime')
        response = client.retrieve_and_generate(
            input={
                'text': body["prompt"]
            },
            retrieveAndGenerateConfiguration={
                'knowledgeBaseConfiguration': {
                    'generationConfiguration': {
                        'guardrailConfiguration': {
                            'guardrailId': guardrailID,
                            'guardrailVersion': 'DRAFT'
                        },
                        "inferenceConfig": {
                            "textInferenceConfig": {
                                "temperature": body["temperature"],
                                "topP": body["topP"]
                            }
                        }
                    },
                    'knowledgeBaseId': outputs["KnowledgeBaseIdS2"],
                    'modelArn': body["modelID"],
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 10,
                            'filter': metadata_filters
                        }
                    }
                },
                'type': 'KNOWLEDGE_BASE'
            }
        )

        response_json = dict()
        response_json["response"] = response["output"]["text"]
        response_json["guardrail_action"] = response["guardrailAction"]
        return {"statusCode": 200, "body": json.dumps(response_json)}

    except Exception as e:
        # Handle any other unexpected errors
        error_message = f"An unexpected error occurred: {str(e)}"
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        }


                                """
            ),
        )

        # Create Cognito User Pool
        user_pool = cognito.UserPool(
            self,
            "BedrockAPIUserPool",
            user_pool_name="bedrock-api-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases={"email": True},
            auto_verify={"email": True},
            standard_attributes={"email": {"required": True, "mutable": True}},
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create Admin Group
        admin_group = cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Admins",
            description="Administrator group",
        )
        admin_group.node.add_dependency(user_pool)

        # Create Users Group
        users_group = cognito.CfnUserPoolGroup(
            self,
            "UsersGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Users",
            description="Regular users group",
        )
        users_group.node.add_dependency(user_pool)

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

        # Create non-admin user
        nonadmin_user = cognito.CfnUserPoolUser(
            self,
            "John",
            user_pool_id=user_pool.user_pool_id,
            username="john@example.com",
            desired_delivery_mediums=["EMAIL"],
            force_alias_creation=True,
            user_attributes=[
                {"name": "email", "value": "john@example.com"},
                {"name": "email_verified", "value": "true"},
            ],
        )
        nonadmin_user.node.add_dependency(users_group)

        # Add Admin User to Admin Group
        admin_user_to_group = cognito.CfnUserPoolUserToGroupAttachment(
            self,
            "AdminUserToGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Admins",
            username=admin_user.username,
        )
        admin_user_to_group.node.add_dependency(admin_user)

        # Add non-admin User to Users Group
        user_to_group = cognito.CfnUserPoolUserToGroupAttachment(
            self,
            "UserToGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Users",
            username=nonadmin_user.username,
        )
        user_to_group.node.add_dependency(nonadmin_user)

        # Create User Pool Client
        client = user_pool.add_client(
            "BedrockCognitoClient",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(admin_user_password=True, user_password=True),
        )
        client.node.add_dependency(user_pool)

        # Create Cognito Authorizer
        auth = apigw.CognitoUserPoolsAuthorizer(
            self, "BedrockAPIAuthorizer", cognito_user_pools=[user_pool]
        )
        auth.node.add_dependency(user_pool)

        # Create API Gateway
        api = apigw.RestApi(self, "BedrockAPI", rest_api_name="Bedrock KB API")

        # Create API Gateway endpoint for Bedrock
        bedrock_resource = api.root.add_resource("bedrock")
        bedrock_resource.add_method(
            "POST",
            apigw.LambdaIntegration(bedrock_lambda),
            authorizer=auth,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # Create Bedrock Knowledgebase
        kb = bedrock.KnowledgeBase(
            self,
            "KnowledgeBase",
            embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_512,
            instruction="Bedrock Knowledge Base for testing PII data",
        )

        # Create S3 bucket to store documents for the KB
        docBucket = s3.Bucket(
            self,
            "PIITestDataBucket",
            bucket_name=f"pii-scenario2-{region}-{account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
        )

        # Add S3 bucket as datasource to KB
        dataSource = bedrock.S3DataSource(
            self,
            "S3DataSource",
            bucket=docBucket,
            knowledge_base=kb,
            data_source_name="pii-test-data",
            chunking_strategy=bedrock.ChunkingStrategy.FIXED_SIZE,
        )

        # Create Guardrail for non-admins
        nonadmin_guardrail = aws_bedrock.CfnGuardrail(
            self,
            "NonAdminGuardrail",
            blocked_input_messaging="blockedInputMessaging",
            blocked_outputs_messaging="blockedOutputsMessaging",
            name="pii-test-nonadmin-guardrail",
            sensitive_information_policy_config=aws_bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="ANONYMIZE", type="ADDRESS"
                    ),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="ANONYMIZE", type="NAME"
                    ),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="ANONYMIZE", type="AGE"
                    ),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="ANONYMIZE", type="EMAIL"
                    ),
                    aws_bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="ANONYMIZE", type="PHONE"
                    ),
                ],
                regexes_config=[
                    aws_bedrock.CfnGuardrail.RegexConfigProperty(
                        name="DateOfBirth",
                        action="ANONYMIZE",
                        pattern=r"(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/([12]\d{3})",
                        description="Date of Birth"
                    )
                ]
            ),
            content_policy_config=aws_bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="HATE"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="VIOLENCE"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="SEXUAL"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="INSULTS"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="MISCONDUCT"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="NONE",
                        type="PROMPT_ATTACK",
                    ),
                ]
            ),
            word_policy_config=aws_bedrock.CfnGuardrail.WordPolicyConfigProperty(
                managed_word_lists_config=[
                    aws_bedrock.CfnGuardrail.ManagedWordsConfigProperty(
                        type="PROFANITY"
                    )
                ]
            ),
            topic_policy_config=aws_bedrock.CfnGuardrail.TopicPolicyConfigProperty(
                topics_config=[
                    aws_bedrock.CfnGuardrail.TopicConfigProperty(
                        definition="Date of birth, birth date, DOB information for any individual",
                        name="DateOfBirth",
                        type="DENY",
                        examples=[
                            "What is their date of birth?",
                            "Tell me John's DOB",
                            "What's his birth date?",
                            "Could you tell me Mary's date of birth?",
                            "I need to know when they were born"
                        ]
                    )
                ]
            )            
        )

        # Create Guardrail for admins
        admin_guardrail = aws_bedrock.CfnGuardrail(
            self,
            "AdminGuardrail",
            blocked_input_messaging="blockedInputMessaging",
            blocked_outputs_messaging="blockedOutputsMessaging",
            name="pii-test-admin-guardrail",
            content_policy_config=aws_bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="HATE"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="VIOLENCE"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="SEXUAL"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="INSULTS"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH", output_strength="HIGH", type="MISCONDUCT"
                    ),
                    aws_bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="NONE",
                        type="PROMPT_ATTACK",
                    ),
                ]
            ),
            word_policy_config=aws_bedrock.CfnGuardrail.WordPolicyConfigProperty(
                managed_word_lists_config=[
                    aws_bedrock.CfnGuardrail.ManagedWordsConfigProperty(
                        type="PROFANITY"
                    )
                ]
            ),
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
                "bedrock:GetInferenceProfile",
            ],
            resources=[
                f"arn:aws:bedrock:{region}:{account}:knowledge-base/{kb.knowledge_base_id}",
                Stack.of(self).stack_id,
                f"arn:aws:bedrock:*::foundation-model/*",
                f"arn:aws:bedrock:*:*:inference-profile/*",
                f"arn:aws:bedrock:{region}:{account}:guardrail/{admin_guardrail.attr_guardrail_id}",
                f"arn:aws:bedrock:{region}:{account}:guardrail/{nonadmin_guardrail.attr_guardrail_id}",
            ],
        )

        bedrock_lambda.add_to_role_policy(lambda_policy)

        CfnOutput(
            self,
            "CognitoUserPoolId",
            value=user_pool.user_pool_id,
            description="The ID of the Cognito User Pool",
            export_name="CognitoUserPoolId",
        )

        CfnOutput(
            self,
            "CognitoUserPoolClientId",
            value=client.user_pool_client_id,
            description="The ID of the Cognito User Pool Client",
            export_name="CognitoUserPoolClientId",
        )

        CfnOutput(
            self,
            "APIGatewayEndpointS2",
            value=api.url,
            description="The URL of the API Gateway endpoint",
            export_name="APIGatewayEndpointS2",
        )

        CfnOutput(
            self,
            "PiiS2BucketName",
            value=docBucket.bucket_name,
            description="The name of the S3 bucket for the KB",
            export_name="PiiS2BucketName",
        )

        CfnOutput(
            self,
            "KnowledgeBaseIdS2",
            value=kb.knowledge_base_id,
            description="The ID of the Bedrock Knowledge Base",
            export_name="KnowledgeBaseIdS2",
        )

        CfnOutput(
            self,
            "KBDataSourceIDS2",
            value=dataSource.data_source_id,
            description="The ID of the Bedrock Knowledge Base Data Source",
            export_name="KBDataSourceIDS2",
        )

        CfnOutput(
            self,
            "AdminGuardrailIDS2",
            value=admin_guardrail.attr_guardrail_id,
            description="The ID of the Bedrock Admin Guardrail",
            export_name="AdminGuardrailIDS2",
        )

        CfnOutput(
            self,
            "NonAdminGuardrailIDS2",
            value=nonadmin_guardrail.attr_guardrail_id,
            description="The ID of the Bedrock Admin Guardrail",
            export_name="NonAdminGuardrailIDS2",
        )
