import boto3
import json
import time
import sys

# Load configuration
with open("config.json", "r") as f:
    config = json.load(f)

# Get current AWS region dynamically
session = boto3.Session()
aws_region = session.region_name or "us-west-2"  # fallback to us-west-2 if not set
print(f"Using AWS region: {aws_region}")

# Initialize clients with dynamic region
ec2 = boto3.client("ec2", region_name=aws_region)
rds = boto3.client("rds", region_name=aws_region)
secrets = boto3.client("secretsmanager", region_name=aws_region)

print("Starting cleanup of AWS resources...")

# Delete Aurora instance first
try:
    print("Deleting Aurora instance...")
    rds.delete_db_instance(
        DBInstanceIdentifier=config["aurora"]["instance_identifier"],
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True,
    )

    # Wait for instance to be deleted
    print("Waiting for instance deletion...")
    while True:
        try:
            response = rds.describe_db_instances(
                DBInstanceIdentifier=config["aurora"]["instance_identifier"]
            )
            status = response["DBInstances"][0]["DBInstanceStatus"]
            print(f"Instance status: {status}")

            if status == "deleting":
                time.sleep(30)
                continue
            else:
                break

        except Exception as e:
            if "DBInstanceNotFound" in str(e):
                print("Aurora instance deleted")
                break
            else:
                raise
except Exception as e:
    print(f"Instance deletion error (might not exist): {e}")

# Delete Aurora cluster
try:
    print("Deleting Aurora cluster...")
    rds.delete_db_cluster(
        DBClusterIdentifier=config["aurora"]["cluster_identifier"],
        SkipFinalSnapshot=True,
    )

    # Wait for cluster to be deleted
    print("Waiting for cluster deletion...")
    while True:
        try:
            response = rds.describe_db_clusters(
                DBClusterIdentifier=config["aurora"]["cluster_identifier"]
            )
            status = response["DBClusters"][0]["Status"]
            print(f"Cluster status: {status}")

            if status == "deleting":
                time.sleep(30)
                continue
            else:
                break

        except Exception as e:
            if "DBClusterNotFoundFault" in str(e):
                print("Aurora cluster deleted")
                break
            else:
                raise
except Exception as e:
    print(f"Cluster deletion error (might not exist): {e}")

# Delete DB subnet group (now that cluster is deleted)
try:
    print("Deleting DB subnet group...")
    rds.delete_db_subnet_group(
        DBSubnetGroupName=config["resources"]["subnet_group_name"]
    )
    print("DB subnet group deleted")
except Exception as e:
    print(f"DB subnet group deletion error: {e}")

# Find and delete the secret (skip RDS-managed secrets)
try:
    print("Finding and deleting secrets...")
    secrets_list = secrets.list_secrets()
    for secret in secrets_list["SecretList"]:
        # Only delete user-created secrets, not RDS-managed ones
        if config["aurora"]["cluster_identifier"] in secret["Name"] and not secret[
            "Name"
        ].startswith("rds!"):
            try:
                secrets.delete_secret(
                    SecretId=secret["ARN"], ForceDeleteWithoutRecovery=True
                )
                print(f"Deleted secret: {secret['Name']}")
            except Exception as e:
                print(f"Could not delete secret {secret['Name']}: {e}")
except Exception as e:
    print(f"Secret deletion error: {e}")

# Get VPC details
try:
    vpcs = ec2.describe_vpcs(
        Filters=[{"Name": "cidr-block", "Values": [config["vpc"]["cidr_block"]]}]
    )["Vpcs"]

    if not vpcs:
        print("VPC not found - cleanup complete")
        sys.exit(0)

    vpc_id = vpcs[0]["VpcId"]
    print(f"Found VPC to cleanup: {vpc_id}")

    # Delete security groups (except default) - but first remove their rules
    try:
        sgs = ec2.describe_security_groups(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["SecurityGroups"]

        # First, remove all ingress and egress rules from custom security groups
        for sg in sgs:
            if sg["GroupName"] != "default":
                try:
                    # Remove ingress rules
                    if sg["IpPermissions"]:
                        ec2.revoke_security_group_ingress(
                            GroupId=sg["GroupId"], IpPermissions=sg["IpPermissions"]
                        )
                    # Remove egress rules
                    if sg["IpPermissionsEgress"]:
                        ec2.revoke_security_group_egress(
                            GroupId=sg["GroupId"],
                            IpPermissions=sg["IpPermissionsEgress"],
                        )
                except Exception as e:
                    print(
                        f"Error removing rules from security group {sg['GroupId']}: {e}"
                    )

        # Now delete the security groups
        for sg in sgs:
            if sg["GroupName"] != "default":
                try:
                    print(f"Deleting security group: {sg['GroupId']}")
                    ec2.delete_security_group(GroupId=sg["GroupId"])
                except Exception as e:
                    print(f"Security group deletion error for {sg['GroupId']}: {e}")
    except Exception as e:
        print(f"Security group deletion error: {e}")

    # Get subnets
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
        "Subnets"
    ]

    # Detach and delete Internet Gateway FIRST (before route tables)
    try:
        igws = ec2.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
        )["InternetGateways"]

        for igw in igws:
            igw_id = igw["InternetGatewayId"]
            print(f"Detaching and deleting Internet Gateway: {igw_id}")
            ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
            ec2.delete_internet_gateway(InternetGatewayId=igw_id)
    except Exception as e:
        print(f"Internet Gateway deletion error: {e}")

    # Delete route table associations and custom route tables (after IGW is detached)
    try:
        route_tables = ec2.describe_route_tables(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["RouteTables"]

        for rt in route_tables:
            # Skip the main route table
            if not any(assoc.get("Main", False) for assoc in rt["Associations"]):
                try:
                    print(f"Deleting route table: {rt['RouteTableId']}")
                    ec2.delete_route_table(RouteTableId=rt["RouteTableId"])
                except Exception as e:
                    print(f"Route table deletion error for {rt['RouteTableId']}: {e}")
    except Exception as e:
        print(f"Route table deletion error: {e}")

    # Delete subnets
    for subnet in subnets:
        try:
            print(f"Deleting subnet: {subnet['SubnetId']}")
            ec2.delete_subnet(SubnetId=subnet["SubnetId"])
        except Exception as e:
            print(f"Subnet deletion error for {subnet['SubnetId']}: {e}")

    # Wait for all resources to be fully cleaned up before attempting VPC deletion
    print("Waiting for all resources to be fully cleaned up before VPC deletion...")
    time.sleep(30)  # Increased wait time

    # Delete VPC as the very last step
    try:
        print(f"Attempting to delete VPC: {vpc_id}")
        ec2.delete_vpc(VpcId=vpc_id)
        print("✅ VPC deleted successfully")
    except Exception as e:
        print(f"❌ VPC deletion failed: {e}")
        print(
            "   This is common on first run. Try running clean.py again to complete VPC deletion."
        )

except Exception as e:
    print(f"Error during cleanup: {e}", flush=True)
