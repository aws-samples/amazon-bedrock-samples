#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_servicediscovery
)

from constructs import Construct


class ServiceDiscoveryStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    private_dns_namespace_name = self.node.try_get_context('private_dns_namespace_name') or "langfuse.local"
    self.namespace = aws_servicediscovery.PrivateDnsNamespace(self, "PrivateDnsNamespace",
      name=private_dns_namespace_name,
      description="Langfuse Service Discovery namespace",
      vpc=vpc
    )
    cdk.Tags.of(self.namespace).add('Name', 'langfuse')

    self.service = self.namespace.create_service("Service",
      name="clickhouse",
      dns_record_type=aws_servicediscovery.DnsRecordType.A,
      dns_ttl=cdk.Duration.seconds(10),
      # load_balancer=False, # default: False
      custom_health_check=aws_servicediscovery.HealthCheckCustomConfig(
        failure_threshold=1
      )
    )
    cdk.Tags.of(self.service).add('Name', 'langfuse_clickhouse')


    cdk.CfnOutput(self, 'NamespaceName',
      value=self.namespace.namespace_name,
      export_name=f'{self.stack_name}-NamespaceName')
    cdk.CfnOutput(self, 'ServiceName',
      value=self.service.service_name,
      export_name=f'{self.stack_name}-ServiceName')

