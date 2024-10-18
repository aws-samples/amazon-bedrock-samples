# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
#
# Modifications Copyright OpenSearch Contributors. See
# GitHub history for details.

# ------------------------------------------------------------------------------------------
# THIS CODE IS AUTOMATICALLY GENERATED AND MANUAL EDITS WILL BE LOST
#
# To contribute, kindly make modifications in the opensearch-py client generator
# or in the OpenSearch API specification, and run `nox -rs generate`. See DEVELOPER_GUIDE.md
# and https://github.com/opensearch-project/opensearch-api-specification for details.
# -----------------------------------------------------------------------------------------+


from typing import Any

from ..client.utils import SKIP_IN_PATH, NamespacedClient, _make_path, query_params


class ObservabilityClient(NamespacedClient):
    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def create_object(
        self,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Creates a new observability object.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        return await self.transport.perform_request(
            "POST",
            "/_plugins/_observability/object",
            params=params,
            headers=headers,
            body=body,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def delete_object(
        self,
        object_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Deletes specific observability object specified by ID.


        :arg object_id: The ID of the Observability Object.
        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        if object_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'object_id'.")

        return await self.transport.perform_request(
            "DELETE",
            _make_path("_plugins", "_observability", "object", object_id),
            params=params,
            headers=headers,
        )

    @query_params(
        "error_trace",
        "filter_path",
        "human",
        "objectId",
        "objectIdList",
        "pretty",
        "source",
    )
    async def delete_objects(
        self,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Deletes specific observability objects specified by ID or a list of IDs.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg objectId: The ID of a single Observability Object to
            delete.
        :arg objectIdList: A comma-separated list of Observability
            Object IDs to delete.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        return await self.transport.perform_request(
            "DELETE", "/_plugins/_observability/object", params=params, headers=headers
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def get_localstats(
        self,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves Local Stats of all observability objects.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        return await self.transport.perform_request(
            "GET",
            "/_plugins/_observability/_local/stats",
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def get_object(
        self,
        object_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves specific observability object specified by ID.


        :arg object_id: The ID of the Observability Object.
        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        if object_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'object_id'.")

        return await self.transport.perform_request(
            "GET",
            _make_path("_plugins", "_observability", "object", object_id),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def list_objects(
        self,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves list of all observability objects.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        return await self.transport.perform_request(
            "GET", "/_plugins/_observability/object", params=params, headers=headers
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def update_object(
        self,
        object_id: Any,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Updates an existing observability object.


        :arg object_id: The ID of the Observability Object.
        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        if object_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'object_id'.")

        return await self.transport.perform_request(
            "PUT",
            _make_path("_plugins", "_observability", "object", object_id),
            params=params,
            headers=headers,
            body=body,
        )
