#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_ecs,
  aws_elasticloadbalancingv2 as elbv2
)

from constructs import Construct


class ECSFargateServiceLangfuseWebStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    vpc,
    ecs_cluster,
    ecs_task_definition,
    sg_redis_client,
    sg_rds_client,
    sg_clickhouse_client,
    alb_listener,
    **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    sg_fargate_service = aws_ec2.SecurityGroup(self, 'ECSFargateServiceSG',
      vpc=vpc,
      allow_all_outbound=True,
      description="Allow inbound from VPC for ECS Fargate Service",
      security_group_name=f'{self.stack_name.lower()}-langfuse-web-sg'
    )
    sg_fargate_service.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(3000),
      description='langfuse-web')
    cdk.Tags.of(sg_fargate_service).add('Name', 'langfuse-web-sg')

    self.fargate_service = aws_ecs.FargateService(self, "FargateService",
      service_name="langfuse_web",
      cluster=ecs_cluster,
      task_definition=ecs_task_definition,
      desired_count=1,
      min_healthy_percent=50,
      security_groups=[sg_fargate_service, sg_redis_client, sg_rds_client, sg_clickhouse_client],
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS),
    )
    cdk.Tags.of(self.fargate_service).add('Name', 'langfuse_web')

    alb_target_group = alb_listener.add_targets("ECS",
      port=3000,
      protocol=elbv2.ApplicationProtocol.HTTP
    )
    alb_target_group.add_target(self.fargate_service)

    # Setup autoscaling policy
    scalable_target = self.fargate_service.auto_scale_task_count(max_capacity=2)
    scalable_target.scale_on_cpu_utilization(
      id="Autoscaling",
      target_utilization_percent=70,
      scale_in_cooldown=cdk.Duration.seconds(60),
      scale_out_cooldown=cdk.Duration.seconds(60),
    )


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
    cdk.CfnOutput(self, "LoadBalancerDNS",
      value=f'http://{alb_listener.load_balancer.load_balancer_dns_name}',
      export_name=f'{self.stack_name}-LoadBalancerDNS')
