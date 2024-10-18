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


class MlClient(NamespacedClient):
    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def delete_model(
        self,
        model_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Deletes a model.


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
        if model_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'model_id'.")

        return self.transport.perform_request(
            "DELETE",
            _make_path("_plugins", "_ml", "models", model_id),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def delete_model_group(
        self,
        model_group_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Deletes a model group.


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
        if model_group_id in SKIP_IN_PATH:
            raise ValueError(
                "Empty value passed for a required argument 'model_group_id'."
            )

        return self.transport.perform_request(
            "DELETE",
            _make_path("_plugins", "_ml", "model_groups", model_group_id),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def get_model_group(
        self,
        model_group_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves a model group.


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
        if model_group_id in SKIP_IN_PATH:
            raise ValueError(
                "Empty value passed for a required argument 'model_group_id'."
            )

        return self.transport.perform_request(
            "GET",
            _make_path("_plugins", "_ml", "model_groups", model_group_id),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def get_task(
        self,
        task_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Retrieves a task.


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
        if task_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'task_id'.")

        return self.transport.perform_request(
            "GET",
            _make_path("_plugins", "_ml", "tasks", task_id),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def register_model(
        self,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Registers a model.


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
        return self.transport.perform_request(
            "POST",
            "/_plugins/_ml/models/_register",
            params=params,
            headers=headers,
            body=body,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def register_model_group(
        self,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Registers a model group.


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
        return self.transport.perform_request(
            "POST",
            "/_plugins/_ml/model_groups/_register",
            params=params,
            headers=headers,
            body=body,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def search_models(
        self,
        body: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Searches for models.


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
        return self.transport.perform_request(
            "GET",
            "/_plugins/_ml/models/_search",
            params=params,
            headers=headers,
            body=body,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def deploy_model(
        self,
        model_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Deploys a model.


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
        if model_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'model_id'.")

        return self.transport.perform_request(
            "POST",
            _make_path("_plugins", "_ml", "models", model_id, "_deploy"),
            params=params,
            headers=headers,
        )

    @query_params("error_trace", "filter_path", "human", "pretty", "source")
    def undeploy_model(
        self,
        model_id: Any,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        """
        Undeploys a model.


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
        if model_id in SKIP_IN_PATH:
            raise ValueError("Empty value passed for a required argument 'model_id'.")

        return self.transport.perform_request(
            "POST",
            _make_path("_plugins", "_ml", "models", model_id, "_undeploy"),
            params=params,
            headers=headers,
        )
