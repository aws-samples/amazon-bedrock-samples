#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ecs,
  aws_iam,
  aws_logs
)

from constructs import Construct


class ECSTaskLangfuseWorkerStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    ecr_repositories,
    database_secret,
    clickhouse_secret,
    clickhouse_migration_url,
    clickhouse_url,
    redis_cluster,
    s3_blob_bucket,
    s3_event_bucket,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    task_role_policy_doc = aws_iam.PolicyDocument()
    task_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "secretsmanager:*",
        "s3:*",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    }))

    task_role = aws_iam.Role(self, "ECSTaskRole",
      role_name=f'ECSTaskRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
      inline_policies={
        'ecs_task_role_policy': task_role_policy_doc
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
      ]
    )

    self.ecs_task_definition = aws_ecs.FargateTaskDefinition(self, "LangfuseWorkerTaskDef",
      family="langfuse-worker",
      task_role=task_role,
      cpu=2*1024,
      memory_limit_mib=4*1024
    )

    db_conn_info = {
      "DATABASE_HOST": database_secret.secret_value_from_json("host").unsafe_unwrap(),
      "DATABASE_PORT": database_secret.secret_value_from_json("port").unsafe_unwrap(),
      "DATABASE_USERNAME": database_secret.secret_value_from_json("username").unsafe_unwrap(),
      "DATABASE_PASSWORD": database_secret.secret_value_from_json("password").unsafe_unwrap(),
      "DATABASE_NAME": "postgres"
    }
    DATABASE_URL = "postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}".format(**db_conn_info)

    redis_conn_info = {
      "REDIS_HOST": redis_cluster.attr_primary_end_point_address,
      "REDIS_PORT": redis_cluster.attr_primary_end_point_port
    }
    REDIS_CONNECTION_STRING = "redis://{REDIS_HOST}:{REDIS_PORT}".format(**redis_conn_info)

    # Environment Variables for the Langfuse Worker container
    # https://langfuse.com/self-hosting/configuration#environment-variables
    docker_run_args = self.node.try_get_context('langfuse_worker_env')
    task_env = {
      **docker_run_args,

      "DATABASE_URL": DATABASE_URL,

      "CLICKHOUSE_MIGRATION_URL": clickhouse_migration_url,
      "CLICKHOUSE_URL": clickhouse_url,
      "CLICKHOUSE_DB": clickhouse_secret.secret_value_from_json("database").unsafe_unwrap(),
      "CLICKHOUSE_USER": clickhouse_secret.secret_value_from_json("user").unsafe_unwrap(),
      "CLICKHOUSE_PASSWORD": clickhouse_secret.secret_value_from_json("password").unsafe_unwrap(),
      "CLICKHOUSE_CLUSTER_ENABLED": "false",

      "REDIS_CONNECTION_STRING": REDIS_CONNECTION_STRING,

      "LANGFUSE_S3_EVENT_UPLOAD_BUCKET": s3_event_bucket.bucket_name,
      "LANGFUSE_S3_EVENT_UPLOAD_PREFIX": "events/",
      "LANGFUSE_S3_EVENT_UPLOAD_REGION": self.region,

      "LANGFUSE_S3_MEDIA_UPLOAD_BUCKET": s3_blob_bucket.bucket_name,
      # "LANGFUSE_S3_MEDIA_UPLOAD_PREFIX": "media/", # default: "" (the bucket root)
      "LANGFUSE_S3_MEDIA_UPLOAD_ENABLED": "true",
    }

    repository = ecr_repositories['langfuse-worker']
    container = self.ecs_task_definition.add_container("LangfuseWorkerContainerDef",
      container_name="worker",
      image=aws_ecs.ContainerImage.from_ecr_repository(repository, tag="latest"),
      # essential=True,
      environment=task_env,
      logging=aws_ecs.LogDriver.aws_logs(
        stream_prefix="langfuse-worker",
        log_retention=aws_logs.RetentionDays.ONE_WEEK
      )
    )

    port_mapping = aws_ecs.PortMapping(
      container_port=3030,
      host_port=3030,
      protocol=aws_ecs.Protocol.TCP
    )
    container.add_port_mappings(port_mapping)


    cdk.CfnOutput(self, 'TaskDefinitionArn',
      value=self.ecs_task_definition.task_definition_arn,
      export_name=f'{self.stack_name}-TaskDefinitionArn')
