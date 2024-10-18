# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
#
# Modifications Copyright OpenSearch Contributors. See
# GitHub history for details.
#
#  Licensed to Elasticsearch B.V. under one or more contributor
#  license agreements. See the NOTICE file distributed with
#  this work for additional information regarding copyright
#  ownership. Elasticsearch B.V. licenses this file to you under
#  the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
# 	http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.


import os
import time
from typing import Any
from unittest import SkipTest, TestCase

import opensearchpy.client
from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError

OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "https://localhost:9200")


def get_test_client(nowait: bool = False, **kwargs: Any) -> OpenSearch:
    # construct kwargs from the environment
    kw = {"timeout": 30}

    if "PYTHON_CONNECTION_CLASS" in os.environ:
        from opensearchpy import connection

        kw["connection_class"] = getattr(
            connection, os.environ["PYTHON_CONNECTION_CLASS"]
        )

    kw.update(kwargs)
    client = OpenSearch(OPENSEARCH_URL, **kw)  # type: ignore

    # wait for yellow status
    for _ in range(1 if nowait else 100):
        try:
            client.cluster.health(wait_for_status="yellow")
            return client
        except ConnectionError:
            time.sleep(0.1)
    else:
        # timeout
        raise SkipTest("OpenSearch failed to start.")


class OpenSearchTestCase(TestCase):
    client: Any

    @staticmethod
    def _get_client() -> OpenSearch:
        return get_test_client()

    @classmethod
    def setup_class(cls) -> None:
        cls.client = cls._get_client()

    def teardown_method(self, _: Any) -> None:
        # Hidden indices expanded in wildcards in OpenSearch 7.7
        expand_wildcards = ["open", "closed"]
        if self.opensearch_version() >= (1, 0):
            expand_wildcards.append("hidden")

        self.client.indices.delete(
            index="*", ignore=404, expand_wildcards=expand_wildcards
        )
        self.client.indices.delete_template(name="*", ignore=404)

    def opensearch_version(self) -> Any:
        if not hasattr(self, "_opensearch_version"):
            self._opensearch_version = opensearch_version(self.client)
        return self._opensearch_version


def _get_version(version_string: str) -> Any:
    if "." not in version_string:
        return ()
    version = version_string.strip().split(".")
    return tuple(int(v) if v.isdigit() else 999 for v in version)


def opensearch_version(client: opensearchpy.client.OpenSearch) -> Any:
    return _get_version(client.info()["version"]["number"])


if "OPENSEARCH_VERSION" in os.environ:
    OPENSEARCH_VERSION = _get_version(os.environ["OPENSEARCH_VERSION"])
else:
    OPENSEARCH_VERSION = opensearch_version(
        get_test_client(
            verify_certs=False,
            http_auth=("admin", os.getenv("OPENSEARCH_PASSWORD", "admin")),
        )
    )

__all__ = ["OpenSearchTestCase"]
