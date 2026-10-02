"""Security configuration builders for the text-to-SQL sample."""


def require_aws_region(region):
    """Return a normalized AWS Region or fail before creating resources."""
    if not isinstance(region, str) or not region.strip():
        raise RuntimeError(
            "Configure an AWS Region before running this sample "
            "(for example, set AWS_DEFAULT_REGION)."
        )
    return region.strip()


def build_athena_workgroup_configuration(
    account_id, output_location, bytes_scanned_cutoff
):
    """Pin encrypted results and cost limits at the Athena service boundary."""
    return {
        "ResultConfiguration": {
            "OutputLocation": output_location,
            "EncryptionConfiguration": {"EncryptionOption": "SSE_S3"},
            "ExpectedBucketOwner": account_id,
        },
        "EnforceWorkGroupConfiguration": True,
        "PublishCloudWatchMetricsEnabled": True,
        "BytesScannedCutoffPerQuery": bytes_scanned_cutoff,
        "RequesterPaysEnabled": False,
    }


def build_glue_data_policy(bucket_name):
    """Allow the crawler to read only this sample's source-data prefix."""
    bucket_arn = f"arn:aws:s3:::{bucket_name}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InspectSampleBucket",
                "Effect": "Allow",
                "Action": "s3:GetBucketLocation",
                "Resource": bucket_arn,
            },
            {
                "Sid": "ListSampleData",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": bucket_arn,
                "Condition": {"StringLike": {"s3:prefix": ["data", "data/*"]}},
            },
            {
                "Sid": "ReadSampleData",
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": f"{bucket_arn}/data/*",
            },
        ],
    }


def build_lambda_query_policy(
    region, account_id, bucket_name, database_name, workgroup_name
):
    """Allow read-only query plumbing only for this sample's resources."""
    bucket_arn = f"arn:aws:s3:::{bucket_name}"
    workgroup_arn = f"arn:aws:athena:{region}:{account_id}:workgroup/{workgroup_name}"
    catalog_arn = f"arn:aws:glue:{region}:{account_id}:catalog"
    database_arn = f"arn:aws:glue:{region}:{account_id}:database/{database_name}"
    table_arn = f"arn:aws:glue:{region}:{account_id}:table/{database_name}/*"
    athena_catalog_arn = (
        f"arn:aws:athena:{region}:{account_id}:datacatalog/AwsDataCatalog"
    )

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "RunQueriesInDedicatedWorkgroup",
                "Effect": "Allow",
                "Action": [
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                    "athena:GetWorkGroup",
                    "athena:StartQueryExecution",
                    "athena:StopQueryExecution",
                ],
                "Resource": workgroup_arn,
            },
            {
                "Sid": "UseDefaultAthenaCatalog",
                "Effect": "Allow",
                "Action": "athena:GetDataCatalog",
                "Resource": athena_catalog_arn,
            },
            {
                "Sid": "ReadSampleCatalog",
                "Effect": "Allow",
                "Action": [
                    "glue:BatchGetPartition",
                    "glue:GetDatabase",
                    "glue:GetPartition",
                    "glue:GetPartitions",
                    "glue:GetTable",
                    "glue:GetTables",
                ],
                "Resource": [catalog_arn, database_arn, table_arn],
            },
            {
                "Sid": "InspectSampleStorage",
                "Effect": "Allow",
                "Action": [
                    "s3:GetBucketLocation",
                    "s3:ListBucketMultipartUploads",
                ],
                "Resource": bucket_arn,
            },
            {
                "Sid": "ListSampleStorage",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": bucket_arn,
                "Condition": {
                    "StringLike": {
                        "s3:prefix": [
                            "data",
                            "data/*",
                            "athena_result",
                            "athena_result/*",
                        ]
                    }
                },
            },
            {
                "Sid": "ReadSampleData",
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": f"{bucket_arn}/data/*",
            },
            {
                "Sid": "ManageQueryResults",
                "Effect": "Allow",
                "Action": [
                    "s3:AbortMultipartUpload",
                    "s3:GetObject",
                    "s3:ListMultipartUploadParts",
                    "s3:PutObject",
                ],
                "Resource": f"{bucket_arn}/athena_result/*",
            },
        ],
    }
