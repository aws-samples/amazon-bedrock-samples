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

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        

        # Create a VPC for the Aurora cluster
        vpc = ec2.Vpc(
            self, "AuroraVPC",
            max_azs=3  # Specify the number of availability zones
        )

        # Create a Secrets Manager secret for the Aurora cluster credentials
        self.db_credentials_secret = secretsmanager.Secret(
            self, "DBCredentialsSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username":"dbadmin"}',
                generate_string_key="password",
                exclude_characters="'@/\"\""
            )
        )

        # Create the Aurora cluster
        # CDK docs: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/README.html
        self.aurora_cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1
            ),
            credentials=rds.Credentials.from_secret(self.db_credentials_secret),
            default_database_name="MyAuroraDB",
            enable_data_api=True,
            writer=rds.ClusterInstance.provisioned("writer",
                publicly_accessible=False,
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE)
            ),
            readers=[
                rds.ClusterInstance.provisioned("reader",
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.LARGE)
                ),
            ],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            vpc=vpc
        )
        
        # Lambda function to create a table using the Data API
        table_creation_function = _lambda.Function(
            self, "TableCreationFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.main",
            code=_lambda.Code.from_inline("""
import boto3
import os

def main(event, context):
    rds_client = boto3.client('rds-data')
    
    sql_statements = [
    "CREATE EXTENSION IF NOT EXISTS vector;",
    "CREATE TABLE IF NOT EXISTS kb_vector_store (id uuid PRIMARY KEY, embedding vector(1024), chunks text, metadata json);"
    ]
    
    try:
        # Execute each sql statement
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
        # Handle any exceptions that occur during execution
        return {
            'statusCode': 500,
            'body': 'An error occurred while executing SQL statements.',
            'error': str(e)
        }
            """),
            environment={
                "DB_CLUSTER_ARN": self.aurora_cluster.cluster_arn,
                "DB_SECRET_ARN": self.db_credentials_secret.secret_arn,
                "DB_NAME": "MyAuroraDB"
            },
            vpc=vpc,
            security_groups=[self.aurora_cluster.connections.security_groups[0]],
            timeout=Duration.minutes(1)  # Setting the timeout to 1 minute
        )


        # Policy granting full permissions to RDS and Secrets Manager
        policy_statement = iam.PolicyStatement(
            actions=[
                "rds:*",
                "rds-data:*",
                "secretsmanager:*",
                "lambda:*"
            ],
            resources=["*"] # '*' grants full access to all resources
        )

        # Attach the policy to the Lambda function's role
        table_creation_function.add_to_role_policy(policy_statement)


        # Use AwsCustomResource to create and execute the Lambda function
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
        
        # Ensure the custom resource depends on the Aurora cluster so that it only runs once the cluster is available
        custom_resource.node.add_dependency(self.aurora_cluster)
        
        # # create an SSM parameters which store export values
        ssm.StringParameter(self, 'dbArn',
                            parameter_name="/e2e-rag/dbArn",
                            string_value=self.aurora_cluster.cluster_arn)
        
        ssm.StringParameter(self, 'secretArn',
                            parameter_name="/e2e-rag/secretArn",
                            string_value=self.db_credentials_secret.secret_arn)
        
        # Output the database cluster endpoint
        CfnOutput(
            self, "AuroraClusterEndpoint",
            value=self.aurora_cluster.cluster_endpoint.socket_address,
            description="The endpoint of the Aurora cluster"
        )
