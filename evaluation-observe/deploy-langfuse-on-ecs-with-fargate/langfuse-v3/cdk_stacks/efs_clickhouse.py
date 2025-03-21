#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_efs,
  aws_iam,
)
from constructs import Construct


class EFSStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    self.sg_efs_inbound = aws_ec2.SecurityGroup(self, "EFSInboundSecurityGroup",
      vpc=vpc,
      allow_all_outbound=True,
      description='Security Group that allows inbound NFS traffic for ECS tasks',
      security_group_name=f'{self.stack_name.lower()}-efs-inbound-sg'
    )
    self.sg_efs_inbound.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
    cdk.Tags.of(self.sg_efs_inbound).add('Name', 'efs-inbound-sg')

    self.sg_efs_outbound = aws_ec2.SecurityGroup(self, "EFSOutboundGroup",
      vpc=vpc,
      allow_all_outbound=False,
      description='Security Group that allows outbound NFS traffic for ECS tasks',
      security_group_name=f'{self.stack_name.lower()}-efs-outbound-sg'
    )
    self.sg_efs_outbound.add_ingress_rule(peer=self.sg_efs_inbound,
      connection=aws_ec2.Port.tcp(2049))
    self.sg_efs_outbound.add_egress_rule(peer=self.sg_efs_inbound,
      connection=aws_ec2.Port.tcp(2049))
    self.sg_efs_outbound.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
    cdk.Tags.of(self.sg_efs_outbound).add('Name', 'efs-outbound-sg')

    self.efs_file_system = aws_efs.FileSystem(self, "EfsFileSystem",
      vpc=vpc,
      performance_mode=aws_efs.PerformanceMode.GENERAL_PURPOSE, # default
      removal_policy=cdk.RemovalPolicy.DESTROY, # default: RemovalPolicy.RETAIN
      security_group=self.sg_efs_outbound,
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS)
    )

    self.efs_file_system.add_to_resource_policy(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "actions": [
        "elasticfilesystem:ClientMount",
      ],
      "principals": [
        aws_iam.AnyPrincipal()
      ],
      "conditions": {
        "Bool": {
          "elasticfilesystem:AccessedViaMountTarget": "true"
        }
      }
    }))

    cdk.Tags.of(self.efs_file_system).add('Name', 'clickhouse-data')


    cdk.CfnOutput(self, 'EFSInboundSecurityGroupId',
      value=self.sg_efs_inbound.security_group_id,
      export_name=f'{self.stack_name}-EFSInboundSecurityGroupId')
    cdk.CfnOutput(self, 'EFSOutboundSecurityGroupId',
      value=self.sg_efs_outbound.security_group_id,
      export_name=f'{self.stack_name}-EFSOutboundSecurityGroupId')
    cdk.CfnOutput(self, 'EFSFileSystemId',
      value=self.efs_file_system.file_system_id,
      export_name=f'{self.stack_name}-EFSFileSystemId')
    cdk.CfnOutput(self, 'EFSFileSystemArn',
      value=self.efs_file_system.file_system_arn,
      export_name=f'{self.stack_name}-EFSFileSystemArn')
