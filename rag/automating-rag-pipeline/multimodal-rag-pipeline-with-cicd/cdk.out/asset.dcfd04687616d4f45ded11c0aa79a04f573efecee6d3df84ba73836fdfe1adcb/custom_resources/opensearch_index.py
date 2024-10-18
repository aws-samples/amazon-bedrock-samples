#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import logging
import os
import time
from typing import Sequence, TypedDict

import boto3
from custom_resources.cr_types import CustomResourceRequest, CustomResourceResponse
from opensearchpy import (
    AuthorizationException,
    AWSV4SignerAuth,
    OpenSearch,
    RequestsHttpConnection,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class MetadataManagementField(TypedDict):
    MappingField: str
    DataType: str
    Filterable: bool


class AnalyzerProperties(TypedDict):
    CharacterFilters: Sequence[str]
    Tokenizer: str
    TokenFilters: Sequence[str]


class VectorIndexProperties(TypedDict):
    Endpoint: str
    IndexName: str
    VectorField: str
    Dimensions: int | str
    MetadataManagement: Sequence[MetadataManagementField]
    Analyzer: AnalyzerProperties | None


def validate_event(event: CustomResourceRequest[VectorIndexProperties]) -> bool:
    if event["ResourceProperties"] is None:
        raise ValueError("ResourceProperties is required")
    if event["ResourceProperties"]["Endpoint"] is None:
        raise ValueError("Endpoint is required")
    if event["ResourceProperties"]["IndexName"] is None:
        raise ValueError("IndexName is required")
    if event["RequestType"] in ["Create", "Update"]:
        if event["ResourceProperties"]["VectorField"] is None:
            raise ValueError("VectorField is required")
        if event["ResourceProperties"]["Dimensions"] is None:
            raise ValueError("Dimensions is required")
        if isinstance(int(event["ResourceProperties"]["Dimensions"]), int) is False:
            raise ValueError("Dimensions must be an integer")
        if event["ResourceProperties"]["MetadataManagement"] is None:
            raise ValueError("MetadataManagement is required")
        if event["RequestType"] == "Update" and event["PhysicalResourceId"] is None:
            raise ValueError("PhysicalResourceId is required")
        if event["ResourceProperties"].get("Analyzer") is not None:
            analyzer = event["ResourceProperties"]["Analyzer"]
            if analyzer["CharacterFilters"] is None:
                raise ValueError("CharacterFilters is required")
            if analyzer["Tokenizer"] is None:
                raise ValueError("Tokenizer is required")
            if analyzer["TokenFilters"] is None:
                raise ValueError("TokenFilters is required")
    elif event["RequestType"] == "Delete":
        if event["PhysicalResourceId"] is None:
            raise ValueError("PhysicalResourceId is required")
    else:
        raise ValueError(f"Unsupported RequestType: {event['RequestType']}")
    if event["ResponseURL"] is None:
        raise ValueError("ResponseURL is required")
    if event["StackId"] is None:
        raise ValueError("StackId is required")
    if event["RequestId"] is None:
        raise ValueError("RequestId is required")
    if event["ResourceType"] is None:
        raise ValueError("ResourceType is required")
    if event["LogicalResourceId"] is None:
        raise ValueError("LogicalResourceId is required")
    return True


def connect_opensearch(endpoint: str) -> OpenSearch:
    service = "aoss" if "aoss" in endpoint else "es"
    logger.debug(f"Connecting to OpenSearch service: {service} at {endpoint}")
    return OpenSearch(
        hosts=[
            {
                "host": endpoint,
                "port": 443,
            }
        ],
        http_auth=AWSV4SignerAuth(
            boto3.Session().get_credentials(), os.getenv("AWS_REGION"), service
        ),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=10,
    )


def create_mapping(
    vector_field: str,
    dimensions: int,
    metadata_management: Sequence[MetadataManagementField],
) -> dict:
    mapping = {
        "properties": {
            vector_field: {
                "type": "knn_vector",
                "dimension": dimensions,
                "method": {
                    "engine": "faiss",
                    "space_type": "l2",
                    "name": "hnsw",
                    "parameters": {},
                },
            },
            "id": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
        },
    }
    for field in metadata_management:
        mapping["properties"][field["MappingField"]] = {
            "type": field["DataType"],
            "index": "true" if field["Filterable"] else "false",
        }
    return mapping


def create_setting(analyzer: AnalyzerProperties | None) -> dict:
    setting = {
        "index": {
            "number_of_shards": "2",
            "knn.algo_param": {"ef_search": "512"},
            "knn": "true",
        },
    }
    if analyzer:
        setting["analysis"] = {
            "analyzer": {
                "custom_analyzer": {
                    "type": "custom",
                    "tokenizer": analyzer["Tokenizer"],
                    "char_filter": analyzer["CharacterFilters"],
                    "filter": analyzer["TokenFilters"],
                }
            }
        }

    return setting


def create_index(
    client: OpenSearch, index_name: str, mapping: dict[str, str], setting: dict[str, str]
) -> None:
    logger.debug(f"creating index {index_name}")
    logger.debug(f"setting: {setting}")
    logger.debug(f"mapping: {mapping}")
    client.indices.create(
        index_name,
        body={
            "settings": setting,
            "mappings": mapping,
        },
        params={"wait_for_active_shards": "all"},
    )
    logger.debug(f"sleep for 30 seconds for bedrock KB  {index_name}")
    time.sleep(30)


# Add retry on AuthorizationException to mitigate policy creation race condition
@retry(
    retry=retry_if_exception_type(AuthorizationException),
    stop=stop_after_attempt(30),
    wait=wait_exponential_jitter(1, 3),
)
def handle_create(
    client: OpenSearch,
    index_name: str,
    vector_field: str,
    dimensions: int,
    metadata_management: Sequence[MetadataManagementField],
    analyzer: AnalyzerProperties | None,
):
    if client.indices.exists(index_name):
        raise ValueError(f"Index {index_name} already exists")

    try:
        mapping = create_mapping(vector_field, dimensions, metadata_management)
        setting = create_setting(analyzer)
        create_index(client, index_name, mapping, setting)
    except Exception as e:
        logger.error(f"Error creating index {index_name}")
        logger.exception(e)
        raise e
    return index_name


@retry(
    retry=retry_if_exception_type(AuthorizationException),
    stop=stop_after_attempt(30),
    wait=wait_exponential_jitter(1, 3),
)
def handle_delete(client: OpenSearch, index_name: str):
    try:
        client.indices.delete(index_name)
    except Exception as e:
        logger.error(f"Error deleting index {index_name}")
        logger.exception(e)
        raise e


def on_create(
    event: CustomResourceRequest[VectorIndexProperties],
) -> CustomResourceResponse:
    validate_event(event)
    client = connect_opensearch(event["ResourceProperties"]["Endpoint"])

    physical_id = handle_create(
        client,
        event["ResourceProperties"]["IndexName"],
        event["ResourceProperties"]["VectorField"],
        int(event["ResourceProperties"]["Dimensions"]),
        event["ResourceProperties"]["MetadataManagement"],
        event["ResourceProperties"].get("Analyzer", None),
    )
    return {"PhysicalResourceId": physical_id}


def on_update(
    _event: CustomResourceRequest[VectorIndexProperties],
) -> CustomResourceResponse:
    raise ValueError("Update not supported")


def on_delete(
    event: CustomResourceRequest[VectorIndexProperties],
) -> CustomResourceResponse:
    validate_event(event)
    client = connect_opensearch(event["ResourceProperties"]["Endpoint"])
    handle_delete(client, event["PhysicalResourceId"])
    return {"PhysicalResourceId": event["PhysicalResourceId"]}


def on_event(event: CustomResourceRequest[VectorIndexProperties], context):
    logger.debug(f"Received event: {event}")
    request_type = event["RequestType"]

    if "ServiceToken" in event["ResourceProperties"]:
        del event["ResourceProperties"]["ServiceToken"]

    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception("Invalid request type: %s" % request_type)
