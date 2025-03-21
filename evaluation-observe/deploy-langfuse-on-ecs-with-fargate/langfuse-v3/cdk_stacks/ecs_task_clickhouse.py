#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import json

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ecs,
  aws_iam,
  aws_logs,
  aws_secretsmanager
)

from constructs import Construct


class ECSTaskClickhouseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    ecr_repositories,
    efs_file_system,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    task_execution_role_policy_doc = aws_iam.PolicyDocument()
    task_execution_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    }))

    task_execution_role = aws_iam.Role(self, "ECSTaskExecutionRole",
      role_name=f'ECSTaskExecutionRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
      inline_policies={
        'ecs_task_execution_role_policy': task_execution_role_policy_doc
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
      ]
    )

    task_role_policy_doc = aws_iam.PolicyDocument()
    task_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": ["*"],
      "actions": [
        "secretsmanager:*",
        "s3:*",
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
      ]
    }))

    task_role = aws_iam.Role(self, "ECSTaskRole",
      role_name=f'ECSTaskRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
      inline_policies={
        'ecs_task_role_policy': task_role_policy_doc
      },
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
      ]
    )

    efs_volume = aws_ecs.Volume(
      name="clickhouse_data",
      efs_volume_configuration=aws_ecs.EfsVolumeConfiguration(
        file_system_id=efs_file_system.file_system_id,
        root_directory="/"
      )
    )

    self.ecs_task_definition = aws_ecs.FargateTaskDefinition(self, "ClickhouseTaskDef",
      family="clickhouse",
      cpu=1*1024,
      memory_limit_mib=8*1024,
      execution_role=task_execution_role,
      task_role=task_role,
      volumes=[efs_volume]
    )

    self.clickhouse_secret = aws_secretsmanager.Secret(self, "ClickhouseSecret",
      generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        secret_string_template=json.dumps({
          "database": "default",
          "user": "clickhouse"
        }),
        generate_string_key="password",
        exclude_punctuation=True,
        password_length=8
      )
    )

    task_env = {
      "CLICKHOUSE_DB": self.clickhouse_secret.secret_value_from_json("database").unsafe_unwrap(),
      "CLICKHOUSE_USER": self.clickhouse_secret.secret_value_from_json("user").unsafe_unwrap(),
      "CLICKHOUSE_PASSWORD": self.clickhouse_secret.secret_value_from_json("password").unsafe_unwrap()
    }

    task_health_check = aws_ecs.HealthCheck(
      command=["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:8123/ping || exit 1"],
      interval=cdk.Duration.minutes(5), # cdk.Duration.seconds(5)
      retries=10,
      start_period=cdk.Duration.minutes(1), # cdk.Duration.seconds(1)
      timeout=cdk.Duration.seconds(5)
    )

    repository = ecr_repositories['clickhouse']
    container = self.ecs_task_definition.add_container("Clickhouse",
      container_name="clickhouse",
      image=aws_ecs.ContainerImage.from_ecr_repository(repository, tag="latest"),
      cpu=1*1024,
      memory_limit_mib=8*1024,
      environment=task_env,
      health_check=task_health_check,
      logging=aws_ecs.LogDriver.aws_logs(
        stream_prefix="clickhouse",
        log_retention=aws_logs.RetentionDays.ONE_WEEK
      ),
      port_mappings=[
        # ClickHouse HTTP interface
        aws_ecs.PortMapping(
          container_port=8123,
          host_port=8123,
          protocol=aws_ecs.Protocol.TCP
        ),
        # ClickHouse native interface
        aws_ecs.PortMapping(
          container_port=9000,
          host_port=9000,
          protocol=aws_ecs.Protocol.TCP
        )
      ],
      ulimits=[
        aws_ecs.Ulimit(
          name=aws_ecs.UlimitName.NOFILE,
          soft_limit=65535,
          hard_limit=65535
        )
      ]
    )

    mount_point = aws_ecs.MountPoint(
      container_path="/var/lib/clickhouse",
      read_only=False,
      source_volume="clickhouse_data"
    )
    container.add_mount_points(mount_point)

    efs_file_system.grant_root_access(self.ecs_task_definition.task_role.grant_principal)


    cdk.CfnOutput(self, 'TaskDefinitionArn',
      value=self.ecs_task_definition.task_definition_arn,
      export_name=f'{self.stack_name}-TaskDefinitionArn')
