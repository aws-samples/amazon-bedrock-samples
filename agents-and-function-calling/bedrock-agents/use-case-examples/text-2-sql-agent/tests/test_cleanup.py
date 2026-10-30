import pathlib
import sys
import unittest

DEPENDENCIES_ROOT = pathlib.Path(__file__).resolve().parents[1] / "dependencies"
sys.path.insert(0, str(DEPENDENCIES_ROOT))

from clean import CleanupReport, delete_iam_role, empty_and_delete_bucket


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return iter(self.pages)


class FakeIamClient:
    def __init__(self):
        self.calls = []
        self.pages = {
            "list_attached_role_policies": [
                {"AttachedPolicies": [{"PolicyArn": "arn:managed:one"}]},
                {"AttachedPolicies": [{"PolicyArn": "arn:managed:two"}]},
            ],
            "list_role_policies": [
                {"PolicyNames": ["inline-one"]},
                {"PolicyNames": ["inline-two"]},
            ],
            "list_instance_profiles_for_role": [
                {
                    "InstanceProfiles": [
                        {"InstanceProfileName": "sample-profile"}
                    ]
                }
            ],
        }

    def get_role(self, **kwargs):
        return {
            "Role": {
                "PermissionsBoundary": {
                    "PermissionsBoundaryArn": "arn:boundary"
                }
            }
        }

    def get_paginator(self, operation_name):
        return FakePaginator(self.pages[operation_name])

    def remove_role_from_instance_profile(self, **kwargs):
        self.calls.append(("remove_profile", kwargs))

    def detach_role_policy(self, **kwargs):
        self.calls.append(("detach", kwargs))

    def delete_role_policy(self, **kwargs):
        self.calls.append(("delete_inline", kwargs))

    def delete_role_permissions_boundary(self, **kwargs):
        self.calls.append(("delete_boundary", kwargs))

    def delete_role(self, **kwargs):
        self.calls.append(("delete_role", kwargs))


class FakeS3Client:
    def __init__(self):
        self.delete_requests = []
        self.deleted_bucket = None
        self.pages = {
            "list_object_versions": [
                {
                    "Versions": [
                        {"Key": "data.csv", "VersionId": "version-1"}
                    ],
                    "DeleteMarkers": [
                        {"Key": "old.csv", "VersionId": "marker-1"}
                    ],
                }
            ],
            "list_objects_v2": [
                {"Contents": [{"Key": "current.csv"}]}
            ],
        }

    def get_paginator(self, operation_name):
        return FakePaginator(self.pages[operation_name])

    def delete_objects(self, **kwargs):
        self.delete_requests.append(kwargs["Delete"]["Objects"])
        return {}

    def delete_bucket(self, **kwargs):
        self.deleted_bucket = kwargs["Bucket"]


class FakeAwsError(Exception):
    def __init__(self, code, message="error"):
        super().__init__(message)
        self.response = {"Error": {"Code": code, "Message": message}}


class CleanupTests(unittest.TestCase):
    def test_role_cleanup_enumerates_every_dependency_before_deletion(self):
        client = FakeIamClient()

        delete_iam_role(client, "sample-role")

        self.assertIn(
            (
                "remove_profile",
                {
                    "InstanceProfileName": "sample-profile",
                    "RoleName": "sample-role",
                },
            ),
            client.calls,
        )
        detached_arns = {
            kwargs["PolicyArn"]
            for operation, kwargs in client.calls
            if operation == "detach"
        }
        self.assertEqual(detached_arns, {"arn:managed:one", "arn:managed:two"})
        inline_names = {
            kwargs["PolicyName"]
            for operation, kwargs in client.calls
            if operation == "delete_inline"
        }
        self.assertEqual(inline_names, {"inline-one", "inline-two"})
        self.assertIn(
            ("delete_boundary", {"RoleName": "sample-role"}),
            client.calls,
        )
        self.assertEqual(
            client.calls[-1],
            ("delete_role", {"RoleName": "sample-role"}),
        )

    def test_bucket_cleanup_removes_versions_markers_and_current_objects(self):
        client = FakeS3Client()

        empty_and_delete_bucket(client, "sample-bucket")

        self.assertEqual(
            client.delete_requests,
            [
                [
                    {"Key": "data.csv", "VersionId": "version-1"},
                    {"Key": "old.csv", "VersionId": "marker-1"},
                ],
                [{"Key": "current.csv"}],
            ],
        )
        self.assertEqual(client.deleted_bucket, "sample-bucket")

    def test_cleanup_report_ignores_only_expected_missing_resources(self):
        report = CleanupReport()

        report.attempt(
            "missing role",
            lambda: (_ for _ in ()).throw(FakeAwsError("NoSuchEntity")),
            {"NoSuchEntity"},
        )
        report.attempt(
            "denied role",
            lambda: (_ for _ in ()).throw(FakeAwsError("AccessDenied")),
            {"NoSuchEntity"},
        )

        self.assertEqual(len(report.failures), 1)
        with self.assertRaisesRegex(RuntimeError, "denied role"):
            report.raise_if_failed()


if __name__ == "__main__":
    unittest.main()
