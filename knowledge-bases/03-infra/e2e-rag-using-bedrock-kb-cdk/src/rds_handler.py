import os

from aws_lambda_powertools import Logger

from amazon_bedrock_knowledge_base_infra_setup_lambda.client_utils import (
    get_rds_data_api_client,
    get_secret_manager_client,
    get_session,
)
from amazon_bedrock_knowledge_base_infra_setup_lambda.rds_utils import (
    create,
    delete,
    get_embedding_dimension,
)

logger = Logger(service="amazon_bedrock_knowledge_base_infra_setup_lambda", level="INFO")

"""
Custom resources: https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.custom_resources-readme.html
Please read the above docs to understand how custom resources work. The idea here is to provide a Lambda to the custom resource Provider. This
Lambda should know how to create, update and delete the resource in question.
In this case, the resource includes the vector extension, schema, role and table required for Bedrock KB to work with RDS.
"""


@logger.inject_lambda_context(log_event=True)
def handler(event, context):
    logger.info(event)
    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception("Invalid request type: %s" % request_type)


"""
During a creation event:
1. We create the vector extension first if it does not exist.
2. We create the schema if it does not exist.
3. We create the role.
4. We grant permissions to the role for the schema.
5. We create the table with columns "embedding", "chunks" and "metadata".

We are using f"{database_name}-{schema_name}-{table_name}-{user_name}" as the physical resource id
because it serves as the identifier for all the resources we create.
"""


def on_create(event):
    props = event["ResourceProperties"]
    logger.info("Create new RDS schema and table for props: %s" % props)
    region = os.environ["AWS_REGION"]
    database_name = props["database_name"]
    table_name = props["table_name"]
    schema_name = props["schema_name"]
    user_name = props["user_name"]
    rds_cluster_arn = props["cluster_arn"]
    rds_secret_arn = props["secret_arn"]
    embedding_model_id = props["embedding_model_id"]
    emb_dim = get_embedding_dimension(embedding_model_id)

    session = get_session()
    rds_data_api_client = get_rds_data_api_client(session, region)
    secretsmanager_client = get_secret_manager_client(session, region)

    create(
        rds_data_api_client,
        secretsmanager_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        table_name,
        schema_name,
        user_name,
        emb_dim,
    )

    return {"PhysicalResourceId": f"{database_name}-{schema_name}-{table_name}-{user_name}"}


"""
During an update event:
1. We first check if the old and new resource properties are identical. If they are, we do nothing.
2. If the old and new resource props are not identical:
a. We delete the old table, user, schema and extension.
b. We create the new extension, schema, user and table.

We return f"{database_name}-{schema_name}-{table_name}-{user_name}" (of the new resources)
as the physical resource id because it serves as the identifier.
"""


def on_update(event):
    props = event["ResourceProperties"]
    old_props = event["OldResourceProperties"]
    logger.info(
        "Updating RDS schema and table for new props %s, old props: %s" % (props, old_props)
    )
    physical_id = event["PhysicalResourceId"]

    if old_props == props:
        logger.info("Props are same, nothing to do")
        return {"PhysicalResourceId": physical_id}

    logger.info("New props are different from old props. Table requires re-creation")
    region = os.environ["AWS_REGION"]

    old_database_name = old_props["database_name"]
    old_table_name = old_props["table_name"]
    old_rds_cluster_arn = old_props["cluster_arn"]
    old_rds_secret_arn = old_props["secret_arn"]
    old_schema_name = old_props["schema_name"]
    old_user_name = old_props["user_name"]

    database_name = props["database_name"]
    table_name = props["table_name"]
    rds_cluster_arn = props["cluster_arn"]
    rds_secret_arn = props["secret_arn"]
    schema_name = props["schema_name"]
    user_name = props["user_name"]
    embedding_model_id = props["embedding_model_id"]
    emb_dim = get_embedding_dimension(embedding_model_id)

    session = get_session()
    rds_data_api_client = get_rds_data_api_client(session, region)
    secretsmanager_client = get_secret_manager_client(session, region)

    delete(
        rds_data_api_client,
        old_rds_cluster_arn,
        old_rds_secret_arn,
        old_database_name,
        old_table_name,
        old_schema_name,
        old_user_name,
    )

    create(
        rds_data_api_client,
        secretsmanager_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        table_name,
        schema_name,
        user_name,
        emb_dim,
    )

    return {"PhysicalResourceId": f"{database_name}-{schema_name}-{table_name}-{user_name}"}


"""
During a delete event:
1. We delete the table if it exists.
2. We revoke permissions from the role for the schema.
3. We delete the role.
4. We delete the schema if it exists.
5. We delete the vector extension first if it exista.

We return f"{database_name}-{schema_name}-{table_name}-{user_name}" (of the resources being deleted)
as the physical resource id because it serves as the identifier.
"""


def on_delete(event):
    props = event["ResourceProperties"]
    logger.info("Deleting RDS schema and tables for props: %s" % props)
    region = os.environ["AWS_REGION"]
    database_name = props["database_name"]
    table_name = props["table_name"]
    schema_name = props["schema_name"]
    user_name = props["user_name"]
    rds_cluster_arn = props["cluster_arn"]
    rds_secret_arn = props["secret_arn"]

    session = get_session()
    rds_data_api_client = get_rds_data_api_client(session, region)

    delete(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        table_name,
        schema_name,
        user_name,
    )

    return {"PhysicalResourceId": f"{database_name}-{schema_name}-{table_name}-{user_name}"}