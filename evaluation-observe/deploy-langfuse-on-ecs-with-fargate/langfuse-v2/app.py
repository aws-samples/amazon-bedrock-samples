#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  ApplicationLoadBalancerStack,
  AuroraPostgresqlStack,
  ECRStack,
  ECSAlbFargateServiceStack,
  ECSClusterStack,
  ECSTaskStack,
  VpcStack
)

AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

ecr_stack = ECRStack(app, "LangFuseECRStack",
  env=AWS_ENV
)

vpc_stack = VpcStack(app, "LangFuseVpcStack",
  env=AWS_ENV
)
vpc_stack.add_dependency(ecr_stack)

alb_stack = ApplicationLoadBalancerStack(app, "LangFuseALBStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
alb_stack.add_dependency(vpc_stack)

rds_stack = AuroraPostgresqlStack(app, "LangFuseAuroraPostgreSQLStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
rds_stack.add_dependency(alb_stack)

ecs_cluster_stack = ECSClusterStack(app, "LangFuseECSClusterStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
ecs_cluster_stack.add_dependency(rds_stack)

ecs_task_stack = ECSTaskStack(app, "LangFuseECSTaskStack",
  ecr_stack.repository,
  rds_stack.database_secret,
  alb_stack.load_balancer_url,
  env=AWS_ENV
)
ecs_task_stack.add_dependency(ecs_cluster_stack)

ecs_fargate_stack = ECSAlbFargateServiceStack(app, "LangFuseECSAlbFargateServiceStack",
  vpc_stack.vpc,
  ecs_cluster_stack.ecs_cluster,
  ecs_task_stack.ecs_task_definition,
  alb_stack.load_balancer,
  rds_stack.sg_rds_client,
  env=AWS_ENV
)
ecs_fargate_stack.add_dependency(ecs_task_stack)

app.synth()
