import os

from aws_lambda_powertools import Logger

from client_utils import (
    get_caller_arn,
    get_oss_client,
    get_oss_http_client,
    get_session,
    get_sts_client,
)
from oss_utils import (
    MODEL_ID_TO_INDEX_REQUEST_MAP,
    create_index_with_retries,
    delete_index_if_present,
    get_access_policy,
    get_host_from_collection_endpoint,
    get_updated_access_policy_with_caller_arn,
    update_access_policy,
)

logger = Logger(service="amazon_bedrock_knowledge_base_infra_setup_lambda", level="INFO")

"""
Custom resources: https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.custom_resources-readme.html
Please read the above docs to understand how custom resources work. The idea here is to provide a Lambda to the custom resource Provider. This
lambda should know how to create, update and delete the resource in question.
In this case, the resource is an OSS index.
"""


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
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
1. We first update the data access policy (supplied as part of the resoure properties) to add the caller arn as a trusted principal.
2. We create an index with name `index_name`.
3. In case of any failure, the error gets thrown and the Custom Resource Provider treats it as a resource creation failure. We don't do any
cleanup since the index failed to be created - so there is nothing to delete.
4. We are using the index_name as the physical resource id because it serves as the identifier for an index.
"""


def on_create(event):
    props = event["ResourceProperties"]
    logger.info("Create new OpenSearch index with props %s" % props)
    region = os.environ["AWS_REGION"]
    policy_name = props["data_access_policy_name"]
    collection_endpoint = props["collection_endpoint"]
    host = get_host_from_collection_endpoint(collection_endpoint)
    index_name = props["index_name"]
    embedding_model_id = props["embedding_model_id"]
    index_request = MODEL_ID_TO_INDEX_REQUEST_MAP[embedding_model_id]

    session = get_session()
    sts_client = get_sts_client(session, region)
    oss_client = get_oss_client(session, region)
    oss_http_client = get_oss_http_client(session, region, host)

    update_access_policy_with_caller_arn_if_applicable(sts_client, oss_client, policy_name)

    logger.info("Creating index {}".format(index_name))
    create_index_with_retries(oss_http_client, index_name, index_request)

    return {"PhysicalResourceId": index_name}


"""
During an update event:
1. We first check if the old resouce properties and the new ones are the same. If they are, we do not do anything.
2. If the properties are different:
a. We first update the data access policy (supplied as part of the resoure properties) to add the caller arn as a trusted principal.
b. We delete the old index.
c. We create a new index with the new `index_name`.
3. In case of any failure, the error gets thrown and the Custom Resource Provider treats it as a resource update failure. The Customer Resource,
provider will send another update event in this case with the old and new resource props reversed and the same update logic, should be able to recreate
the old index again during rollback.
6. We are using the new index_name as the physical resource id because it serves as the identifier for the index. If the index naem has changed from before,
the Custom Resource provider will send a delete event for the old index but our deletion logic below is robust enough to not fail if we try deleting a non-existent index.
"""


def on_update(event):
    props = event["ResourceProperties"]
    old_props = event["OldResourceProperties"]
    logger.info("Updating OpenSearch index with new props %s, old props: %s" % (props, old_props))
    index_name = event["PhysicalResourceId"]

    if old_props == props:
        logger.info("Props are same, nothing to do")
        return {"PhysicalResourceId": index_name}

    logger.info("New props are different from old props. Index requires re-creation")
    region = os.environ["AWS_REGION"]
    policy_name = props["data_access_policy_name"]
    collection_endpoint = props["collection_endpoint"]
    host = get_host_from_collection_endpoint(collection_endpoint)
    index_name = props["index_name"]
    embedding_model_id = props["embedding_model_id"]
    index_request = MODEL_ID_TO_INDEX_REQUEST_MAP[embedding_model_id]

    session = get_session()
    sts_client = get_sts_client(session, region)
    oss_client = get_oss_client(session, region)
    oss_http_client = get_oss_http_client(session, region, host)

    update_access_policy_with_caller_arn_if_applicable(sts_client, oss_client, policy_name)

    old_index_name = old_props["index_name"]
    logger.info("Deleting old index {}".format(old_index_name))
    delete_index_if_present(oss_http_client, old_index_name)

    logger.info("Creating new index {}".format(index_name))
    create_index_with_retries(oss_http_client, index_name, index_request)
    return {"PhysicalResourceId": index_name}


"""
During a delete event:
1. We try deleting the index if it exists.
2. If it doesn't exist, we return without error. If it exists, we delete it.
3. In case of any errors (when the index exists), we throw the error and CFN treats it as a Deletion failure.
"""


def on_delete(event):
    index_name = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    logger.info("Deleting OpenSearch index {} with props {}".format(index_name, props))
    region = os.environ["AWS_REGION"]
    collection_endpoint = props["collection_endpoint"]
    host = get_host_from_collection_endpoint(collection_endpoint)

    session = get_session()
    oss_http_client = get_oss_http_client(session, region, host)

    delete_index_if_present(oss_http_client, index_name)
    return {"PhysicalResourceId": index_name}


def update_access_policy_with_caller_arn_if_applicable(sts_client, oss_client, policy_name):
    caller_arn = get_caller_arn(sts_client)

    access_policy = get_access_policy(oss_client, policy_name)
    updated_access_policy = {
        **access_policy,
        "Policy": get_updated_access_policy_with_caller_arn(access_policy["Policy"], caller_arn),
    }
    logger.info("Updating access policy")
    update_access_policy(
        oss_client,
        updated_access_policy["Policy"],
        updated_access_policy["Version"],
        updated_access_policy["PolicyName"],
    )
