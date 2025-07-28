import hashlib
import json
import time
from pathlib import Path

from aws_cdk import CfnOutput, CfnParameter, Fn, RemovalPolicy, Stack
from aws_cdk import aws_glue as glue
from aws_cdk import aws_iam as iam
from aws_cdk import aws_quicksight as quicksight
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from cdk_nag import NagSuppressions
from constructs import Construct


class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:  # noqa: PLR0915
        super().__init__(scope, construct_id, **kwargs)

        # Get current account number using Fn.ref
        account_id = Fn.ref("AWS::AccountId")

        # Create a parameter for Bedrock Logs S3 bucket
        bedrock_logs_bucket = CfnParameter(
            self, "BedrockLogsS3Bucket",
            type="String",
            description="Name of the S3 bucket where Bedrock logs will be stored.",
        )

        # Create a parameter for QuickSight username
        quicksight_username = CfnParameter(
            self, "QuickSightUserName",
            type="String",
            description="Name of the QuickSight user for setting up the dataset and dashboards.",
        )

        # Create a parameter for QuickSight region
        quicksight_region = CfnParameter(
            self, "QuickSightRegion",
            type="String",
            description="Name of the Region where quicksight and IDC are enabled.",
        )

        # Create destination bucket with account number in name
        transformed_logs_bucket = s3.Bucket(
            self, "BedrockLogsTransformed",
            bucket_name=f"bedrock-logs-transformed-{self.region}-{account_id}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # Add bucket policy to allow QuickSight service to access the transformed bucket
        transformed_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("quicksight.amazonaws.com")],
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    transformed_logs_bucket.bucket_arn,
                    f"{transformed_logs_bucket.bucket_arn}/*",
                ],
            ),
        )

        # Create a policy for the QuickSight service role
        quicksight_policy = iam.ManagedPolicy(
            self, "QuickSightServiceRolePolicy",
            managed_policy_name="QuickSightS3AccessPolicy",
            description="Policy to allow QuickSight service role to access S3 bucket",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        transformed_logs_bucket.bucket_arn,
                        f"{transformed_logs_bucket.bucket_arn}/*",
                    ],
                ),
            ],
            roles=[
                iam.Role.from_role_name(
                    self, "QuickSightServiceRole",
                    role_name="aws-quicksight-service-role-v0",
                ),
            ],
        )
        
        # Add specific suppression for the QuickSightServiceRolePolicy resource
        NagSuppressions.add_resource_suppressions(
            quicksight_policy,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard permissions are required for S3 bucket access patterns in QuickSight integration",
                    "appliesTo": ["Resource::<BedrockLogsTransformed01DD90B4.Arn>/*"]
                }
            ]
        )

        # Create IAM role for Glue
        glue_role = iam.Role(
            self, "BedrockLogs_GlueETLRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
        )

        # Add managed policy for Glue service role
        glue_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
        )

        # Create custom policy for S3 read access
        s3_read_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
            ],
            resources=[
                f"arn:aws:s3:::{bedrock_logs_bucket.value_as_string}",
                f"arn:aws:s3:::{bedrock_logs_bucket.value_as_string}/*",
            ],
        )

        # Create custom policy for S3 write access to destination bucket
        s3_write_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
            ],
            resources=[
                transformed_logs_bucket.bucket_arn,
                f"{transformed_logs_bucket.bucket_arn}/*",
                "arn:aws:s3:::cdk*",
                "arn:aws:s3:::cdk*/*",
            ],
        )


        # Attach the custom S3 policy to the role
        glue_role.add_to_policy(s3_read_policy)
        glue_role.add_to_policy(s3_write_policy)

        # Add managed policy for Glue service role
        glue_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
        )

        # Add Lake Formation Data Admin managed policy
        glue_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSLakeFormationDataAdmin"),
        )

        # Create the ETL script asset
        etl_script = s3_assets.Asset(
            self,
            "ETLGlueScript",
            path="./glue/bedrock_logs_transform.py",  # Path to your local script file
        )

        # Create Glue ETL Job
        glue_etl_job = glue.CfnJob(
            self,
            "BedrockFlattenLogsETL",
            name="bedrock-flatten-logs",
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=etl_script.s3_object_url,
            ),
            description="Job to transform and flatten Bedrock logs",
            role=glue_role.role_arn,
            glue_version="5.0",
            worker_type="G.8X",
            number_of_workers=10,
            timeout=120,
            max_retries=0,
            execution_class="STANDARD",
            default_arguments={
                "--source_bucket": bedrock_logs_bucket.value_as_string,
                "--target_bucket": transformed_logs_bucket.bucket_name,
                "--job-bookmark-option": "job-bookmark-enable",
            },
        )

        # Create a scheduled trigger for the Glue job
        glue.CfnTrigger(
            self,
            "BedrockLogsETLTrigger",
            name="bedrock-logs-etl-trigger",
            type="SCHEDULED",
            schedule="cron(0 */3 * * ? *)",
            actions=[
                glue.CfnTrigger.ActionProperty(
                    job_name=glue_etl_job.name,
                ),
            ],
        )

        # Create Glue Database
        glue_database = glue.CfnDatabase(
            self,
            "BedrockLogsDatabase",
            catalog_id=account_id,  # Using the account_id we already have
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"bedrock-{self.region}",
                description="Database for Bedrock usage logs and analytics",
                location_uri=f"s3://{transformed_logs_bucket.bucket_name}/",
            ),
        )

        schema_path = "./glue/bedrock_logs_schema.json"
        with Path.open(schema_path) as f:
            schema_content = f.read()
            schema = json.loads(schema_content)
            content_hash = hashlib.md5(schema_content.encode()).hexdigest()  #nosec noqa: S324 Hash is being used only for comparing file changes during cdk runs

        # Create Glue Table for Bedrock logs
        bedrock_logs_table = glue.CfnTable(
            self,
            "BedrockLogsTable",
            catalog_id=account_id,
            database_name=glue_database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name="bedrock_usage_logs",
                description="Bedrock usage logs",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "parquet",
                    "compressionType": "snappy",
                    "schema_hash": content_hash,
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(
                            name=col["name"],
                            type=col["type"],
                        ) for col in schema["columns"]
                    ],
                    location=f"s3://{transformed_logs_bucket.bucket_name}/main/",
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                    ),
                ),
                partition_keys=[
                    glue.CfnTable.ColumnProperty(
                        name=key["name"],
                        type=key["type"],
                    ) for key in schema["partition_keys"]
                ],
            ),
        )
        bedrock_logs_table.add_dependency(glue_database)

        # Load schema from Bedrock Logs Metadata JSON file
        metadata_path = "./glue/bedrock_metadata_schema.json"
        with Path.open(metadata_path) as f:
            metadata_content = f.read()
            metadata = json.loads(metadata_content)


        # Create Glue Table for Bedrock Logs Metadata
        bedrock_metadata_table = glue.CfnTable(
            self,
            "BedrockMetadataTable",
            catalog_id=account_id,
            database_name=glue_database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name="bedrock_usage_metadata",
                description="Bedrock usage metadata logs",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "parquet",
                    "compressionType": "snappy",
                    "schema_hash": content_hash,
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(
                            name=col["name"],
                            type=col["type"],
                        ) for col in metadata["columns"]
                    ],
                    location=f"s3://{transformed_logs_bucket.bucket_name}/metadata/",
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                    ),
                ),
                partition_keys=[
                    glue.CfnTable.ColumnProperty(
                        name=key["name"],
                        type=key["type"],
                    ) for key in metadata["partition_keys"]
                ],
            ),
        )
        bedrock_metadata_table.add_dependency(glue_database)

        # Create IAM role for the crawler
        crawler_role = iam.Role(
            self,
            "BedrockLogsCrawlerRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
            ],
        )

        # Add S3 read permissions to the crawler role
        crawler_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                resources=[
                    transformed_logs_bucket.bucket_arn,
                    f"{transformed_logs_bucket.bucket_arn}/*",
                ],
            ),
        )

        # Create the Glue Crawler for Bedrock logs
        bedrock_logs_crawler = glue.CfnCrawler(
            self,
            "BedrockLogsCrawler",
            name="bedrock-logs-crawler",
            role=crawler_role.role_arn,
            database_name=glue_database.ref,
            targets=glue.CfnCrawler.TargetsProperty(
                catalog_targets=[
                    glue.CfnCrawler.CatalogTargetProperty(
                        database_name=glue_database.ref,
                        tables=[bedrock_logs_table.ref],
                    ),
                ],
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                delete_behavior="LOG",
                update_behavior="LOG",
            ),
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                recrawl_behavior="CRAWL_EVERYTHING",
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression="cron(0 */3 * * ? *)",
            ),
        )
        bedrock_logs_crawler.add_dependency(bedrock_logs_table)

        # Create the Glue Crawler for Bedrock logs
        bedrock_metadata_crawler = glue.CfnCrawler(
            self,
            "BedrockMetadataCrawler",
            name="bedrock-metadata-crawler",
            role=crawler_role.role_arn,
            database_name=glue_database.ref,
            targets=glue.CfnCrawler.TargetsProperty(
                catalog_targets=[
                    glue.CfnCrawler.CatalogTargetProperty(
                        database_name=glue_database.ref,
                        tables=[bedrock_metadata_table.ref],
                    ),
                ],
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                delete_behavior="LOG",
                update_behavior="LOG",
            ),
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                recrawl_behavior="CRAWL_EVERYTHING",
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression="cron(0 */3 * * ? *)",
            ),
        )
        bedrock_metadata_crawler.add_dependency(bedrock_metadata_table)

        # Load schema from Bedrock Pricing JSON file
        pricing_schema_path = "./glue/bedrock_pricing_schema.json"
        with Path.open(pricing_schema_path) as f:
            pricing_schema_content = f.read()
            pricing_schema = json.loads(pricing_schema_content)
            pricing_hash = hashlib.md5(pricing_schema_content.encode()).hexdigest()  #nosec noqa: S324 Hash is being used only for comparing file changes during cdk runs

        # Create Glue Table for Bedrock Pricing
        bedrock_pricing_table = glue.CfnTable(
            self,
            "BedrockPricingTable",
            catalog_id=account_id,
            database_name=glue_database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name="bedrock_pricing",
                description="Bedrock pricing information",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "csv",
                    "delimiter": ",",
                    "skip.header.line.count": "1",
                    "schema_hash": pricing_hash,
                },
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(
                            name=col["name"],
                            type=col["type"],
                        ) for col in pricing_schema["columns"]
                    ],
                    location=f"s3://{transformed_logs_bucket.bucket_name}/pricing/",
                    input_format="org.apache.hadoop.mapred.TextInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
                        parameters={
                            "field.delim": ",",
                            "skip.header.line.count": "1",
                        },
                    ),
                ),
            ),
        )
        bedrock_pricing_table.add_dependency(glue_database)

        # Create the Glue Crawler for Bedrock Pricing
        bedrock_pricing_crawler = glue.CfnCrawler(
            self,
            "BedrockPricingCrawler",
            name="bedrock-pricing-crawler",
            role=crawler_role.role_arn,
            database_name=glue_database.ref,
            targets=glue.CfnCrawler.TargetsProperty(
                catalog_targets=[
                    glue.CfnCrawler.CatalogTargetProperty(
                        database_name=glue_database.ref,
                        tables=[bedrock_pricing_table.ref],
                    ),
                ],
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                delete_behavior="LOG",
                update_behavior="LOG",
            ),
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                recrawl_behavior="CRAWL_EVERYTHING",
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(
                schedule_expression="cron(0 */3 * * ? *)",
            ),
        )
        bedrock_pricing_crawler.add_dependency(bedrock_pricing_table)


        # Get QuickSight principal ARN - replace with your QuickSight user/group ARN
        quicksight_principal = f"arn:aws:quicksight:{quicksight_region.value_as_string}:{self.account}:user/default/{quicksight_username.value_as_string}"

        # Create IAM role for QuickSight
        quicksight_role = iam.Role(
            self, "QuickSightRole",
            assumed_by=iam.ServicePrincipal("quicksight.amazonaws.com"),
        )

        # Add permissions for QuickSight to access Athena, Glue, and S3
        quicksight_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                    "athena:GetWorkGroup",
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:GetPartitions",
                    "s3:GetBucketLocation",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:ListAllMyBuckets",
                    "s3:ListBucketMultipartUploads",
                    "s3:ListMultipartUploadParts",
                    "s3:AbortMultipartUpload",
                ],
                resources=[
                    f"arn:aws:athena:{self.region}:{account_id}:workgroup/primary",
                    f"arn:aws:glue:{self.region}:{account_id}:catalog",
                    f"arn:aws:glue:{self.region}:{account_id}:database/{glue_database.ref}",
                    f"arn:aws:glue:{self.region}:{account_id}:table/{glue_database.ref}/*",
                    transformed_logs_bucket.bucket_arn,
                    f"{transformed_logs_bucket.bucket_arn}/*",
                ],
            ),
        )

        # Add managed policy for Athena access
        quicksight_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSQuicksightAthenaAccess"),
        )

        data_source_permissions = [
            quicksight.CfnDataSource.ResourcePermissionProperty(
                principal=quicksight_principal,
                actions=[
                    "quicksight:UpdateDataSourcePermissions",
                    "quicksight:DescribeDataSourcePermissions",
                    "quicksight:PassDataSource",
                    "quicksight:DescribeDataSource",
                    "quicksight:DeleteDataSource",
                    "quicksight:UpdateDataSource",
                ],
            ),
        ]

        dataset_permissions = [
            quicksight.CfnDataSet.ResourcePermissionProperty(
                principal=quicksight_principal,
                actions=[
                    "quicksight:PassDataSet",
                    "quicksight:DescribeIngestion",
                    "quicksight:CreateIngestion",
                    "quicksight:UpdateDataSet",
                    "quicksight:DeleteDataSet",
                    "quicksight:DescribeDataSet",
                    "quicksight:CancelIngestion",
                    "quicksight:DescribeDataSetPermissions",
                    "quicksight:ListIngestions",
                    "quicksight:UpdateDataSetPermissions",
                ],
            ),
        ]

        analysis_permissions = [
            quicksight.CfnAnalysis.ResourcePermissionProperty(
                principal=quicksight_principal,
                actions=[
                    "quicksight:RestoreAnalysis",
                    "quicksight:UpdateAnalysisPermissions",
                    "quicksight:DeleteAnalysis",
                    "quicksight:QueryAnalysis",
                    "quicksight:DescribeAnalysisPermissions",
                    "quicksight:DescribeAnalysis",
                    "quicksight:UpdateAnalysis",
                ],
            ),
        ]

        template_permissions = [
            quicksight.CfnTemplate.ResourcePermissionProperty(
                principal=quicksight_principal,
                actions=[
                    "quicksight:UpdateTemplatePermissions",
                    "quicksight:DescribeTemplatePermissions",
                    "quicksight:UpdateTemplateAlias",
                    "quicksight:DeleteTemplateAlias",
                    "quicksight:DescribeTemplateAlias",
                    "quicksight:ListTemplateAliases",
                    "quicksight:ListTemplates",
                    "quicksight:CreateTemplateAlias",
                    "quicksight:DeleteTemplate",
                    "quicksight:UpdateTemplate",
                    "quicksight:ListTemplateVersions",
                    "quicksight:DescribeTemplate",
                    "quicksight:CreateTemplate",
                ],
            ),
        ]

        dashboard_permissions = [
            quicksight.CfnDashboard.ResourcePermissionProperty(
                principal=quicksight_principal,
                actions=[
                    "quicksight:DescribeDashboard",
                    "quicksight:ListDashboardVersions",
                    "quicksight:UpdateDashboardPermissions",
                    "quicksight:QueryDashboard",
                    "quicksight:UpdateDashboard",
                    "quicksight:DeleteDashboard",
                    "quicksight:UpdateDashboardPublishedVersion",
                    "quicksight:DescribeDashboardPermissions",
                ],
            ),
        ]

        quicksight_datasource = quicksight.CfnDataSource(
            scope=self,
            id="BedrockLogsDataSource",
            name="bedrock-logs-datasource",
            data_source_id="bedrock-logs-datasource",
            aws_account_id=account_id,
            permissions=data_source_permissions,
            data_source_parameters=quicksight.CfnDataSource.DataSourceParametersProperty(
                athena_parameters=quicksight.CfnDataSource.AthenaParametersProperty(
                    work_group="primary",
                ),
            ),
            type="ATHENA",
        )

        # Create dataset for bedrock usage logs
        bedrock_logs_dataset = quicksight.CfnDataSet(
            scope=self,
            id="BedrockLogsDataSet",
            name="bedrock-usage-logs",
            data_set_id="bedrock-usage-logs",
            aws_account_id=self.account,
            physical_table_map={
                "BedrockLogsTable": quicksight.CfnDataSet.PhysicalTableProperty(
                    relational_table=quicksight.CfnDataSet.RelationalTableProperty(
                        data_source_arn=quicksight_datasource.attr_arn,
                        name="bedrock_usage_logs",
                        schema="bedrock",
                        input_columns=[
                            quicksight.CfnDataSet.InputColumnProperty(name="schematype", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="schemaversion", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="timestamp", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="accountid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="region", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="requestid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="operation", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="modelid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="identity_arn", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_contenttype", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="task_type", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_tokencount", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_contenttype", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_tokencount", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_latencyms", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="usage_inputtokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="usage_outputtokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="usage_totaltokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="image_width", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="image_height", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="numberOfImages", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_duration", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_resolution", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_duration", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_FPS", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_videoWidth", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_videoHeight", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="parsed_timestamp", type="DATETIME"),
                            quicksight.CfnDataSet.InputColumnProperty(name="tenantid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="year", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="month", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="date", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="batchid", type="STRING"),
                        ],
                    ),
                ),
            },
            logical_table_map={
                "BedrockLogsLogicalTable": quicksight.CfnDataSet.LogicalTableProperty(
                    alias="bedrock_logs",
                    source=quicksight.CfnDataSet.LogicalTableSourceProperty(
                        physical_table_id="BedrockLogsTable",
                    ),
                ),
            },
            permissions=dataset_permissions,
            import_mode="DIRECT_QUERY",
        )
        bedrock_logs_dataset.add_dependency(quicksight_datasource)

        # Create dataset for bedrock metadata
        bedrock_metadata_dataset = quicksight.CfnDataSet(
            scope=self,
            id="BedrockMetaDataDataSet",
            name="bedrock-usage-metadata",
            data_set_id="bedrock-usage-metadata",
            aws_account_id=self.account,
            physical_table_map={
                "BedrockMetaDataTable": quicksight.CfnDataSet.PhysicalTableProperty(
                    relational_table=quicksight.CfnDataSet.RelationalTableProperty(
                        data_source_arn=quicksight_datasource.attr_arn,
                        name="bedrock_usage_metadata",
                        schema="bedrock",
                        input_columns=[
                            quicksight.CfnDataSet.InputColumnProperty(name="timestamp", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="requestid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="accountid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="metadata_key", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="metadata_value", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="parsed_timestamp", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="tenantid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="year", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="month", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="date", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="batchid", type="STRING"),
                        ],
                    ),
                ),
            },
            logical_table_map={
                "BedrockMetaDataLogicalTable": quicksight.CfnDataSet.LogicalTableProperty(
                    alias="bedrock_metadata",
                    source=quicksight.CfnDataSet.LogicalTableSourceProperty(
                        physical_table_id="BedrockMetaDataTable",
                    ),
                ),
            },
            permissions=dataset_permissions,
            import_mode="DIRECT_QUERY",
        )
        bedrock_metadata_dataset.add_dependency(quicksight_datasource)

        # Create dataset for bedrock metadata
        bedrock_pricing_dataset = quicksight.CfnDataSet(
            scope=self,
            id="BedrockPricingDataSet",
            name="bedrock-pricing",
            data_set_id="bedrock-pricing",
            aws_account_id=self.account,
            physical_table_map={
                "BedrockPricingTable": quicksight.CfnDataSet.PhysicalTableProperty(
                    relational_table=quicksight.CfnDataSet.RelationalTableProperty(
                        data_source_arn=quicksight_datasource.attr_arn,
                        name="bedrock_pricing",
                        schema="bedrock",
                        input_columns=[
                            quicksight.CfnDataSet.InputColumnProperty(name="model_id", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_cost", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_cost", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cache_write", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cache_read", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="start_date", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="end_date", type="STRING"),
                        ],
                    ),
                ),
            },
            logical_table_map={
                "BedrockPricingLogicalTable": quicksight.CfnDataSet.LogicalTableProperty(
                    alias="bedrock_pricing",
                    source=quicksight.CfnDataSet.LogicalTableSourceProperty(
                        physical_table_id="BedrockPricingTable",
                    ),
                ),
            },
            permissions=dataset_permissions,
            import_mode="DIRECT_QUERY",
        )
        bedrock_pricing_dataset.add_dependency(quicksight_datasource)

        # Create dataset for bedrock logs with metadata pivot
        bedrock_logs_with_metadata_dataset = quicksight.CfnDataSet(
            scope=self,
            id="BedrockLogsWithMetadataDataSet",
            name="bedrock-logs-with-metadata",
            data_set_id="bedrock-logs-with-metadata",
            aws_account_id=self.account,
            physical_table_map={
                "BedrockLogsWithMetadataTable": quicksight.CfnDataSet.PhysicalTableProperty(
                    custom_sql=quicksight.CfnDataSet.CustomSqlProperty(
                        data_source_arn=quicksight_datasource.attr_arn,
                        name="bedrock_logs_with_metadata", 
                        sql_query=f"""
                            SELECT
                                logs.*,
                                MAX(CASE WHEN meta.metadata_key = 'TenantID' THEN meta.metadata_value END) AS tenant_id,
                                MAX(CASE WHEN meta.metadata_key = 'CostCenter' THEN meta.metadata_value END) AS cost_center,
                                MAX(CASE WHEN meta.metadata_key = 'ApplicationID' THEN meta.metadata_value END) AS application_id,
                                MAX(CASE WHEN meta.metadata_key = 'ModelName' THEN meta.metadata_value END) AS model_name,
                                MAX(CASE WHEN meta.metadata_key = 'Environment' THEN meta.metadata_value END) AS environment,
                                MAX(CASE WHEN meta.metadata_key = 'Department' THEN meta.metadata_value END) AS department,
                                MAX(CASE WHEN meta.metadata_key = 'Company' THEN meta.metadata_value END) AS company,
                                (logs.usage_inputtokens / 1000000.0) * price.input_cost AS input_cost,
                                (logs.usage_outputtokens / 1000000.0) * price.output_cost AS output_cost,
                                (logs.cache_readtokens / 1000000.0) * price.cache_read AS cache_read_cost,
                                (logs.cache_writetokens / 1000000.0) * price.cache_write AS cache_write_cost,
                                ((logs.usage_inputtokens / 1000000.0) * price.input_cost) +
                                ((logs.usage_outputtokens / 1000000.0) * price.output_cost) +
                                ((logs.cache_readtokens / 1000000.0) * price.cache_read) +
                                ((logs.cache_writetokens / 1000000.0) * price.cache_write) AS total_cost
                            FROM
                                "bedrock-{self.region}"."bedrock_usage_logs" logs
                            LEFT JOIN
                                "bedrock-{self.region}"."bedrock_usage_metadata" meta ON logs.requestid = meta.requestid
                                AND logs.year = meta.year
                                AND logs.month = meta.month
                                AND logs.date = meta.date
                            LEFT JOIN
                                "bedrock-{self.region}"."bedrock_pricing" price ON
                                CASE
                                    WHEN logs.modelid LIKE '%/%'
                                    THEN SUBSTRING(logs.modelid FROM (LENGTH(logs.modelid) - POSITION('/' IN REVERSE(logs.modelid)) + 2))
                                    ELSE logs.modelid
                                END = price.model_id
                                AND DATE_PARSE(SUBSTRING(logs.timestamp, 1, 10), '%Y-%m-%d') BETWEEN
                                    DATE_PARSE(price.start_date, '%m-%d-%Y')
                                    AND COALESCE(DATE_PARSE(price.end_date, '%m-%d-%Y'), DATE_PARSE('12-31-9999', '%m-%d-%Y'))
                            GROUP BY
                                logs.schematype, logs.schemaversion, logs.timestamp, logs.accountid, logs.region,
                                logs.requestid, logs.operation, logs.modelid, logs.identity_arn, logs.input_contenttype,
                                logs.task_type, logs.input_tokencount, logs.output_contenttype, logs.output_tokencount,
                                logs.output_latencyms, logs.usage_inputtokens, logs.usage_outputtokens, logs.usage_totaltokens,
                                logs.cache_readtokens, logs.cache_writetokens, logs.image_width, logs.image_height,
                                logs.numberOfImages, logs.input_duration, logs.input_resolution, logs.output_duration,
                                logs.output_FPS, logs.output_videoWidth, logs.output_videoHeight, logs.parsed_timestamp,
                                logs.tenantid, logs.year, logs.month, logs.date, logs.batchid,
                                price.input_cost, price.output_cost, price.cache_read, price.cache_write,price.model_id
                        """,  # noqa: S608 #nosec non-user facing sql
                        columns=[
                            quicksight.CfnDataSet.InputColumnProperty(name="schematype", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="schemaversion", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="timestamp", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="accountid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="region", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="requestid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="operation", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="modelid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="identity_arn", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_contenttype", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="task_type", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_tokencount", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_contenttype", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_tokencount", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_latencyms", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="usage_inputtokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="usage_outputtokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="usage_totaltokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cache_readtokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cache_writetokens", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="image_width", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="image_height", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="numberofimages", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_duration", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_resolution", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_duration", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_fps", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_videowidth", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_videoheight", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="parsed_timestamp", type="DATETIME"),
                            quicksight.CfnDataSet.InputColumnProperty(name="tenantid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="year", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="month", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="date", type="INTEGER"),
                            quicksight.CfnDataSet.InputColumnProperty(name="batchid", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="tenant_id", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cost_center", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="application_id", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="model_name", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="environment", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="department", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="company", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="model_id", type="STRING"),
                            quicksight.CfnDataSet.InputColumnProperty(name="input_cost", type="DECIMAL"),
                            quicksight.CfnDataSet.InputColumnProperty(name="output_cost", type="DECIMAL"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cache_read_cost", type="DECIMAL"),
                            quicksight.CfnDataSet.InputColumnProperty(name="cache_write_cost", type="DECIMAL"),
                            quicksight.CfnDataSet.InputColumnProperty(name="total_cost", type="DECIMAL"),
                        ],
                    ),
                ),
            },
            permissions=dataset_permissions,
            import_mode="DIRECT_QUERY",
        )
        bedrock_logs_with_metadata_dataset.add_dependency(quicksight_datasource)

        bedrock_analysis = quicksight.CfnAnalysis(
            scope=self,
            id="BedrockUsageAnalysis",
            analysis_id="bedrock-usage-analysis",
            name="Bedrock Usage Analysis",
            aws_account_id=self.account,
            definition=quicksight.CfnAnalysis.AnalysisDefinitionProperty(
                data_set_identifier_declarations=[
                    quicksight.CfnAnalysis.DataSetIdentifierDeclarationProperty(
                        data_set_arn=bedrock_logs_with_metadata_dataset.attr_arn,
                        identifier="bedrock_logs_with_metadata",
                    ),
                ],
                parameter_declarations=[
                    # Partition-based parameters
                    quicksight.CfnAnalysis.ParameterDeclarationProperty(
                        string_parameter_declaration=quicksight.CfnAnalysis.StringParameterDeclarationProperty(
                            parameter_value_type="MULTI_VALUED",
                            name="TenantIdParameter",
                            default_values=quicksight.CfnAnalysis.StringDefaultValuesProperty(
                                static_values=["All"],
                            ),
                        ),
                    ),
                    quicksight.CfnAnalysis.ParameterDeclarationProperty(
                        integer_parameter_declaration=quicksight.CfnAnalysis.IntegerParameterDeclarationProperty(
                            parameter_value_type="SINGLE_VALUED",
                            name="YearParameter",
                        ),
                    ),
                    quicksight.CfnAnalysis.ParameterDeclarationProperty(
                        integer_parameter_declaration=quicksight.CfnAnalysis.IntegerParameterDeclarationProperty(
                            parameter_value_type="SINGLE_VALUED",
                            name="MonthParameter",
                        ),
                    ),
                    quicksight.CfnAnalysis.ParameterDeclarationProperty(
                        integer_parameter_declaration=quicksight.CfnAnalysis.IntegerParameterDeclarationProperty(
                            parameter_value_type="SINGLE_VALUED",
                            name="DayParameter",
                        ),
                    ),
                    # Business parameters
                    quicksight.CfnAnalysis.ParameterDeclarationProperty(
                        string_parameter_declaration=quicksight.CfnAnalysis.StringParameterDeclarationProperty(
                            parameter_value_type="MULTI_VALUED",
                            name="ModelIdParameter",
                            default_values=quicksight.CfnAnalysis.StringDefaultValuesProperty(
                                static_values=["All"],
                            ),
                        ),
                    ),
                ],
                sheets=[
                    quicksight.CfnAnalysis.SheetDefinitionProperty(
                        sheet_id="main-sheet",
                        name="Bedrock Usage Overview",
                        parameter_controls=[
                            # Row 1: Time-based filters
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="year-control",
                                    title="Year",
                                    source_parameter_name="YearParameter",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="year",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="month-control",
                                    title="Month",
                                    source_parameter_name="MonthParameter",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="month",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="day-control",
                                    title="Day",
                                    source_parameter_name="DayParameter",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="date",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            # Row 2: Business filters
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="tenant-control",
                                    title="Tenant",
                                    source_parameter_name="TenantIdParameter",
                                    type="MULTI_SELECT",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="tenant_id",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="model-control",
                                    title="Model",
                                    source_parameter_name="ModelIdParameter",
                                    type="MULTI_SELECT",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="modelid",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        visuals=[
                            # Bar chart for usage summary (converted from table)
                            quicksight.CfnAnalysis.VisualProperty(
                                bar_chart_visual=quicksight.CfnAnalysis.BarChartVisualProperty(
                                    visual_id="usage-summary-bar",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Token Usage by Tenant",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.BarChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.BarChartFieldWellsProperty(
                                            bar_chart_aggregated_field_wells=quicksight.CfnAnalysis.BarChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="tenant_id_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="tenant_id",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="total_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_totaltokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        orientation="HORIZONTAL",
                                        # Removing sort configuration as it's causing errors
                                    ),
                                ),
                            ),
                            # Pie chart for company usage distribution
                            quicksight.CfnAnalysis.VisualProperty(
                                pie_chart_visual=quicksight.CfnAnalysis.PieChartVisualProperty(
                                    visual_id="company-distribution-pie",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Token Usage by Company",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.PieChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.PieChartFieldWellsProperty(
                                            pie_chart_aggregated_field_wells=quicksight.CfnAnalysis.PieChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="company_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="company",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="company_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_totaltokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            # Bar chart for department usage
                            quicksight.CfnAnalysis.VisualProperty(
                                bar_chart_visual=quicksight.CfnAnalysis.BarChartVisualProperty(
                                    visual_id="department-usage-bar",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Token Usage by Department",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.BarChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.BarChartFieldWellsProperty(
                                            bar_chart_aggregated_field_wells=quicksight.CfnAnalysis.BarChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="department_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="department",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="department_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_totaltokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        orientation="HORIZONTAL",
                                    ),
                                ),
                            ),
                            # Sample Donut Chart for Model Distribution
                            quicksight.CfnAnalysis.VisualProperty(
                                pie_chart_visual=quicksight.CfnAnalysis.PieChartVisualProperty(
                                    visual_id="model-distribution-donut",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Model Distribution",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.PieChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.PieChartFieldWellsProperty(
                                            pie_chart_aggregated_field_wells=quicksight.CfnAnalysis.PieChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="model_id_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="modelid",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="model_count_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_totaltokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="COUNT",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        donut_options=quicksight.CfnAnalysis.DonutOptionsProperty(
                                            arc_options=quicksight.CfnAnalysis.ArcOptionsProperty(
                                                arc_thickness="MEDIUM",
                                            ),
                                        ),
                                    ),
                                ),
                            ),

                        ],
                    ),
                    quicksight.CfnAnalysis.SheetDefinitionProperty(
                        sheet_id="trends-sheet",
                        name="Usage Trends",
                        parameter_controls=[
                            # Row 1: Time-based filters
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="year-control-trends",
                                    title="Year",
                                    source_parameter_name="YearParameter",
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="month-control-trends",
                                    title="Month",
                                    source_parameter_name="MonthParameter",
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="day-control-trends",
                                    title="Day",
                                    source_parameter_name="DayParameter",
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            # Row 2: Business filters
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="tenant-control-trends",
                                    title="Tenant",
                                    source_parameter_name="TenantIdParameter",
                                    type="MULTI_SELECT",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="tenantid",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="model-control-trends",
                                    title="Model",
                                    source_parameter_name="ModelIdParameter",
                                    type="MULTI_SELECT",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="modelid",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        visuals=[
                            # Line chart for usage over time
                            quicksight.CfnAnalysis.VisualProperty(
                                line_chart_visual=quicksight.CfnAnalysis.LineChartVisualProperty(
                                    visual_id="usage-trend-line",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Token Usage Over Time",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.LineChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.LineChartFieldWellsProperty(
                                            line_chart_aggregated_field_wells=quicksight.CfnAnalysis.LineChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        date_dimension_field=quicksight.CfnAnalysis.DateDimensionFieldProperty(
                                                            field_id="date_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="parsed_timestamp",
                                                            ),
                                                            date_granularity="DAY",
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="daily_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_totaltokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                colors=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="model_color_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="modelid",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            # Input vs Output Tokens Stacked Bar Chart
                            quicksight.CfnAnalysis.VisualProperty(
                                bar_chart_visual=quicksight.CfnAnalysis.BarChartVisualProperty(
                                    visual_id="input-output-tokens-bar",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Input vs Output Tokens by Day",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.BarChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.BarChartFieldWellsProperty(
                                            bar_chart_aggregated_field_wells=quicksight.CfnAnalysis.BarChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        date_dimension_field=quicksight.CfnAnalysis.DateDimensionFieldProperty(
                                                            field_id="date_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="parsed_timestamp",
                                                            ),
                                                            date_granularity="DAY",
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="input_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_inputtokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="output_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_outputtokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        # Removed custom color palette as it's causing validation errors

                                        orientation="VERTICAL",
                                    ),
                                ),
                            ),
                            # Average Latency by Model
                            quicksight.CfnAnalysis.VisualProperty(
                                bar_chart_visual=quicksight.CfnAnalysis.BarChartVisualProperty(
                                    visual_id="latency-by-model-bar",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Average Latency by Model (ms)",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.BarChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.BarChartFieldWellsProperty(
                                            bar_chart_aggregated_field_wells=quicksight.CfnAnalysis.BarChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="model_latency_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="modelid",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="avg_latency_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="output_latencyms",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="AVERAGE",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        orientation="HORIZONTAL",
                                    ),
                                ),
                            ),
                            # Usage by Environment Pie Chart
                            quicksight.CfnAnalysis.VisualProperty(
                                pie_chart_visual=quicksight.CfnAnalysis.PieChartVisualProperty(
                                    visual_id="usage-by-environment-pie",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Token Usage by Environment",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.PieChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.PieChartFieldWellsProperty(
                                            pie_chart_aggregated_field_wells=quicksight.CfnAnalysis.PieChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="environment_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="environment",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="env_tokens_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="usage_totaltokens",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ],
                    ),
                    quicksight.CfnAnalysis.SheetDefinitionProperty(
                        sheet_id="cost-trends-sheet",
                        name="Cost Trends",
                        parameter_controls=[
                            # Row 1: Time-based filters
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="year-control-cost",
                                    title="Year",
                                    source_parameter_name="YearParameter",
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="month-control-cost",
                                    title="Month",
                                    source_parameter_name="MonthParameter",
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="day-control-cost",
                                    title="Day",
                                    source_parameter_name="DayParameter",
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            # Row 2: Business filters
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="tenant-control-cost",
                                    title="Tenant",
                                    source_parameter_name="TenantIdParameter",
                                    type="MULTI_SELECT",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="tenantid",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            quicksight.CfnAnalysis.ParameterControlProperty(
                                dropdown=quicksight.CfnAnalysis.ParameterDropDownControlProperty(
                                    parameter_control_id="model-control-cost",
                                    title="Model",
                                    source_parameter_name="ModelIdParameter",
                                    type="MULTI_SELECT",
                                    selectable_values=quicksight.CfnAnalysis.ParameterSelectableValuesProperty(
                                        link_to_data_set_column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                            data_set_identifier="bedrock_logs_with_metadata",
                                            column_name="modelid",
                                        ),
                                    ),
                                    display_options=quicksight.CfnAnalysis.DropDownControlDisplayOptionsProperty(
                                        title_options=quicksight.CfnAnalysis.LabelOptionsProperty(
                                            visibility="VISIBLE",
                                            font_configuration=quicksight.CfnAnalysis.FontConfigurationProperty(
                                                font_size=quicksight.CfnAnalysis.FontSizeProperty(relative="SMALL"),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        visuals=[
                            # Line chart for cost over time
                            quicksight.CfnAnalysis.VisualProperty(
                                line_chart_visual=quicksight.CfnAnalysis.LineChartVisualProperty(
                                    visual_id="cost-trend-line",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Cost Over Time",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.LineChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.LineChartFieldWellsProperty(
                                            line_chart_aggregated_field_wells=quicksight.CfnAnalysis.LineChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        date_dimension_field=quicksight.CfnAnalysis.DateDimensionFieldProperty(
                                                            field_id="date_cost_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="parsed_timestamp",
                                                            ),
                                                            date_granularity="DAY",
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="daily_cost_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="total_cost",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                colors=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="model_color_cost_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="modelid",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                            # Cost breakdown by type
                            quicksight.CfnAnalysis.VisualProperty(
                                bar_chart_visual=quicksight.CfnAnalysis.BarChartVisualProperty(
                                    visual_id="cost-breakdown-bar",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Cost Breakdown by Type",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.BarChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.BarChartFieldWellsProperty(
                                            bar_chart_aggregated_field_wells=quicksight.CfnAnalysis.BarChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="model_breakdown_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="modelid",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="input_cost_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="input_cost",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        orientation="HORIZONTAL",
                                    ),
                                ),
                            ),
                            # Output cost breakdown
                            quicksight.CfnAnalysis.VisualProperty(
                                bar_chart_visual=quicksight.CfnAnalysis.BarChartVisualProperty(
                                    visual_id="output-cost-breakdown-bar",
                                    title=quicksight.CfnAnalysis.VisualTitleLabelOptionsProperty(
                                        visibility="VISIBLE",
                                        format_text=quicksight.CfnAnalysis.ShortFormatTextProperty(
                                            plain_text="Output Cost by Model",
                                        ),
                                    ),
                                    chart_configuration=quicksight.CfnAnalysis.BarChartConfigurationProperty(
                                        field_wells=quicksight.CfnAnalysis.BarChartFieldWellsProperty(
                                            bar_chart_aggregated_field_wells=quicksight.CfnAnalysis.BarChartAggregatedFieldWellsProperty(
                                                category=[
                                                    quicksight.CfnAnalysis.DimensionFieldProperty(
                                                        categorical_dimension_field=quicksight.CfnAnalysis.CategoricalDimensionFieldProperty(
                                                            field_id="model_output_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="modelid",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                                values=[
                                                    quicksight.CfnAnalysis.MeasureFieldProperty(
                                                        numerical_measure_field=quicksight.CfnAnalysis.NumericalMeasureFieldProperty(
                                                            field_id="output_cost_field",
                                                            column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                                                data_set_identifier="bedrock_logs_with_metadata",
                                                                column_name="output_cost",
                                                            ),
                                                            aggregation_function=quicksight.CfnAnalysis.NumericalAggregationFunctionProperty(
                                                                simple_numerical_aggregation="SUM",
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        orientation="HORIZONTAL",
                                    ),
                                ),
                            ),
                        ],
                    ),
                ],
                filter_groups=[
                    quicksight.CfnAnalysis.FilterGroupProperty(
                        filter_group_id="tenant-filter-group",
                        cross_dataset="SINGLE_DATASET",
                        filters=[
                            quicksight.CfnAnalysis.FilterProperty(
                                category_filter=quicksight.CfnAnalysis.CategoryFilterProperty(
                                    filter_id="tenant-filter",
                                    column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                        data_set_identifier="bedrock_logs_with_metadata",
                                        column_name="tenant_id",
                                    ),
                                    configuration=quicksight.CfnAnalysis.CategoryFilterConfigurationProperty(
                                        custom_filter_configuration=quicksight.CfnAnalysis.CustomFilterConfigurationProperty(
                                            match_operator="EQUALS",
                                            parameter_name="TenantIdParameter",
                                            null_option="ALL_VALUES",
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        scope_configuration=quicksight.CfnAnalysis.FilterScopeConfigurationProperty(
                            selected_sheets=quicksight.CfnAnalysis.SelectedSheetsFilterScopeConfigurationProperty(
                                sheet_visual_scoping_configurations=[
                                    quicksight.CfnAnalysis.SheetVisualScopingConfigurationProperty(
                                        sheet_id="main-sheet",
                                        scope="ALL_VISUALS",
                                    ),
                                ],
                            ),
                        ),
                        status="ENABLED",
                    ),
                    quicksight.CfnAnalysis.FilterGroupProperty(
                        filter_group_id="year-filter-group",
                        cross_dataset="SINGLE_DATASET",
                        filters=[
                            quicksight.CfnAnalysis.FilterProperty(
                                category_filter=quicksight.CfnAnalysis.CategoryFilterProperty(
                                    filter_id="year-filter",
                                    column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                        data_set_identifier="bedrock_logs_with_metadata",
                                        column_name="year",
                                    ),
                                    configuration=quicksight.CfnAnalysis.CategoryFilterConfigurationProperty(
                                        custom_filter_configuration=quicksight.CfnAnalysis.CustomFilterConfigurationProperty(
                                            match_operator="EQUALS",
                                            parameter_name="YearParameter",
                                            null_option="ALL_VALUES",
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        scope_configuration=quicksight.CfnAnalysis.FilterScopeConfigurationProperty(
                            selected_sheets=quicksight.CfnAnalysis.SelectedSheetsFilterScopeConfigurationProperty(
                                sheet_visual_scoping_configurations=[
                                    quicksight.CfnAnalysis.SheetVisualScopingConfigurationProperty(
                                        sheet_id="main-sheet",
                                        scope="ALL_VISUALS",
                                    ),
                                ],
                            ),
                        ),
                        status="ENABLED",
                    ),
                    quicksight.CfnAnalysis.FilterGroupProperty(
                        filter_group_id="month-filter-group",
                        cross_dataset="SINGLE_DATASET",
                        filters=[
                            quicksight.CfnAnalysis.FilterProperty(
                                category_filter=quicksight.CfnAnalysis.CategoryFilterProperty(
                                    filter_id="month-filter",
                                    column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                        data_set_identifier="bedrock_logs_with_metadata",
                                        column_name="month",
                                    ),
                                    configuration=quicksight.CfnAnalysis.CategoryFilterConfigurationProperty(
                                        custom_filter_configuration=quicksight.CfnAnalysis.CustomFilterConfigurationProperty(
                                            match_operator="EQUALS",
                                            parameter_name="MonthParameter",
                                            null_option="ALL_VALUES",
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        scope_configuration=quicksight.CfnAnalysis.FilterScopeConfigurationProperty(
                            selected_sheets=quicksight.CfnAnalysis.SelectedSheetsFilterScopeConfigurationProperty(
                                sheet_visual_scoping_configurations=[
                                    quicksight.CfnAnalysis.SheetVisualScopingConfigurationProperty(
                                        sheet_id="main-sheet",
                                        scope="ALL_VISUALS",
                                    ),
                                ],
                            ),
                        ),
                        status="ENABLED",
                    ),
                    quicksight.CfnAnalysis.FilterGroupProperty(
                        filter_group_id="day-filter-group",
                        cross_dataset="SINGLE_DATASET",
                        filters=[
                            quicksight.CfnAnalysis.FilterProperty(
                                category_filter=quicksight.CfnAnalysis.CategoryFilterProperty(
                                    filter_id="day-filter",
                                    column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                        data_set_identifier="bedrock_logs_with_metadata",
                                        column_name="date",
                                    ),
                                    configuration=quicksight.CfnAnalysis.CategoryFilterConfigurationProperty(
                                        custom_filter_configuration=quicksight.CfnAnalysis.CustomFilterConfigurationProperty(
                                            match_operator="EQUALS",
                                            parameter_name="DayParameter",
                                            null_option="ALL_VALUES",
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        scope_configuration=quicksight.CfnAnalysis.FilterScopeConfigurationProperty(
                            selected_sheets=quicksight.CfnAnalysis.SelectedSheetsFilterScopeConfigurationProperty(
                                sheet_visual_scoping_configurations=[
                                    quicksight.CfnAnalysis.SheetVisualScopingConfigurationProperty(
                                        sheet_id="main-sheet",
                                        scope="ALL_VISUALS",
                                    ),
                                ],
                            ),
                        ),
                        status="ENABLED",
                    ),
                    quicksight.CfnAnalysis.FilterGroupProperty(
                        filter_group_id="model-filter-group",
                        cross_dataset="SINGLE_DATASET",
                        filters=[
                            quicksight.CfnAnalysis.FilterProperty(
                                category_filter=quicksight.CfnAnalysis.CategoryFilterProperty(
                                    filter_id="model-filter",
                                    column=quicksight.CfnAnalysis.ColumnIdentifierProperty(
                                        data_set_identifier="bedrock_logs_with_metadata",
                                        column_name="modelid",
                                    ),
                                    configuration=quicksight.CfnAnalysis.CategoryFilterConfigurationProperty(
                                        custom_filter_configuration=quicksight.CfnAnalysis.CustomFilterConfigurationProperty(
                                            match_operator="EQUALS",
                                            parameter_name="ModelIdParameter",
                                            null_option="ALL_VALUES",
                                        ),
                                    ),
                                ),
                            ),
                        ],
                        scope_configuration=quicksight.CfnAnalysis.FilterScopeConfigurationProperty(
                            selected_sheets=quicksight.CfnAnalysis.SelectedSheetsFilterScopeConfigurationProperty(
                                sheet_visual_scoping_configurations=[
                                    quicksight.CfnAnalysis.SheetVisualScopingConfigurationProperty(
                                        sheet_id="main-sheet",
                                        scope="ALL_VISUALS",
                                    ),
                                ],
                            ),
                        ),
                        status="ENABLED",
                    ),
                ],
            ),
            permissions=analysis_permissions,
        )
        bedrock_analysis.add_dependency(bedrock_logs_with_metadata_dataset)

        # Generate a unique timestamp for this deployment
        deployment_timestamp = str(int(time.time()))

        bedrock_template = quicksight.CfnTemplate(
            scope=self,
            id="BedrockUsageTemplate",
            template_id=f"bedrock-usage-template-{deployment_timestamp}",
            name="Bedrock Usage Dashboard Template",
            aws_account_id=self.account,
            source_entity=quicksight.CfnTemplate.TemplateSourceEntityProperty(
                source_analysis=quicksight.CfnTemplate.TemplateSourceAnalysisProperty(
                    arn=bedrock_analysis.attr_arn,
                    data_set_references=[
                        quicksight.CfnTemplate.DataSetReferenceProperty(
                            data_set_arn=bedrock_logs_with_metadata_dataset.attr_arn,
                            data_set_placeholder="bedrock_logs_with_metadata",
                        ),
                    ],
                ),
            ),
            permissions=template_permissions,
        )
        bedrock_template.add_dependency(bedrock_analysis)

        # Step 3: Create Dashboard from the Template
        bedrock_dashboard = quicksight.CfnDashboard(
            scope=self,
            id="BedrockUsageDashboard",
            dashboard_id=f"bedrock-usage-dashboard-{deployment_timestamp}",
            name="Bedrock Usage Dashboard",
            aws_account_id=self.account,
            source_entity=quicksight.CfnDashboard.DashboardSourceEntityProperty(
                source_template=quicksight.CfnDashboard.DashboardSourceTemplateProperty(
                    arn=bedrock_template.attr_arn,
                    data_set_references=[
                        quicksight.CfnDashboard.DataSetReferenceProperty(
                            data_set_arn=bedrock_logs_with_metadata_dataset.attr_arn,
                            data_set_placeholder="bedrock_logs_with_metadata",
                        ),
                    ],
                ),
            ),
            permissions=dashboard_permissions,
            dashboard_publish_options=quicksight.CfnDashboard.DashboardPublishOptionsProperty(
                ad_hoc_filtering_option=quicksight.CfnDashboard.AdHocFilteringOptionProperty(
                    availability_status="ENABLED",
                ),
                export_to_csv_option=quicksight.CfnDashboard.ExportToCSVOptionProperty(
                    availability_status="ENABLED",
                ),
                sheet_controls_option=quicksight.CfnDashboard.SheetControlsOptionProperty(
                    visibility_state="EXPANDED",
                ),
            ),
        )
        bedrock_dashboard.add_dependency(bedrock_template)

        # Create dashboard URL output
        dashboard_url = f"https://{self.region}.quicksight.aws.amazon.com/sn/dashboards/{bedrock_dashboard.dashboard_id}"
        CfnOutput(
            self, "DashboardURL",
            description="URL to access the Bedrock Cost Reporting dashboard",
            value=dashboard_url,
        )

        # Create transformed bucket name output
        CfnOutput(
            self, "TransformedBucketName",
            description="Name of the S3 bucket containing transformed Bedrock logs",
            value=transformed_logs_bucket.bucket_name,
        )

