import boto3
from aws_lambda_powertools import Logger
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = Logger(service="amazon_bedrock_knowledge_base_infra_setup_lambda", level="INFO")


def get_session():
    return boto3.Session()


def get_credentials(session):
    return session.get_credentials()


def get_caller_id(sts_client):
    return sts_client.get_caller_identity()


def get_caller_arn(sts_client):
    logger.info("Getting caller arn")
    caller_id = get_caller_id(sts_client)
    caller_arn = caller_id["Arn"]
    logger.info("Caller arn: {}".format(caller_arn))
    return caller_arn


def get_sts_client(session, region):
    return session.client("sts", region_name=region)


def get_oss_client(session, region):
    return session.client("opensearchserverless", region_name=region)


def get_oss_http_client(session, region, host):
    credentials = get_credentials(session)
    access_key = credentials.access_key
    secret_key = credentials.secret_key
    session_token = credentials.token
    awsauth = AWS4Auth(access_key, secret_key, region, "aoss", session_token=session_token)

    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300,
    )


def get_rds_data_api_client(session, region):
    return session.client("rds-data", region_name=region)


def get_secret_manager_client(session, region):
    return session.client("secretsmanager", region_name=region)