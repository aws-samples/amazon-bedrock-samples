#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_ecs
)

from constructs import Construct


class ECSFargateServiceClickhouseStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    vpc,
    ecs_cluster,
    ecs_task_definition,
    sg_efs_inbound,
    cloud_map_service,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    self.sg_clickhouse_client = aws_ec2.SecurityGroup(self, 'ClickhouseClientSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for clickhouse client',
      security_group_name=f'{self.stack_name.lower()}-clickhouse-client-sg'
    )
    cdk.Tags.of(self.sg_clickhouse_client).add('Name', 'clickhouse-client-sg')

    sg_clickhouse_server = aws_ec2.SecurityGroup(self, 'ECSFargateServiceSG',
      vpc=vpc,
      allow_all_outbound=True,
      description="Allow inbound from VPC for ECS Fargate Service",
      security_group_name=f'{self.stack_name.lower()}-clickhouse-server-sg'
    )
    sg_clickhouse_server.add_ingress_rule(peer=self.sg_clickhouse_client,
      connection=aws_ec2.Port.tcp(8123),
      description='clickhouse http interface')
    sg_clickhouse_server.add_ingress_rule(peer=self.sg_clickhouse_client,
      connection=aws_ec2.Port.tcp(9000),
      description='clickhouse http interface')
    cdk.Tags.of(sg_clickhouse_server).add('Name', 'clickhouse-server-sg')

    self.fargate_service = aws_ecs.FargateService(self, "FargateService",
      service_name="clickhouse",
      cluster=ecs_cluster,
      task_definition=ecs_task_definition,
      desired_count=1,
      min_healthy_percent=50,
      security_groups=[sg_clickhouse_server, sg_efs_inbound],
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS),
    )
    self.fargate_service.associate_cloud_map_service(
      service=cloud_map_service,
      container_port=self.fargate_service.task_definition.default_container.container_port)
    cdk.Tags.of(self.fargate_service).add('Name', 'langfuse_clickhouse')

    self.clickhouse_migration_url = f"clickhouse://{cloud_map_service.service_name}.{cloud_map_service.namespace.namespace_name}:9000"
    self.clickhouse_url = f"http://{cloud_map_service.service_name}.{cloud_map_service.namespace.namespace_name}:8123"
    # Outputs:
    #   ClickhouseMigrationUrl = clickhouse://clickhouse.langfuse.local:9000
    #   ClickhouseUrl = http://clickhouse.langfuse.local:8123


    cdk.CfnOutput(self, "ClickhouseUrl",
      value=self.clickhouse_url,
      export_name=f'{self.stack_name}-ClickhouseUrl')
    cdk.CfnOutput(self, "ClickhouseMigrationUrl",
      value=self.clickhouse_migration_url,
      export_name=f'{self.stack_name}-ClickhouseMigrationUrl')
    cdk.CfnOutput(self, "FargateServiceName",
      value=self.fargate_service.service_name,
      export_name=f'{self.stack_name}-FargateServiceName')
    cdk.CfnOutput(self, "FargateServiceArn",
      value=self.fargate_service.service_arn,
      export_name=f'{self.stack_name}-FargateServiceArn')
    cdk.CfnOutput(self, "TaskDefinitionArn",
      value=self.fargate_service.task_definition.task_definition_arn,
      export_name=f'{self.stack_name}-TaskDefinitionArn')
    cdk.CfnOutput(self, "ClusterName",
      value=self.fargate_service.cluster.cluster_name,
      export_name=f'{self.stack_name}-ClusterName')
