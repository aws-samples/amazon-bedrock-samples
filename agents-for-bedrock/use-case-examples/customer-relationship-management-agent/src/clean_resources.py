import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import sys

# boto3  clients
s3 = boto3.client("s3")
iam = boto3.client("iam")
lambda_client = boto3.client("lambda")
agent = boto3.client("bedrock-agent")
ssm = boto3.client("ssm")
dynamodb = boto3.client("dynamodb")
session = boto3.session.Session()

# Command line arguments
ENV = sys.argv[1]
BUCKET_NAME = sys.argv[2]

# Global variables
AGENT_NAME = f"crm-agent-{ENV}"
CUSTOMER_TABLE = f"customer-{ENV}"
INTERACTIONS_TABLE = f"interactions-{ENV}"
LAMBDA_NAME = f"crm-lambda-action-{ENV}"
LAMBDA_ROLE_NAME = f"lambda-role-{ENV}"
AGENT_ROLE_NAME = f"AmazonBedrockExecutionRoleForAgents_{ENV}"

if_agent_deleted = False

def delete_if_resource_exists(client_exception, resource_type):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except client_exception as e:
                print(f"{resource_type} does not exist.")
            except (NoCredentialsError, PartialCredentialsError) as e:
                print(
                    "Credentials not available. Please configure your AWS credentials."
                )
            except Exception as e:
                print(f"An error occurred: {e}")

        return wrapper

    return decorator


@delete_if_resource_exists(s3.exceptions.NoSuchBucket, "Bucket")
def check_and_empty_bucket(bucket_name):
    response = s3.head_bucket(Bucket=bucket_name)
    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        bucket = boto3.resource("s3").Bucket(bucket_name)
        bucket.object_versions.delete()
        bucket.objects.all().delete()


@delete_if_resource_exists(iam.exceptions.NoSuchEntityException, "IAM Role")
def check_and_delete_iam_role(role_name):
    # Check if the IAM role exists
    iam.get_role(RoleName=role_name)

    # If the role exists, delete it
    print(f"IAM Role '{role_name}' exists. Deleting the IAM Role...")

    # Delete inline policies attached to the role
    inline_policies = iam.list_role_policies(RoleName=role_name).get("PolicyNames", [])
    for inline_policy in inline_policies:
        print(f"Deleting Inline policy {inline_policy}")
        iam.delete_role_policy(RoleName=role_name, PolicyName=inline_policy)

    # Detach and delete policies attached to the role
    attached_policies = iam.list_attached_role_policies(RoleName=role_name).get(
        "AttachedPolicies", []
    )
    for policy in attached_policies:
        print(f"Deleting attached policy {policy}")
        iam.detach_role_policy(RoleName=role_name, PolicyArn=policy["PolicyArn"])
        try:
            iam.delete_policy(PolicyArn=policy["PolicyArn"])
        except Exception as ex:
            print("AWS Managed Policy not deleted")

    # Delete the IAM role
    iam.delete_role(RoleName=role_name)

    print("IAM Role deleted successfully.")


@delete_if_resource_exists(
    lambda_client.exceptions.ResourceNotFoundException, "Lambda function"
)
def check_and_delete_lambda_function(function_name):
    # Check if the Lambda function exists
    lambda_client.get_function(FunctionName=function_name)

    # If the function exists, delete it
    print(f"Lambda function '{function_name}' exists. Deleting the Lambda function...")

    # Delete the Lambda function
    lambda_client.delete_function(FunctionName=function_name)

    print("Lambda function deleted successfully.")


@delete_if_resource_exists(agent.exceptions.ResourceNotFoundException, "Agent")
def check_and_delete_bedrock_agent():
    global if_agent_deleted
    print(f"Deleting Agent")

    AGENT_ID = session.client("ssm").get_parameter(
        Name=f"/streamlitapp/{ENV}/AGENT_ID", WithDecryption=True
    )["Parameter"]["Value"]
    print(f"Deleting Agent {AGENT_ID}")

    # Check if the Agent exists
    agent.get_agent(agentId=AGENT_ID)

    # If the agent exists, delete it
    print(f"Bedrock Agent '{AGENT_ID}' exists. Deleting the Agent...")

    agent.delete_agent(agentId=AGENT_ID, skipResourceInUseCheck=True)

    print("Bedrock agent deleted successfully.")

    if_agent_deleted = True


@delete_if_resource_exists(ssm.exceptions.ParameterNotFound, "SSM Parameter")
def check_and_delete_ssm_parameter(parameter_name):
    # Check if the SSM parameter exists
    ssm.get_parameter(Name=parameter_name)

    # If the parameter exists, delete it
    print(f"SSM parameter '{parameter_name}' exists. Deleting...")

    # Delete the SSM parameter
    ssm.delete_parameter(Name=parameter_name)

    print("SSM parameter deleted successfully.")


def delete_dynamodb_table(table_name):
    # Check if the table exists
    existing_tables = dynamodb.list_tables()["TableNames"]
    if table_name in existing_tables:
        # Table exists, so delete it
        dynamodb.delete_table(TableName=table_name)
        print(f"Table '{table_name}' deleted successfully.")
    else:
        print(f"Table '{table_name}' does not exist.")


if __name__ == "__main__":
    # Empty bucket
    check_and_empty_bucket(BUCKET_NAME)

    # Delete Lambda
    check_and_delete_lambda_function(function_name=LAMBDA_NAME)

    # Delete Lambda role
    check_and_delete_iam_role(role_name=LAMBDA_ROLE_NAME)

    # Delete Agent
    check_and_delete_bedrock_agent()
    # print(if_agent_deleted)

    # Delete Agent role an Polices
    check_and_delete_iam_role(role_name=AGENT_ROLE_NAME)

    # Delete SSM Parameter
    if if_agent_deleted:
        check_and_delete_ssm_parameter(
            parameter_name=f"/streamlitapp/{ENV}/AGENT_ID"
        )
    check_and_delete_ssm_parameter(
        parameter_name=f"/streamlitapp/{ENV}/AGENT_ALIAS_ID"
    )

    # DynamoTables
    delete_dynamodb_table(CUSTOMER_TABLE)
    delete_dynamodb_table(INTERACTIONS_TABLE)
