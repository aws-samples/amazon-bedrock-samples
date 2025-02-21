from constructs import Construct
from aws_cdk import (
    CfnOutput,
    Duration,
    App, Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
    aws_lambda as _lambda,
    custom_resources as cr,
    aws_iam as iam,
)

class AuroraStack(Stack):
    """
    This AWS CDK stack sets up an Amazon Aurora PostgreSQL cluster within a VPC. 
    Key components of this stack include:
    - A VPC for networking
    - An Aurora PostgreSQL cluster with a writer and reader instance
    - AWS Secrets Manager for securely storing database credentials
    - A Lambda function to create a table in the Aurora cluster using the Data API
    - IAM policies to grant necessary permissions
    - AWS Systems Manager (SSM) Parameter Store for storing the cluster ARN and secret ARN
    - A CloudFormation output for the database endpoint
    """
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Create a Virtual Private Cloud (VPC) to host the Aurora database cluster
        vpc = ec2.Vpc(
            self, "AuroraVPC",
            max_azs=3  # Maximum number of Availability Zones to use
        )

        # Create a Secrets Manager secret to securely store the database credentials
        self.db_credentials_secret = secretsmanager.Secret(
            self, "DBCredentialsSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username":"dbadmin"}',  # Set default username
                generate_string_key="password",  # Auto-generate a password
                exclude_characters="'@/\"\""  # Exclude special characters that might cause issues
            )
        )

        # Create an Aurora PostgreSQL cluster
        self.aurora_cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1  # Specify the Aurora PostgreSQL version
            ),
            credentials=rds.Credentials.from_secret(self.db_credentials_secret),  # Use stored credentials
            default_database_name="MyAuroraDB",  # Set the default database name
            enable_data_api=True,  # Enable Data API for access to create tables programmatically 
            writer=rds.ClusterInstance.provisioned("writer",
                publicly_accessible=False,  # Keep the database private
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE)
            ),
            readers=[
                rds.ClusterInstance.provisioned("reader",
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE)
                ),
            ],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS  # Place database in private subnets
            ),
            vpc=vpc
        )
        
        # Define a Lambda function that creates a table in the Aurora database using the Data API
        table_creation_function = _lambda.Function(
            self, "TableCreationFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",  # Specify the entry point function
            code=_lambda.Code.from_inline("""
import boto3
import os

def lambda_handler(event, context):
    rds_client = boto3.client('rds-data')
    
    sql_statements = [
    "CREATE EXTENSION IF NOT EXISTS vector;",
    "CREATE TABLE IF NOT EXISTS kb_vector_store (id uuid PRIMARY KEY, embedding vector(1024), chunks text, metadata json);"
    ]
    
    try:
        # Execute each SQL statement
        for statement in sql_statements:
          print("SQL STATEMENT: ", statement)
          
          response = rds_client.execute_statement(
            resourceArn=os.environ['DB_CLUSTER_ARN'],
            secretArn=os.environ['DB_SECRET_ARN'],
            database=os.environ['DB_NAME'],
            sql=statement 
          )
          
          print("SQL RESPONSE: ", response)

        return {
            'statusCode': 200,
            'body': 'SQL statements executed successfully!',
        }

    except Exception as e:
        # Handle any errors that occur during execution
        return {
            'statusCode': 500,
            'body': 'An error occurred while executing SQL statements.',
            'error': str(e)
        }
            """),
            environment={
                "DB_CLUSTER_ARN": self.aurora_cluster.cluster_arn,  # Aurora Cluster ARN
                "DB_SECRET_ARN": self.db_credentials_secret.secret_arn,  # Secret ARN for credentials
                "DB_NAME": "MyAuroraDB"  # Database name
            },
            vpc=vpc,
            security_groups=[self.aurora_cluster.connections.security_groups[0]],
            timeout=Duration.minutes(1)  # Set timeout to 1 minute
        )

        # Define an IAM policy that allows Lambda to access RDS and Secrets Manager
        policy_statement = iam.PolicyStatement(
            actions=[
                "rds:*",
                "rds-data:*",
                "secretsmanager:*",
                "lambda:*"
            ],
            resources=["*"] # Grant full access to all resources (use least privilege in production!)
        )

        # Attach the policy to the Lambda function
        table_creation_function.add_to_role_policy(policy_statement)

        # Use AwsCustomResource to invoke the Lambda function during stack deployment
        custom_resource = cr.AwsCustomResource(
            self, "TableCreationCustomResource",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": table_creation_function.function_name,
                    "InvocationType": "RequestResponse",
                    "Payload": "{}"
                },
                physical_resource_id=cr.PhysicalResourceId.of("TableCreationResource")
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[table_creation_function.function_arn]
                )
            ])
        )
        
        # Ensure the custom resource only runs after the Aurora cluster is available
        custom_resource.node.add_dependency(self.aurora_cluster)
        
        # Store the database ARN and secret ARN in AWS Systems Manager Parameter Store
        ssm.StringParameter(self, 'dbArn',
                            parameter_name="/e2e-rag/dbArn",
                            string_value=self.aurora_cluster.cluster_arn)
        
        ssm.StringParameter(self, 'secretArn',
                            parameter_name="/e2e-rag/secretArn",
                            string_value=self.db_credentials_secret.secret_arn)
        
        # Output the Aurora database cluster endpoint for reference
        CfnOutput(
            self, "AuroraClusterEndpoint",
            value=self.aurora_cluster.cluster_endpoint.socket_address,
            description="The endpoint of the Aurora cluster"
        )
