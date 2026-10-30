import json
import logging
import os
import time

import boto3

from query_guard import QueryValidationError, validate_read_only_query

LOGGER = logging.getLogger(__name__)
DEFAULT_DATABASE_NAME = "thehistoryofbaseball"
DEFAULT_QUERY_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RESULT_ROWS = 100


class RequestValidationError(ValueError):
    """Raised when the Bedrock action-group event is malformed."""


class QueryExecutionError(RuntimeError):
    """Raised when Athena cannot safely complete a query."""


def get_glue_client():
    """Create the Glue API client used by this Lambda invocation."""
    return boto3.client("glue")


def get_athena_client():
    """Create the Athena API client used by this Lambda invocation."""
    return boto3.client("athena")


def _required_text_setting(name, default=None):
    raw_value = os.environ.get(name, default)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise RuntimeError(f"{name} must be configured with a non-empty value.")
    return raw_value.strip()


def get_schema(glue_client=None):
    """Return table and column metadata from only the configured database."""
    database_name = _required_text_setting(
        "DATABASE_NAME", DEFAULT_DATABASE_NAME
    )
    client = glue_client or get_glue_client()
    table_schemas = []

    paginator = client.get_paginator("get_tables")
    for page in paginator.paginate(DatabaseName=database_name):
        for table in page.get("TableList", []):
            columns = table.get("StorageDescriptor", {}).get("Columns", [])
            schema = {column["Name"]: column["Type"] for column in columns}
            table_schemas.append({"Table": table["Name"], "Schema": schema})

    return table_schemas


def _bounded_integer_setting(name, default, maximum):
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"{name} must be an integer.") from error

    if value < 1 or value > maximum:
        raise RuntimeError(f"{name} must be between 1 and {maximum}.")
    return value


def _query_timeout_seconds():
    return _bounded_integer_setting(
        "QUERY_TIMEOUT_SECONDS",
        DEFAULT_QUERY_TIMEOUT_SECONDS,
        DEFAULT_QUERY_TIMEOUT_SECONDS,
    )


def _max_result_rows():
    return _bounded_integer_setting(
        "MAX_RESULT_ROWS",
        DEFAULT_MAX_RESULT_ROWS,
        DEFAULT_MAX_RESULT_ROWS,
    )


def _load_query_settings():
    """Validate all settings before an Athena client or query is created."""
    return {
        "database_name": _required_text_setting(
            "DATABASE_NAME", DEFAULT_DATABASE_NAME
        ),
        "workgroup_name": _required_text_setting("ATHENA_WORKGROUP"),
        "timeout_seconds": _query_timeout_seconds(),
        "max_result_rows": _max_result_rows(),
    }


def _wait_for_query(athena_client, query_execution_id, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds

    while True:
        response = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )
        status = response["QueryExecution"]["Status"]
        state = status["State"]

        if state == "SUCCEEDED":
            return
        if state in {"FAILED", "CANCELLED"}:
            LOGGER.warning(
                "Athena query %s ended in state %s: %s",
                query_execution_id,
                state,
                status.get("StateChangeReason", "No reason returned"),
            )
            raise QueryExecutionError(f"Athena query ended in state {state}.")
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            try:
                athena_client.stop_query_execution(
                    QueryExecutionId=query_execution_id
                )
            except Exception:
                LOGGER.exception(
                    "Could not cancel timed-out Athena query %s",
                    query_execution_id,
                )
            raise QueryExecutionError("Athena query exceeded the execution timeout.")

        time.sleep(min(0.5, remaining_seconds))


def extract_result_data(query_results, max_result_rows):
    """Convert one Athena result page into a bounded, explicit result envelope."""
    result_set = query_results["ResultSet"]
    column_info = result_set["ResultSetMetadata"]["ColumnInfo"]
    column_names = [column["Name"] for column in column_info]
    result_data = []

    for index, row in enumerate(result_set.get("Rows", [])):
        values = [item.get("VarCharValue") for item in row.get("Data", [])]
        if index == 0 and values == column_names:
            continue
        values.extend([None] * (len(column_names) - len(values)))
        result_data.append(dict(zip(column_names, values)))

    return {
        "rows": result_data[:max_result_rows],
        "truncated": (
            bool(query_results.get("NextToken"))
            or len(result_data) > max_result_rows
        ),
    }


def execute_athena_query(query, athena_client=None):
    """Validate and execute one read-only query in the dedicated workgroup."""
    validated_query = validate_read_only_query(query)
    settings = _load_query_settings()
    client = athena_client or get_athena_client()

    response = client.start_query_execution(
        QueryString=validated_query,
        QueryExecutionContext={
            "Catalog": "AwsDataCatalog",
            "Database": settings["database_name"],
        },
        WorkGroup=settings["workgroup_name"],
    )
    query_execution_id = response["QueryExecutionId"]
    LOGGER.info("Started Athena query %s", query_execution_id)

    _wait_for_query(
        client,
        query_execution_id,
        settings["timeout_seconds"],
    )
    query_results = client.get_query_results(
        QueryExecutionId=query_execution_id,
        MaxResults=settings["max_result_rows"] + 1,
    )
    return extract_result_data(
        query_results,
        settings["max_result_rows"],
    )


def _extract_query(event):
    try:
        properties = event["requestBody"]["content"]["application/json"][
            "properties"
        ]
    except (KeyError, TypeError) as error:
        raise RequestValidationError("The request body is malformed.") from error

    if not isinstance(properties, list) or len(properties) != 1:
        raise RequestValidationError(
            "The request must contain exactly one query property."
        )

    query_property = properties[0]
    if (
        not isinstance(query_property, dict)
        or query_property.get("name") != "query"
        or "value" not in query_property
    ):
        raise RequestValidationError("The query property is missing or invalid.")

    return query_property["value"]


def _build_response(event, status_code, body):
    event = event if isinstance(event, dict) else {}
    response_body = {"application/json": {"body": json.dumps(body)}}
    action_response = {
        "actionGroup": event.get("actionGroup", ""),
        "apiPath": event.get("apiPath", ""),
        "httpMethod": event.get("httpMethod", ""),
        "httpStatusCode": status_code,
        "responseBody": response_body,
    }
    return {
        "messageVersion": "1.0",
        "response": action_response,
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }


def lambda_handler(event, context):
    """Handle the two operations exposed by the Bedrock action group."""
    del context

    if not isinstance(event, dict):
        return _build_response(event, 400, {"error": "The request is malformed."})

    try:
        if event.get("apiPath") == "/getschema":
            result = get_schema()
        elif event.get("apiPath") == "/querydatabase":
            result = execute_athena_query(_extract_query(event))
        else:
            return _build_response(event, 404, {"error": "Unknown API path."})
    except (QueryValidationError, RequestValidationError) as error:
        LOGGER.info("Rejected invalid action-group request: %s", error)
        return _build_response(event, 400, {"error": str(error)})
    except Exception:
        LOGGER.exception("The action-group request failed")
        return _build_response(
            event, 500, {"error": "The database query could not be completed."}
        )

    return _build_response(event, 200, result)
