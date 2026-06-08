from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_lambda as lambda_,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
    Size,
)
from constructs import Construct

from cdk_nag import ( AwsSolutionsChecks, NagSuppressions )

class ConverseSqlAgentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Use the default VPC
        vpc = ec2.Vpc.from_lookup(self, "DefaultVPC", is_default=True)
    
        # Create new private subnets in the default VPC
        new_private_subnets = []
        for i, az in enumerate(vpc.availability_zones):
            subnet = ec2.PrivateSubnet(
                self, f"NewPrivateSubnet{i}",
                vpc_id=vpc.vpc_id,
                availability_zone=az,
                cidr_block=f"172.31.{96+i*16}.0/20",  # Adjust CIDR blocks as needed
            )
            new_private_subnets.append(subnet)

        # Create DynamoDB table
        dynamodb_table = dynamodb.Table(
            self, "TEXT2SQLTable",
            table_name="advtext2sql_memory_tb",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create RDS MySQL instance
        db_secret = secretsmanager.Secret(
            self, "DBSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
                exclude_punctuation=True,
                include_space=False
            )
        )

        db_subnet_group = rds.SubnetGroup(
            self, "DBSubnetGroup",
            vpc=vpc,
            description="Subnet group for RDS database",
            vpc_subnets=ec2.SubnetSelection(subnets=new_private_subnets)
        )
        
        # Create a security group for RDS and Lambda. For POC purpose we are using a same Security group for both RDS and Lambda but when implementing as per best practice it is good to use seperate security groups.
        security_group = ec2.SecurityGroup(
            self, "SharedSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="Security group for RDS and Lambda"
        )
        
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.all_traffic(),
            description="Allow all inbound traffic from VPC CIDR"
        )
        
        db_instance = rds.DatabaseInstance(
            self, "MyRDSInstance",
            instance_identifier="myrdsdatabase",
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0_39),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=new_private_subnets),
            subnet_group=db_subnet_group,
            credentials=rds.Credentials.from_secret(db_secret),
            multi_az=False,
            allocated_storage=20,
            max_allocated_storage=100,
            security_groups=[security_group],
            publicly_accessible=False,
            delete_automated_backups=True,
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY 
        )

        # Create VPC Endpoints
        dynamodb_endpoint = vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            subnets=[ec2.SubnetSelection(subnets=new_private_subnets)]
        )
        secrets_manager_endpoint = vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=ec2.SubnetSelection(subnets=new_private_subnets),
            security_groups=[security_group]
        )
        bedrock_endpoint = vpc.add_interface_endpoint(
            "BedrockEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            subnets=ec2.SubnetSelection(subnets=new_private_subnets),
            security_groups=[security_group]
        )

        # Create Lambda function
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # Add permissions for DynamoDB, Secrets Manager, and Bedrock
        
        # Grant DynamoDB permissions
        dynamodb_table.grant_read_write_data(lambda_role)

        # Grant Secrets Manager permissions
        db_secret.grant_read(lambda_role)
        
        
        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"))
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"]
        ))

        # Create Lambda layers
        layer1 = lambda_.LayerVersion(
            self, "psycopg2_final",
            layer_version_name="layer_content",
            code=lambda_.Code.from_asset("./src/layers/layer_content.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11]
        )        

        # Create Lambda function
        lambda_function = lambda_.Function(
            self, "SQLAgentFunction",
            function_name="sqlagent",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("./src/ConverseSqlAgent"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=new_private_subnets),
            security_groups=[security_group],
            layers=[layer1],
            role=lambda_role,
            memory_size=1024,
            ephemeral_storage_size=Size.gibibytes(2),
            timeout=Duration.minutes(15),
            environment={
                "DynamoDbMemoryTable": dynamodb_table.table_name,
                "BedrockModelId": "anthropic.claude-3-sonnet-20240229-v1:0"
            }
        )

        # Grant permissions
        dynamodb_table.grant_read_write_data(lambda_function)
        db_secret.grant_read(lambda_function)
