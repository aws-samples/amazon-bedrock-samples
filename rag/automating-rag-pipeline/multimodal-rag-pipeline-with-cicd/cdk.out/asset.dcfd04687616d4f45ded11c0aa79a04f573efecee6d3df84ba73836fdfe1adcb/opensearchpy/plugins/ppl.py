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

from ..client.utils import SKIP_IN_PATH, NamespacedClient, query_params


class PplClient(NamespacedClient):
    @query_params(
        "error_trace", "filter_path", "format", "human", "pretty", "sanitize", "source"
    )
    def explain(
        self,
        body: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Shows how a query is executed against OpenSearch.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg format: A short version of the Accept header, e.g. json,
            yaml.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg sanitize: Specifies whether to escape special characters in
            the results. Default is True.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        if body in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'body'.")

        return self.transport.perform_request(
            "POST", "/_plugins/_ppl/_explain", params=params, headers=headers, body=body
        )

    @query_params(
        "error_trace", "filter_path", "format", "human", "pretty", "sanitize", "source"
    )
    def get_stats(
        self,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Collect metrics for the plugin within the interval.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg format: A short version of the Accept header, e.g. json,
            yaml.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg sanitize: Specifies whether to escape special characters in
            the results. Default is True.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        return self.transport.perform_request(
            "GET", "/_plugins/_ppl/stats", params=params, headers=headers
        )

    @query_params(
        "error_trace", "filter_path", "format", "human", "pretty", "sanitize", "source"
    )
    def post_stats(
        self,
        body: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        By a stats endpoint, you are able to collect metrics for the plugin within the
        interval.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg format: A short version of the Accept header, e.g. json,
            yaml.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg sanitize: Specifies whether to escape special characters in
            the results. Default is True.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        if body in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'body'.")

        return self.transport.perform_request(
            "POST", "/_plugins/_ppl/stats", params=params, headers=headers, body=body
        )

    @query_params(
        "error_trace", "filter_path", "format", "human", "pretty", "sanitize", "source"
    )
    def query(
        self,
        body: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Send a PPL query to the PPL plugin.


        :arg error_trace: Whether to include the stack trace of returned
            errors.
        :arg filter_path: Comma-separated list of filters used to reduce
            the response.
        :arg format: A short version of the Accept header, e.g. json,
            yaml.
        :arg human: Whether to return human readable values for
            statistics.
        :arg pretty: Whether to pretty format the returned JSON
            response.
        :arg sanitize: Specifies whether to escape special characters in
            the results. Default is True.
        :arg source: The URL-encoded request definition. Useful for
            libraries that do not accept a request body for non-POST requests.
        """
        if body in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'body'.")

        return self.transport.perform_request(
            "POST", "/_plugins/_ppl", params=params, headers=headers, body=body
        )
