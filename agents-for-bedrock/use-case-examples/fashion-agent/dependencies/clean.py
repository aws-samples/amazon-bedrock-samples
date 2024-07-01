from config import *

# Empty and delete S3 Bucket
try:
    objects = s3_client.list_objects(Bucket=bucket_name)
    if "Contents" in objects:
        for obj in objects["Contents"]:
            s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
    s3_client.delete_bucket(Bucket=bucket_name)
except:
    pass

# Delete Agent
list_agent = bedrock_agent_client.list_agents()["agentSummaries"]
agent_id = next(
    (agent["agentId"] for agent in list_agent if agent["agentName"] == agent_name), None
)

print(agent_id)
try:
    response = bedrock_agent_client.list_agent_action_groups(
        agentId=agent_id,
        agentVersion="1",
    )
    list_action_group = response["actionGroupSummaries"]
    print(list_action_group)

    action_group_name = "imagevar"

    action_group_id = next(
        (
            agent["actionGroupId"]
            for agent in list_action_group
            if agent["actionGroupName"] == action_group_name
        ),
        None,
    )
    print(action_group_id)

    response = bedrock_agent_client.list_agent_aliases(
        agentId=agent_id,
    )
    print(response["agentAliasSummaries"])
    print(type(response["agentAliasSummaries"]))
    agentAliasId = next(
        (
            agent["agentAliasId"]
            for agent in response["agentAliasSummaries"]
            if agent["agentAliasName"] == agent_alias_name
        ),
        None,
    )
    agentAliasId
except:
    pass

lambda_name = f"{agent_name}-{suffix}"
print(lambda_name)
try:
    resp = lambda_client.get_function(FunctionName=lambda_name)
    print(resp["Configuration"]["FunctionArn"])
    FunctionArn = resp["Configuration"]["FunctionArn"]

    response = bedrock_agent_client.update_agent_action_group(
        agentId=agent_id,
        agentVersion="DRAFT",
        actionGroupId=action_group_id,
        actionGroupName=action_group_name,
        actionGroupExecutor={"lambda": FunctionArn},
        apiSchema={"s3": {"s3BucketName": bucket_name, "s3ObjectKey": bucket_key}},
        actionGroupState="DISABLED",
    )

    action_group_deletion = bedrock_agent_client.delete_agent_action_group(
        agentId=agent_id, agentVersion="DRAFT", actionGroupId=action_group_id
    )
except:
    pass

try:
    agent_alias_deletion = bedrock_agent_client.delete_agent_alias(
        agentId=agent_id, agentAliasId=agentAliasId
    )
except:
    pass
try:
    agent_deletion = bedrock_agent_client.delete_agent(agentId=agent_id)
except:
    pass

try:
    # Delete Lambda function
    lambda_client.delete_function(FunctionName=lambda_name)
except:
    pass

try:
    for role_name in [agent_role_name]:
        iam_client.delete_role(RoleName=role_name)

    for role_name in [lambda_role_name]:
        iam_client.delete_role(RoleName=role_name)
except:
    pass


# Initialize the IAM client

# The name of the policy you want to delete
# bedrock_agent_bedrock_allow_policy_name = 'YourPolicyNameHere'


def delete_policy_by_name(policy_name):
    # List all policies
    paginator = iam_client.get_paginator("list_policies")
    for response in paginator.paginate(Scope="Local"):
        for policy in response["Policies"]:
            if policy["PolicyName"] == policy_name:
                policy_arn = policy["Arn"]

                # Detach the policy from all roles
                response = iam_client.list_entities_for_policy(PolicyArn=policy_arn)
                for role in response["PolicyRoles"]:
                    role_name = role["RoleName"]
                    iam_client.detach_role_policy(
                        RoleName=role_name, PolicyArn=policy_arn
                    )

                # Delete the policy by ARN
                try:
                    iam_client.delete_policy(PolicyArn=policy_arn)
                    print(f"Policy '{policy_name}' deleted successfully.")
                    return
                except Exception as e:
                    print(f"Error deleting policy '{policy_name}':", e)
                    return
    print(f"Policy '{policy_name}' not found.")


try:
    # Example usage
    delete_policy_by_name(bedrock_agent_bedrock_allow_policy_name)
    delete_policy_by_name(bedrock_agent_s3_allow_policy_name)
except:
    pass

# Delete Roles
for role_name in [agent_role_name, lambda_role_name]:
    try:
        # Detach all policies from the role
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in response["AttachedPolicies"]:
            policy_arn = policy["PolicyArn"]
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        # Delete all inline policies from the role
        response = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in response["PolicyNames"]:
            iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

        # Delete the role
        iam_client.delete_role(RoleName=role_name)
        print(f"Role '{role_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting roles: {e}")

# Delete Policies for OpenSearchServerless
try:
    # Delete encryption policy
    response = aoss_client.delete_security_policy(
        name="{}-policy".format(collection_name), type="encryption"
    )
    print(f"Encryption policy '{collection_name}-policy' deleted successfully.")

    # Delete network policy
    response = aoss_client.delete_security_policy(
        name="{}-policy".format(collection_name), type="network"
    )
    print(f"Network policy '{collection_name}-policy' deleted successfully.")

    # Delete data access policy
    response = aoss_client.delete_access_policy(
        name="{}-policy".format(collection_name), type="data"
    )
    print(f"Data access policy '{collection_name}-policy' deleted successfully.")

except Exception as e:
    print(f"Error cleaning up resources: {e}")

# Delete Collection for OpenSearchServerless
try:
    # Delete collection
    response = aoss_client.delete_collection(id=aoss_collection_id)
    print(f"Collection '{aoss_collection_id}' deleted successfully.")

except Exception as e:
    print(f"Error cleaning up resources: {e}")

# Delete updated lines in Config.py
try:
    if aoss_collection_id:
        with open("dependencies/config.py", "r") as f:
            lines = f.readlines()
        with open("dependencies/config.py", "w") as f:
            f.writelines(lines[:-5])  # Remove aoss_collection_id and aoss_host
        print("aoss_collection_id and aoss_host removed from config.py")
except Exception as e:
    print(f"Config.py not change")
