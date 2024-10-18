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


class QueryClient(NamespacedClient):
    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def datasource_delete(
        self,
        datasource_name: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Deletes specific datasource specified by name.


        :arg datasource_name: The Name of the DataSource to delete.
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
        if datasource_name in SKIP_IN_PATH:
            raise ValueError(
                "Empty value passed for a required argument 'datasource_name'."
            )

        return await self.transport.perform_request(
            "DELETE",
            _make_path("_plugins", "_query", "_datasources", datasource_name),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def datasource_retrieve(
        self,
        datasource_name: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves specific datasource specified by name.


        :arg datasource_name: The Name of the DataSource to retrieve.
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
        if datasource_name in SKIP_IN_PATH:
            raise ValueError(
                "Empty value passed for a required argument 'datasource_name'."
            )

        return await self.transport.perform_request(
            "GET",
            _make_path("_plugins", "_query", "_datasources", datasource_name),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def datasources_create(
        self,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Creates a new query datasource.


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
            "/_plugins/_query/_datasources",
            params=params,
            headers=headers,
            body=body,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def datasources_list(
        self,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves list of all datasources.


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
            "GET", "/_plugins/_query/_datasources", params=params, headers=headers
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    async def datasources_update(
        self,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Updates an existing query datasource.


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
            "PUT",
            "/_plugins/_query/_datasources",
            params=params,
            headers=headers,
            body=body,
        )
