#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_elasticloadbalancingv2 as elbv2
)

from constructs import Construct


class ApplicationLoadBalancerStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    service_name = self.node.try_get_context('ecs_service_name') or "langfuse-alb-service"

    sg_alb = aws_ec2.SecurityGroup(self, 'LoadBalancerSG',
      vpc=vpc,
      allow_all_outbound=True,
      description="Allow inbound from VPC for ECS Fargate Service",
      security_group_name=f'{service_name}-alb-sg'
    )
    sg_alb.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(80))
    sg_alb.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(443))
    cdk.Tags.of(sg_alb).add('Name', 'ecs-service-alb-sg')

    self.load_balancer = elbv2.ApplicationLoadBalancer(self, "LoadBalancer",
      vpc=vpc,
      internet_facing=True,
      security_group=sg_alb
    )
    self.load_balancer.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

    self.load_balancer_url = f'http://{self.load_balancer.load_balancer_dns_name}'


    cdk.CfnOutput(self, "LoadBalancerDNS",
      value=self.load_balancer_url,
      export_name=f'{self.stack_name}-LoadBalancerDNS')
