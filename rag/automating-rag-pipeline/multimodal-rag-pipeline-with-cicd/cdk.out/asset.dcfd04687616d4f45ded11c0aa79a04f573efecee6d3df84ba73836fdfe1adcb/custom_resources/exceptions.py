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
import os

import botocore.exceptions

import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class AWSRetryableError(Exception):
    Errors = (
        "ThrottlingException",
        "AccessDeniedException",
        "RequestLimitExceededException",
        "ProvisionedThroughputExceededException",
        "ResourceInUseException",
        "ServiceUnavailableException",
        "TooManyRequestsException",
        "InternalServerException",
        "ValidationException",  # "[security_exception] all shards failed" possible race condition
    )


def can_retry(e: botocore.exceptions.ClientError):
    if (
        e.response["Error"]["Code"] in AWSRetryableError.Errors
        or "index_not_found_exception" in e.response["Error"]["Message"]
    ):
        logger.info(
            f"Retrying after {e.response['Error']['Code']}: {e.response['Error']['Message']}"
        )
        raise AWSRetryableError(e)
    logger.exception(e)
    raise e
