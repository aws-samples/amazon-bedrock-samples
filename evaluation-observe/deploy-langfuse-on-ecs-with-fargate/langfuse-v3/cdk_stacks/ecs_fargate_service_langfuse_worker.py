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


class ECSFargateServiceLangfuseWorkerStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    vpc,
    ecs_cluster,
    ecs_task_definition,
    sg_redis_client,
    sg_rds_client,
    sg_clickhouse_client,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    sg_fargate_service = aws_ec2.SecurityGroup(self, 'ECSFargateServiceSG',
      vpc=vpc,
      allow_all_outbound=True,
      description="Allow inbound from VPC for ECS Fargate Service",
      security_group_name=f'{self.stack_name.lower()}-langfuse-worker-sg'
    )
    sg_fargate_service.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.all_tcp(),
      description='langfuse-worker')
    cdk.Tags.of(sg_fargate_service).add('Name', 'langfuse-worker-sg')

    worker_desired_count = self.node.try_get_context('langfuse_worker_desired_count') or 1
    self.fargate_service = aws_ecs.FargateService(self, "FargateService",
      service_name="langfuse_worker",
      cluster=ecs_cluster,
      task_definition=ecs_task_definition,
      desired_count=int(worker_desired_count),
      min_healthy_percent=50,
      security_groups=[sg_fargate_service, sg_redis_client, sg_rds_client, sg_clickhouse_client],
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS),
    )
    cdk.Tags.of(self.fargate_service).add('Name', 'langfuse_worker')


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
