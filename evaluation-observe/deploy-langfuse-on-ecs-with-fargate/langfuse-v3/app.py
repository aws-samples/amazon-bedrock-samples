#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from cdk_stacks import (
  ALBLangfuseWebStack,
  AuroraPostgresqlStack,
  ECRStack,
  ECSClusterStack,
  ECSTaskClickhouseStack,
  ECSFargateServiceClickhouseStack,
  EFSStack,
  ECSTaskLangfuseWebStack,
  ECSTaskLangfuseWorkerStack,
  ECSFargateServiceLangfuseWebStack,
  ECSFargateServiceLangfuseWorkerStack,
  RedisClusterStack,
  S3BucketStack,
  ServiceDiscoveryStack,
  VpcStack
)

AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"]
)

app = cdk.App()

ecr_stack = ECRStack(app, "LangfuseECRStack",
  env=AWS_ENV
)

vpc_stack = VpcStack(app, "LangfuseVpcStack",
  env=AWS_ENV
)
vpc_stack.add_dependency(ecr_stack)

langfuse_web_alb_stack = ALBLangfuseWebStack(app, "LangfuseWebALBStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
langfuse_web_alb_stack.add_dependency(vpc_stack)

redis_stack = RedisClusterStack(app, "LangfuseCacheStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
redis_stack.add_dependency(langfuse_web_alb_stack)

rds_stack = AuroraPostgresqlStack(app, "LangfuseAuroraPostgreSQLStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
rds_stack.add_dependency(redis_stack)

s3_buckets = S3BucketStack(app, "LangfuseS3BucketStack",
  env=AWS_ENV
)
s3_buckets.add_dependency(rds_stack)

service_discovery_stack = ServiceDiscoveryStack(app, "LangfuseServiceDiscoveryStack",
  vpc_stack.vpc,
  env=AWS_ENV)
service_discovery_stack.add_dependency(s3_buckets)

ecs_cluster_stack = ECSClusterStack(app, "LangfuseECSClusterStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
ecs_cluster_stack.add_dependency(service_discovery_stack)

clickhouse_efs_stack = EFSStack(app, "LangfuseClickhouseEFSStack",
  vpc_stack.vpc,
  env=AWS_ENV
)
clickhouse_efs_stack.add_dependency(ecs_cluster_stack)

clickhouse_stack = ECSTaskClickhouseStack(app, "LangfuseClickhouseECSTaskStack",
  ecr_stack.repositories,
  clickhouse_efs_stack.efs_file_system,
  env=AWS_ENV
)
clickhouse_stack.add_dependency(clickhouse_efs_stack)

clickhouse_service_stack = ECSFargateServiceClickhouseStack(app, "LangfuseClickhouseECSServiceStack",
  vpc_stack.vpc,
  ecs_cluster_stack.ecs_cluster,
  clickhouse_stack.ecs_task_definition,
  clickhouse_efs_stack.sg_efs_inbound,
  service_discovery_stack.service,
  env=AWS_ENV
)
clickhouse_service_stack.add_dependency(clickhouse_stack)

langfuse_worker_stack = ECSTaskLangfuseWorkerStack(app, "LangfuseWorkerECSTaskStack",
  ecr_repositories=ecr_stack.repositories,
  database_secret=rds_stack.database_secret,
  clickhouse_secret=clickhouse_stack.clickhouse_secret,
  clickhouse_migration_url=clickhouse_service_stack.clickhouse_migration_url,
  clickhouse_url=clickhouse_service_stack.clickhouse_url,
  redis_cluster=redis_stack.redis_cluster,
  s3_blob_bucket=s3_buckets.blob_bucket,
  s3_event_bucket=s3_buckets.event_bucket,
  env=AWS_ENV
)
langfuse_worker_stack.add_dependency(clickhouse_service_stack)

langfuse_worker_service_stack = ECSFargateServiceLangfuseWorkerStack(app, "LangfuseWorkerECSServiceStack",
  vpc=vpc_stack.vpc,
  ecs_cluster=ecs_cluster_stack.ecs_cluster,
  ecs_task_definition=langfuse_worker_stack.ecs_task_definition,
  sg_redis_client=redis_stack.sg_elasticache_client,
  sg_rds_client=rds_stack.sg_rds_client,
  sg_clickhouse_client=clickhouse_service_stack.sg_clickhouse_client,
  env=AWS_ENV
)
langfuse_worker_service_stack.add_dependency(langfuse_worker_stack)

langfuse_web_stack = ECSTaskLangfuseWebStack(app, "LangfuseWebECSTaskStack",
  ecr_repositories=ecr_stack.repositories,
  database_secret=rds_stack.database_secret,
  clickhouse_secret=clickhouse_stack.clickhouse_secret,
  clickhouse_migration_url=clickhouse_service_stack.clickhouse_migration_url,
  clickhouse_url=clickhouse_service_stack.clickhouse_url,
  redis_cluster=redis_stack.redis_cluster,
  s3_blob_bucket=s3_buckets.blob_bucket,
  s3_event_bucket=s3_buckets.event_bucket,
  load_balancer_url=langfuse_web_alb_stack.load_balancer_url,
  env=AWS_ENV
)
langfuse_web_stack.add_dependency(langfuse_worker_service_stack)

langfuse_web_service_stack = ECSFargateServiceLangfuseWebStack(app, "LangfuseWebECSServiceStack",
  vpc=vpc_stack.vpc,
  ecs_cluster=ecs_cluster_stack.ecs_cluster,
  ecs_task_definition=langfuse_web_stack.ecs_task_definition,
  sg_redis_client=redis_stack.sg_elasticache_client,
  sg_rds_client=rds_stack.sg_rds_client,
  sg_clickhouse_client=clickhouse_service_stack.sg_clickhouse_client,
  alb_listener=langfuse_web_alb_stack.alb_listener,
  env=AWS_ENV
)
langfuse_web_service_stack.add_dependency(langfuse_web_stack)

app.synth()
