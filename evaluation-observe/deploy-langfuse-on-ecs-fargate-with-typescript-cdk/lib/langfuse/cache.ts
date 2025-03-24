// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as elasticache from "aws-cdk-lib/aws-elasticache";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface ICacheClusterProps {
  /**
   * AWS VPC in which to deploy the cache
   */
  vpc: ec2.IVpc;
  /**
   * The compute and memory capacity of the nodes in the node group (shard).
   *
   * @see — http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticache-replicationgroup.html#cfn-elasticache-replicationgroup-cachenodetype
   *
   * @default "cache.t3.small"
   */
  cacheNodeType?: string;
  /**
   * The number of clusters this replication group initially has.
   *
   * Must be in range 1-6. If >=1, multi-AZ mode will be used automatically.
   *
   * @see — http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticache-replicationgroup.html#cfn-elasticache-replicationgroup-numcacheclusters
   *
   * @default 2
   */
  numCacheClusters?: number;
  /**
   * Port on which the cache cluster should listen for clients
   *
   * @default 6379
   */
  port?: number;
  /**
   * AWS Tags to apply to created resources (cluster, security groups, etc)
   */
  tags?: cdk.Tag[];
}

/**
 * (Redis / Valkey) cache cluster for use with Langfuse
 */
export class CacheCluster extends Construct {
  public readonly authSecret: secretsmanager.Secret;
  public readonly clientSecurityGroup: ec2.SecurityGroup;
  public readonly cluster: elasticache.CfnReplicationGroup;
  /**
   * The port number that the primary read-write cache engine is listening on.
   */
  public readonly primaryPort: number;

  constructor(scope: Construct, id: string, props: ICacheClusterProps) {
    super(scope, id);
    const stack = cdk.Stack.of(this);
    const cacheNodeType = props.cacheNodeType || "cache.t3.small";
    const numCacheClusters = props.numCacheClusters || 2;
    this.primaryPort = props.port || 6379;

    this.authSecret = new secretsmanager.Secret(this, "AuthSecret", {
      description:
        "Redis/Valkey AUTH secret (Used to authenticate cache access)",
      generateSecretString: {
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 50,
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.authSecret).add(tag.key, tag.value),
      );
    }
    NagSuppressions.addResourceSuppressions(
      this.authSecret,
      [
        {
          id: "AwsSolutions-SMG4",
          // To support this, we'd need to automatically force restart of the Langfuse web & worker
          // containers when rotation happens.
          // See: https://repost.aws/questions/QUYHw--TXvTTewJeVsT2T5QA/
          reason: "Redis secret auto-rotation not yet implemented",
        },
      ],
      true,
    );

    this.clientSecurityGroup = new ec2.SecurityGroup(this, "ClientSG", {
      vpc: props.vpc,
      allowAllOutbound: false,
      description:
        "Security group for clients connecting to Langfuse cache cluster",
    });
    cdk.Tags.of(this.clientSecurityGroup).add(
      "Name",
      "langfuse-cache-client-sg",
    );
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(this.clientSecurityGroup).add(tag.key, tag.value);
      });
    }

    const serverSecurityGroup = new ec2.SecurityGroup(this, "ServerSG", {
      vpc: props.vpc,

      description: "Security group for Langfuse cache cluster nodes",
      securityGroupName: `${stack.stackName}-cache-server-sg`,
    });
    cdk.Tags.of(serverSecurityGroup).add("Name", "langfuse-cache-server-sg");
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(serverSecurityGroup).add(tag.key, tag.value);
      });
    }
    this.clientSecurityGroup.addEgressRule(
      serverSecurityGroup,
      ec2.Port.tcp(this.primaryPort),
      "To Langfuse cache cluster",
    );
    serverSecurityGroup.addIngressRule(
      this.clientSecurityGroup,
      ec2.Port.tcp(this.primaryPort),
      "From Langfuse cache clients",
    );
    serverSecurityGroup.addIngressRule(
      serverSecurityGroup,
      ec2.Port.allTcp(),
      "Within-cluster Langfuse cache comms",
    );

    const clusterSubnetGroup = new elasticache.CfnSubnetGroup(
      this,
      "SubnetGroup",
      {
        description: "Langfuse cache cluster subnet group",
        subnetIds: props.vpc.selectSubnets({
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }).subnetIds,
      },
    );

    const paramGroup = new elasticache.CfnParameterGroup(this, "ParamGroup", {
      description: "Langfuse cache parameter group",
      cacheParameterGroupFamily: "valkey7",
      properties: {
        "maxmemory-policy": "noeviction",
      },
      tags: props.tags,
    });

    this.cluster = new elasticache.CfnReplicationGroup(this, "Cluster", {
      authToken: new cdk.CfnDynamicReference(
        cdk.CfnDynamicReferenceService.SECRETS_MANAGER,
        `${this.authSecret.secretArn}:SecretString:::`,
      ) as unknown as string,
      replicationGroupDescription: "Langfuse Cache/Queue Replication Group",
      cacheNodeType,
      // Comparing Valkey, Memcached, and Redis OSS self-designed caches:
      // https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SelectEngine.html
      engine: "valkey",
      // Amazon ElastiCache Supported engines and versions:
      // https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/supported-engine-versions.html
      engineVersion: "7.2",
      numCacheClusters,
      port: this.primaryPort,
      atRestEncryptionEnabled: true,
      // automaticFailoverEnabled: false, // Can't enable this in multi-AZ mode
      cacheParameterGroupName: paramGroup.attrCacheParameterGroupName,
      cacheSubnetGroupName: clusterSubnetGroup.ref,
      multiAzEnabled: numCacheClusters > 1,
      securityGroupIds: [serverSecurityGroup.securityGroupId],
      snapshotRetentionLimit: 3,
      snapshotWindow: "19:00-21:00",
      preferredMaintenanceWindow: "mon:21:00-mon:22:30",
      autoMinorVersionUpgrade: true,
      transitEncryptionEnabled: true,
      transitEncryptionMode: "required",
      tags: [
        { key: "Name", value: "langfuse-cache-cluster" },
        ...(props.tags ? props.tags : []),
      ],
    });
    this.cluster.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
  }

  /**
   * The DNS address of the primary read-write cache node
   */
  public get primaryEndpoint() {
    return this.cluster.attrPrimaryEndPointAddress;
  }

  /**
   * A string with a list of endpoints for the read-only replicas. The order of the addresses maps
   * to the order of the ports from the ReadEndPoint.Ports attribute.
   */
  public get readOnlyEndpoints() {
    return this.cluster.attrReadEndPointAddressesList;
  }

  /**
   * A string with a list of ports for the read-only replicas. The order of the ports maps to the
   * order of the addresses from the ReadEndPoint.Addresses attribute.
   */
  public get readOnlyPorts() {
    return this.cluster.attrReadEndPointPortsList;
  }
}
