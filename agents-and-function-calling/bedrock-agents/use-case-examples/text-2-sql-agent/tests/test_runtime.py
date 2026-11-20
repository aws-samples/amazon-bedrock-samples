import os
import pathlib
import sys
import types
import unittest
from unittest import mock

SAMPLE_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SAMPLE_ROOT))

try:
    import boto3  # noqa: F401
except ModuleNotFoundError:
    sys.modules["boto3"] = types.SimpleNamespace(
        client=lambda service_name: (_ for _ in ()).throw(
            AssertionError(f"unexpected {service_name} client creation")
        )
    )

from lambda_function import (
    QueryExecutionError,
    _wait_for_query,
    execute_athena_query,
    extract_result_data,
    get_schema,
)


class TrackingAthenaClient:
    def __init__(self):
        self.started = False

    def start_query_execution(self, **kwargs):
        self.started = True
        return {"QueryExecutionId": "query-id"}


class RuntimeConfigurationTests(unittest.TestCase):
    def test_invalid_settings_never_start_an_athena_query(self):
        invalid_environments = [
            {
                "ATHENA_WORKGROUP": "",
                "DATABASE_NAME": "database",
                "QUERY_TIMEOUT_SECONDS": "120",
                "MAX_RESULT_ROWS": "100",
            },
            {
                "ATHENA_WORKGROUP": "workgroup",
                "DATABASE_NAME": " ",
                "QUERY_TIMEOUT_SECONDS": "120",
                "MAX_RESULT_ROWS": "100",
            },
            {
                "ATHENA_WORKGROUP": "workgroup",
                "DATABASE_NAME": "database",
                "QUERY_TIMEOUT_SECONDS": "not-an-integer",
                "MAX_RESULT_ROWS": "100",
            },
            {
                "ATHENA_WORKGROUP": "workgroup",
                "DATABASE_NAME": "database",
                "QUERY_TIMEOUT_SECONDS": "120",
                "MAX_RESULT_ROWS": "101",
            },
        ]

        for environment in invalid_environments:
            client = TrackingAthenaClient()
            with self.subTest(environment=environment), mock.patch.dict(
                os.environ,
                environment,
                clear=True,
            ), self.assertRaises(RuntimeError):
                execute_athena_query("SELECT 1", athena_client=client)
            self.assertFalse(client.started)

    def test_invalid_settings_prevent_athena_client_creation(self):
        environment = {
            "ATHENA_WORKGROUP": "workgroup",
            "DATABASE_NAME": "database",
            "QUERY_TIMEOUT_SECONDS": "0",
            "MAX_RESULT_ROWS": "100",
        }
        with mock.patch.dict(
            os.environ,
            environment,
            clear=True,
        ), mock.patch(
            "lambda_function.get_athena_client"
        ) as get_athena_client, self.assertRaises(RuntimeError):
            execute_athena_query("SELECT 1")

        get_athena_client.assert_not_called()

    def test_empty_database_prevents_glue_client_use(self):
        glue_client = mock.Mock()
        with mock.patch.dict(
            os.environ,
            {"DATABASE_NAME": ""},
            clear=True,
        ), self.assertRaises(RuntimeError):
            get_schema(glue_client=glue_client)

        glue_client.get_paginator.assert_not_called()


class ResultAndTimeoutTests(unittest.TestCase):
    def test_result_envelope_is_bounded_and_reports_truncation(self):
        results = {
            "NextToken": "more-results",
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [{"Name": "name"}, {"Name": "year"}]
                },
                "Rows": [
                    {
                        "Data": [
                            {"VarCharValue": "name"},
                            {"VarCharValue": "year"},
                        ]
                    },
                    {
                        "Data": [
                            {"VarCharValue": "Ada"},
                            {"VarCharValue": "2001"},
                        ]
                    },
                    {"Data": [{"VarCharValue": "Grace"}]},
                ],
            },
        }

        self.assertEqual(
            extract_result_data(results, max_result_rows=1),
            {
                "rows": [{"name": "Ada", "year": "2001"}],
                "truncated": True,
            },
        )

    def test_cancellation_failure_does_not_mask_timeout(self):
        class TimedOutClient:
            def __init__(self):
                self.stop_called = False

            def get_query_execution(self, **kwargs):
                return {"QueryExecution": {"Status": {"State": "RUNNING"}}}

            def stop_query_execution(self, **kwargs):
                self.stop_called = True
                raise RuntimeError("cancel failed")

        client = TimedOutClient()
        with mock.patch(
            "lambda_function.time.monotonic",
            side_effect=[100.0, 102.0],
        ), self.assertLogs("lambda_function", level="ERROR"), self.assertRaisesRegex(
            QueryExecutionError,
            "exceeded the execution timeout",
        ):
            _wait_for_query(client, "query-id", timeout_seconds=1)

        self.assertTrue(client.stop_called)


if __name__ == "__main__":
    unittest.main()
