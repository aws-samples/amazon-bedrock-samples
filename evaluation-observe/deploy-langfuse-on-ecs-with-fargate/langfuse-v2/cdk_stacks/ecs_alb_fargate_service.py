#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_ecs_patterns,
)

from constructs import Construct


class ECSAlbFargateServiceStack(Stack):

  def __init__(self, scope: Construct, construct_id: str,
    vpc, ecs_cluster, ecs_task_definition,
    load_balancer, sg_rds_client, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    service_name = self.node.try_get_context('ecs_service_name') or "langfuse-alb-service"

    sg_fargate_service = aws_ec2.SecurityGroup(self, 'ECSFargateServiceSG',
      vpc=vpc,
      allow_all_outbound=True,
      description="Allow inbound from VPC for ECS Fargate Service",
      security_group_name=f'{service_name}-ecs-service-sg'
    )
    sg_fargate_service.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(3000),
      description='langfuse-server')
    cdk.Tags.of(sg_fargate_service).add('Name', 'ecs-service-alb-sg')

    fargate_service = aws_ecs_patterns.ApplicationLoadBalancedFargateService(self, "ALBFargateService",
      service_name=service_name,
      cluster=ecs_cluster,
      task_definition=ecs_task_definition,
      load_balancer=load_balancer,
      security_groups=[sg_fargate_service, sg_rds_client]
    )

    # Setup autoscaling policy
    scalable_target = fargate_service.service.auto_scale_task_count(max_capacity=2)
    scalable_target.scale_on_cpu_utilization(
      id="Autoscaling",
      target_utilization_percent=70,
      scale_in_cooldown=cdk.Duration.seconds(60),
      scale_out_cooldown=cdk.Duration.seconds(60),
    )

    cdk.CfnOutput(self, "LoadBalancerDNS",
      value=f'http://{fargate_service.load_balancer.load_balancer_dns_name}',
      export_name=f'{self.stack_name}-LoadBalancerDNS')