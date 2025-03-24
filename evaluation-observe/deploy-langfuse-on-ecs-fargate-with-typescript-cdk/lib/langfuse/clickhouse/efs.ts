// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as efs from "aws-cdk-lib/aws-efs";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export interface IEFSWithSecurityGroupsProps {
  /**
   * The VPC into which the EFS FileSystem should be deployed
   */
  vpc: ec2.IVpc;
  /**
   * Optional AWS Tags to apply to the created FileSystem and Security Groups
   */
  tags?: cdk.Tag[];
}

/**
 * An EFS FileSystem with associated Security Groups to grant network access
 */
export class EFSWithSecurityGroups extends Construct {
  /**
   * Security group for clients wanting to mount the FileSystem
   */
  public readonly clientSecurityGroup: ec2.SecurityGroup;
  /**
   * Security group attached to the FileSystem itself (clients should not need to use this)
   */
  public readonly nodeSecurityGroup: ec2.SecurityGroup;
  /**
   * The created FileSystem
   */
  public readonly fileSystem: efs.FileSystem;

  constructor(
    scope: Construct,
    id: string,
    props: IEFSWithSecurityGroupsProps,
  ) {
    super(scope, id);

    const EFS_PORTS = [
      ec2.Port.tcp(2049), // NFS: https://docs.aws.amazon.com/efs/latest/ug/source-ports.html
    ];

    this.clientSecurityGroup = new ec2.SecurityGroup(this, "EFSClientSG", {
      vpc: props.vpc,
      allowAllOutbound: false,
      description: "Clients for ClickHouse NFS",
    });
    this.clientSecurityGroup.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
    cdk.Tags.of(this.clientSecurityGroup).add("Name", "clickhouse-efs-clients");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.clientSecurityGroup).add(tag.key, tag.value),
      );
    }

    this.nodeSecurityGroup = new ec2.SecurityGroup(this, "EFSNodeSG", {
      vpc: props.vpc,
      allowAllOutbound: false,
      description: "ClickHouse NFS nodes",
    });
    this.nodeSecurityGroup.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
    cdk.Tags.of(this.nodeSecurityGroup).add("Name", "clickhouse-efs-nodes");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.nodeSecurityGroup).add(tag.key, tag.value),
      );
    }

    EFS_PORTS.forEach((port) => {
      this.clientSecurityGroup.addEgressRule(this.nodeSecurityGroup, port);
      this.nodeSecurityGroup.addIngressRule(this.clientSecurityGroup, port);
    });

    this.fileSystem = new efs.FileSystem(this, "FileSystem", {
      vpc: props.vpc,
      performanceMode: efs.PerformanceMode.GENERAL_PURPOSE,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      securityGroup: this.nodeSecurityGroup,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });
    cdk.Tags.of(this.fileSystem).add("Name", "clickhouse-data");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.fileSystem).add(tag.key, tag.value),
      );
    }

    this.fileSystem.addToResourcePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["elasticfilesystem:ClientMount"],
        principals: [new iam.AnyPrincipal()],
        conditions: {
          Bool: {
            "elasticfilesystem:AccessedViaMountTarget": "true",
          },
        },
      }),
    );
  }
}
