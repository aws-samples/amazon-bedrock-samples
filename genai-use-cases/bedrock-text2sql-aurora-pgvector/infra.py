import boto3
import json
import time
import sys

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Get current AWS region dynamically
session = boto3.Session()
aws_region = session.region_name or 'us-west-2'  # fallback to us-west-2 if not set
print(f"Using AWS region: {aws_region}")

# Initialize clients with dynamic region
ec2 = boto3.client('ec2', region_name=aws_region)
rds = boto3.client('rds', region_name=aws_region)

# Create VPC
vpc = ec2.create_vpc(CidrBlock=config['vpc']['cidr_block'])
vpc_id = vpc['Vpc']['VpcId']
print(f"Created VPC: {vpc_id}")

# Get availability zones
azs = ec2.describe_availability_zones()['AvailabilityZones'][:3]
az_names = [az['ZoneName'] for az in azs]

# Create subnets in 3 AZs
subnet_ids = []
for i, az in enumerate(az_names):
    subnet = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock=config['vpc']['subnet_cidrs'][i],
        AvailabilityZone=az
    )
    subnet_ids.append(subnet['Subnet']['SubnetId'])
    print(f"Created subnet {subnet['Subnet']['SubnetId']} in {az}")

# Create Internet Gateway
igw = ec2.create_internet_gateway()
igw_id = igw['InternetGateway']['InternetGatewayId']
ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

# Create route table and add route to IGW
rt = ec2.create_route_table(VpcId=vpc_id)
rt_id = rt['RouteTable']['RouteTableId']
ec2.create_route(RouteTableId=rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)

# Associate subnets with route table
for subnet_id in subnet_ids:
    ec2.associate_route_table(RouteTableId=rt_id, SubnetId=subnet_id)

# Create security group for Aurora
sg = ec2.create_security_group(
    GroupName=config['resources']['security_group_name'],
    Description='Aurora PostgreSQL security group',
    VpcId=vpc_id
)
sg_id = sg['GroupId']

# Allow PostgreSQL access within VPC
ec2.authorize_security_group_ingress(
    GroupId=sg_id,
    IpPermissions=[{
        'IpProtocol': 'tcp',
        'FromPort': 5432,
        'ToPort': 5432,
        'IpRanges': [{'CidrIp': config['vpc']['cidr_block']}]
    }]
)

# Create DB subnet group
rds.create_db_subnet_group(
    DBSubnetGroupName=config['resources']['subnet_group_name'],
    DBSubnetGroupDescription='Aurora subnet group',
    SubnetIds=subnet_ids
)

# Create Aurora PostgreSQL Serverless v2 cluster
cluster = rds.create_db_cluster(
    DBClusterIdentifier=config['aurora']['cluster_identifier'],
    Engine='aurora-postgresql',
    EngineMode='provisioned',
    DatabaseName=config['aurora']['database_name'],
    MasterUsername=config['aurora']['master_username'],
    ManageMasterUserPassword=True,
    VpcSecurityGroupIds=[sg_id],
    DBSubnetGroupName=config['resources']['subnet_group_name'],
    StorageType='aurora',
    EnableHttpEndpoint=True,
    MonitoringInterval=0,
    ServerlessV2ScalingConfiguration={
        'MinCapacity': config['aurora']['min_capacity'],
        'MaxCapacity': config['aurora']['max_capacity']
    }
)

print(f"Created Aurora cluster: {cluster['DBCluster']['DBClusterIdentifier']}")

# Wait for cluster to be available
print("Waiting for cluster to be available...")
while True:
    try:
        response = rds.describe_db_clusters(DBClusterIdentifier=config['aurora']['cluster_identifier'])
        status = response['DBClusters'][0]['Status']
        print(f"Cluster status: {status}")
        
        if status == 'available':
            break
        elif status in ['failed', 'deleted', 'deleting']:
            raise Exception(f"Cluster creation failed with status: {status}")
        
        time.sleep(30)
    except Exception as e:
        if 'DBClusterNotFoundFault' in str(e):
            raise Exception("Cluster creation failed - cluster not found")
        raise

# Create Aurora instance
instance = rds.create_db_instance(
    DBInstanceIdentifier=config['aurora']['instance_identifier'],
    DBInstanceClass='db.serverless',
    Engine='aurora-postgresql',
    DBClusterIdentifier=config['aurora']['cluster_identifier']
)

print(f"Created Aurora instance: {instance['DBInstance']['DBInstanceIdentifier']}")

# Wait for instance to be available
print("Waiting for instance to be available...")
while True:
    try:
        response = rds.describe_db_instances(DBInstanceIdentifier=config['aurora']['instance_identifier'])
        status = response['DBInstances'][0]['DBInstanceStatus']
        print(f"Instance status: {status}", flush=True)
        
        if status == 'available':
            print("✅ Aurora instance is now available!", flush=True)
            break
        elif status in ['failed', 'deleted', 'deleting']:
            raise Exception(f"Instance creation failed with status: {status}")
        
        print("⏳ Waiting 30 seconds before next status check...", flush=True)
        time.sleep(30)
    except Exception as e:
        if 'DBInstanceNotFound' in str(e):
            raise Exception("Instance creation failed - instance not found")
        raise

print("Infrastructure deployment completed!", flush=True)
print(f"VPC ID: {vpc_id}", flush=True)
print(f"Cluster: {config['aurora']['cluster_identifier']}", flush=True)
print(f"Database: {config['aurora']['database_name']}", flush=True)

# Get the cluster ARN and secrets ARN for dynamic linking
cluster_arn = cluster['DBCluster']['DBClusterArn']
secrets_arn = cluster['DBCluster']['MasterUserSecret']['SecretArn']

print("\n" + "="*80)
print("📋 COPY THESE VALUES TO YOUR JUPYTER NOTEBOOK:")
print("="*80)
print("# Database connection configuration")
print("# Replace the hardcoded values in your notebook with these:")
print(f"CLUSTER_ARN = '{cluster_arn}'")
print(f"SECRET_ARN = '{secrets_arn}'")
print(f"DATABASE_NAME = '{config['aurora']['database_name']}'")
print(f"AWS_REGION = '{aws_region}'")
print("="*80)

# Natural completion for Jupyter notebook compatibility
print("✅ Infrastructure deployment completed successfully!", flush=True)