#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ecs,
  aws_iam
)

from constructs import Construct
from typing import List


def check_env_variables(envars: dict, vars: List[str]):
  for k in vars:
    assert envars.get(k)


class ECSTaskStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, ecr_repository, database_secret, load_balancer_url, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    task_role_policy_doc = aws_iam.PolicyDocument()
    task_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
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

    task_definition = aws_ecs.FargateTaskDefinition(self, "LangFuseServer",
      task_role=task_role,
      cpu=1 * 1024,
      memory_limit_mib=2 * 1024
    )

    db_conn_info = {
      "DATABASE_HOST": database_secret.secret_value_from_json("host").unsafe_unwrap(),
      "DATABASE_PORT": database_secret.secret_value_from_json("port").unsafe_unwrap(),
      "DATABASE_USERNAME": database_secret.secret_value_from_json("username").unsafe_unwrap(),
      "DATABASE_PASSWORD": database_secret.secret_value_from_json("password").unsafe_unwrap(),
      "DATABASE_NAME": "postgres"
    }
    DATABASE_URL = "postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}".format(**db_conn_info)

    docker_run_args = self.node.try_get_context('langfuse_env')
    task_env = {
      **docker_run_args,
      "NEXTAUTH_URL": load_balancer_url,
      "DATABASE_URL": DATABASE_URL
    }

    check_env_variables(task_env,
      [
        'NODE_ENV', 'NEXTAUTH_SECRET', 'SALT',
        'TELEMETRY_ENABLED', 'NEXTAUTH_URL', 'NEXT_PUBLIC_SIGN_UP_DISABLED',
        'LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES', 'DATABASE_URL'
      ]
    )

    container = task_definition.add_container("LangFuseServer",
      image=aws_ecs.ContainerImage.from_ecr_repository(ecr_repository, tag="latest"),
      environment=task_env,
      logging=aws_ecs.LogDriver.aws_logs(stream_prefix="langfuse-server"),
    )

    port_mapping = aws_ecs.PortMapping(
      container_port=3000,
      host_port=3000,
      protocol=aws_ecs.Protocol.TCP
    )
    container.add_port_mappings(port_mapping)

    self.ecs_task_definition = task_definition


    cdk.CfnOutput(self, 'TaskDefinitionArn',
      value=self.ecs_task_definition.task_definition_arn,
      export_name=f'{self.stack_name}-TaskDefinitionArn')
