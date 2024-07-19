import json
import re
from datetime import datetime
from time import sleep
import os

from aws_lambda_powertools import Logger
from opensearchpy import NotFoundError

logger = Logger(service="amazon_bedrock_knowledge_base_infra_setup_lambda", level="INFO")

vector_field_name = os.environ.get('VECTOR_FIELD_NAME')
metadata_field_name = os.environ.get('METADATA_FIELD_NAME')
text_field_name = os.environ.get('TEXT_FIELD_NAME')


MODEL_ID_TO_INDEX_REQUEST_MAP = {
    "amazon.titan-embed-text-v1": {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                        "space_type": "l2",
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": "false"},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": "true"},
            }
        },
    },
    "amazon.titan-embed-text-v2:0": {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                        "space_type": "l2",
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": "false"},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": "true"},
            }
        },
    },
    "cohere.embed-english-v3": {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                        "space_type": "l2",
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": "false"},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": "true"},
            }
        },
    },
}


def get_access_policy(oss_client, policy_name):
    policy_response = oss_client.get_access_policy(name=policy_name, type="data")
    policy_details = policy_response["accessPolicyDetail"]
    policy_version = policy_details["policyVersion"]
    return {
        "Policy": policy_details["policy"],
        "Version": policy_version,
        "PolicyName": policy_name,
    }


def update_access_policy(oss_client, updated_policy, policy_version, policy_name):
    logger.info(updated_policy)
    response = oss_client.update_access_policy(
        name=policy_name,
        policyVersion=policy_version,
        policy=json.dumps(updated_policy),
        description="Policy updated at {}".format(datetime.now()),
        type="data",
    )
    logger.info(response)
    logger.info("Updated data access policy, sleeping for 2 minutes for permissions to propagate")
    sleep(120)


def get_updated_access_policy_with_caller_arn(policy, caller_arn):
    policy_copy = list(policy)
    existing_principals = policy_copy[0]["Principal"]
    if caller_arn not in existing_principals:
        policy_copy[0]["Principal"] = [*existing_principals, caller_arn]
    return policy_copy


def create_index(oss_http_client, index_name, request_body):
    return oss_http_client.indices.create(index_name, body=request_body)


def create_index_with_retries(oss_http_client, index_name, request_body):
    attempts = 0
    while attempts < 10:
        try:
            response = create_index(oss_http_client, index_name, request_body)
            logger.info(response)
            logger.info(
                "Created index {}, sleeping for 2 minutes for index to get ready".format(index_name)
            )
            sleep(120)
            return response
        except Exception as e:
            logger.info("Caught: " + str(e))
            logger.info("Sleeping for 10 seconds and retrying.")
            sleep(10)
            attempts += 1
            if attempts == 10:
                raise e


def delete_index_if_present(oss_http_client, index_name):
    try:
        response = oss_http_client.indices.delete(index=index_name)
        logger.info(response)
        logger.info("Deleted index {}, sleeping for 1 min".format(index_name))
        sleep(60)
        return response
    except NotFoundError:
        logger.info("Index {} not found, skipping deletion".format(index_name))
    except Exception as e:
        logger.info("Deletion of index {} failed, reason: {}".format(index_name, e))


def get_host_from_collection_endpoint(collection_endpoint):
    return re.sub(r"https?://", "", collection_endpoint)