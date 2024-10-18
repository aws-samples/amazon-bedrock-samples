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

__version__ = "0.1.0"

import logging
import os
import time

from .cr_types import CustomResourceRequest, CustomResourceResponse
from .opensearch_index import on_event as on_event_opensearch_index

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


def on_event(event: CustomResourceRequest, context):
    logger.debug(f"Received event: {event}")
    resource_type = event["ResourceType"]

    if resource_type == "Custom::OpenSearchIndex":
        return on_event_opensearch_index(event, context)
    if resource_type == "Custom::NoOp":
        logger.info("NoOp resource type")
        # Return a response with a physical resource ID that is not empty.
        # This is required by CloudFormation to avoid a race condition.
        time.sleep(event["ResourceProperties"].get("delay", 0))
        return CustomResourceResponse(
            PhysicalResourceId=event["ResourceProperties"].get("message", "no-op")
        )
    raise Exception("Invalid resource type: %s" % resource_type)
