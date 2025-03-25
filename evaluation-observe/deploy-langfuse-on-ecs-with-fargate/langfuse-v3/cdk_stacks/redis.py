#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_elasticache
)
from constructs import Construct


class RedisClusterStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    self.sg_elasticache_client = aws_ec2.SecurityGroup(self, 'RedisClientSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for redis client',
      security_group_name=f'{self.stack_name}-redis-client-sg'
    )
    cdk.Tags.of(self.sg_elasticache_client).add('Name', 'redis-client-sg')

    sg_elasticache_server = aws_ec2.SecurityGroup(self, 'RedisServerSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for redis server',
      security_group_name=f'{self.stack_name}-redis-server-sg'
    )
    cdk.Tags.of(sg_elasticache_server).add('Name', 'redis-server-sg')

    sg_elasticache_server.add_ingress_rule(peer=self.sg_elasticache_client,
      connection=aws_ec2.Port.tcp(6379),
      description='redis-client-sg')
    sg_elasticache_server.add_ingress_rule(peer=sg_elasticache_server,
      connection=aws_ec2.Port.all_tcp(),
      description='redis-server-sg')

    redis_cluster_subnet_group = aws_elasticache.CfnSubnetGroup(self, 'RedisSubnetGroup',
      description='subnet group for redis',
      subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids,
      cache_subnet_group_name=f'{self.stack_name}-redis-cluster'
    )

    self.redis_cluster = aws_elasticache.CfnReplicationGroup(self, 'RedisCluster',
      replication_group_id='langfuse-cache',
      replication_group_description='Langfuse Cache/Queue Replication Group',

      #XXX: Amazon ElastiCache Supported node types
      # https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheNodes.SupportedTypes.html#CacheNodes.CurrentGen
      cache_node_type='cache.t3.small',
      engine='valkey',

      #XXX: Comparing Valkey, Memcached, and Redis OSS self-designed caches
      # https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SelectEngine.html
      #XXX: Amazon ElastiCache Supported engines and versions
      # https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/supported-engine-versions.html
      engine_version='7.2',

      num_cache_clusters=1,
      automatic_failover_enabled=False,
      cache_parameter_group_name="default.valkey7",
      cache_subnet_group_name=redis_cluster_subnet_group.cache_subnet_group_name,
      security_group_ids=[sg_elasticache_server.security_group_id],
      snapshot_retention_limit=3,
      snapshot_window='19:00-21:00',
      preferred_maintenance_window='mon:21:00-mon:22:30',
      auto_minor_version_upgrade=False,
      transit_encryption_enabled=True,
      transit_encryption_mode='preferred',
      tags=[
        cdk.CfnTag(key='Name', value='langfuse-cache')
      ]
    )
    self.redis_cluster.add_dependency(redis_cluster_subnet_group)
    self.redis_cluster.apply_removal_policy(cdk.RemovalPolicy.DESTROY)


    cdk.CfnOutput(self, 'PrimaryEndpoint',
      value=self.redis_cluster.attr_primary_end_point_address,
      export_name=f'{self.stack_name}-PrimaryEndpoint')
    cdk.CfnOutput(self, 'PrimaryPort',
      value=self.redis_cluster.attr_primary_end_point_port,
      export_name=f'{self.stack_name}-PrimaryPort')
