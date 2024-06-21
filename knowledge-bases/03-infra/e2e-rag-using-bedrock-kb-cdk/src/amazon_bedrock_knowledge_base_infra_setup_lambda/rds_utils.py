import json

from aws_lambda_powertools import Logger

logger = Logger(service="amazon_bedrock_knowledge_base_infra_setup_lambda", level="INFO")


def create(
    rds_data_api_client,
    secretsmanager_client,
    rds_cluster_arn,
    rds_secret_arn,
    database_name,
    table_name,
    schema_name,
    user_name,
    emb_dim,
):
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        r"CREATE EXTENSION IF NOT EXISTS vector;",
    )
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"CREATE SCHEMA IF NOT EXISTS {schema_name};",
    )

    secret_value = secretsmanager_client.get_secret_value(SecretId=rds_secret_arn)
    password = json.loads(secret_value["SecretString"])["password"]
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"CREATE ROLE {user_name} WITH PASSWORD '{password}' LOGIN;",
    )

    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"GRANT ALL ON SCHEMA {schema_name} TO {user_name};",
    )
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (id uuid PRIMARY KEY, embedding vector({emb_dim}), chunks text, metadata json);",
    )


def delete(
    rds_data_api_client,
    rds_cluster_arn,
    rds_secret_arn,
    database_name,
    table_name,
    schema_name,
    user_name,
):
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"DROP TABLE IF EXISTS {schema_name}.{table_name};",
        True,
    )
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"REVOKE ALL ON SCHEMA {schema_name} FROM {user_name};",
        True,
    )
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"DROP ROLE IF EXISTS {user_name};",
        True,
    )
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        f"DROP SCHEMA IF EXISTS {schema_name};",
        True,
    )
    execute_sql_statement(
        rds_data_api_client,
        rds_cluster_arn,
        rds_secret_arn,
        database_name,
        r"DROP EXTENSION IF EXISTS vector;",
        True,
    )


def execute_sql_statement(
    rds_data_api_client,
    rds_cluster_arn,
    rds_secret_arn,
    database_name,
    statement,
    ignore_error=False,
):
    try:
        logger.info("Executing: {}".format(statement))
        response = rds_data_api_client.execute_statement(
            resourceArn=rds_cluster_arn,
            secretArn=rds_secret_arn,
            database=database_name,
            sql=statement,
        )
        logger.info(response)
    except Exception as e:
        logger.error("Error executing statment {}: {}".format(statement, str(e)))
        if not ignore_error:
            raise e


def get_embedding_dimension(embedding_model_id):
    if embedding_model_id == "amazon.titan-embed-text-v1":
        return 1536
    elif embedding_model_id == "cohere.embed-english-v3":
        return 1024
    else:
        raise Exception("Unsupported embedding model id {} provided!".format(embedding_model_id))