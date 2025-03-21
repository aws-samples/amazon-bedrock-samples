#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ecs as ecs,
)

from constructs import Construct


class ECSClusterStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    cluster_name = self.node.try_get_context('ecs_cluster_name') or "langfuse-cluster"
    cluster = ecs.Cluster(self, "ECSCluster",
      cluster_name=cluster_name,
      vpc=vpc
    )

    self.ecs_cluster = cluster

    cdk.CfnOutput(self, 'ClusterName',
      value=self.ecs_cluster.cluster_name,
      export_name=f'{self.stack_name}-ClusterName')
    cdk.CfnOutput(self, 'ClusterArn',
      value=self.ecs_cluster.cluster_arn,
      export_name=f'{self.stack_name}-ClusterArn')
