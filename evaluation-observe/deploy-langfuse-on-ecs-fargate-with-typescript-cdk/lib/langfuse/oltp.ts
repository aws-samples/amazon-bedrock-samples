// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as logs from "aws-cdk-lib/aws-logs";
import * as rds from "aws-cdk-lib/aws-rds";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

const POSTGRES_PORT = 5432;

export interface IOLTPDatabaseProps {
  /**
   * VPC in which to place the database
   */
  vpc: ec2.IVpc;
  /**
   * Instance type to use for the database
   *
   * @default "r6g.large"
   */
  instanceType?: ec2.InstanceType;
  /**
   * Optional AWS Tags to apply to created resources
   */
  tags?: cdk.Tag[];
}

/**
 * Construct for an (RDS Aurora for Postgres-based) OLTP database for Langfuse
 */
export class OLTPDatabase extends Construct {
  /**
   * Security group granting connection to the created database
   */
  public readonly clientSecurityGroup: ec2.SecurityGroup;
  public readonly dbCluster: rds.DatabaseCluster;
  /**
   * Security group of the database cluster itself (consumers want `clientSecurityGroup` instead)
   */
  public readonly dbClusterSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: IOLTPDatabaseProps) {
    super(scope, id);

    const instanceType =
      props.instanceType || new ec2.InstanceType("r6g.large");

    this.clientSecurityGroup = new ec2.SecurityGroup(this, "DBClientSG", {
      vpc: props.vpc,
      allowAllOutbound: false,
      description: "Langfuse OLTP database clients",
    });
    cdk.Tags.of(this.clientSecurityGroup).add(
      "Name",
      "langfuse-oltpdb-client-sg",
    );
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(this.clientSecurityGroup).add(tag.key, tag.value);
      });
    }

    this.dbClusterSecurityGroup = new ec2.SecurityGroup(this, "DBClusterSG", {
      vpc: props.vpc,
      description: "Langfuse OLTP database nodes",
    });
    cdk.Tags.of(this.dbClusterSecurityGroup).add(
      "Name",
      "langfuse-oltpdb-cluster-sg",
    );
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(this.dbClusterSecurityGroup).add(tag.key, tag.value);
      });
    }

    this.clientSecurityGroup.addEgressRule(
      this.dbClusterSecurityGroup,
      ec2.Port.tcp(POSTGRES_PORT),
      "Connect to OLTP DB",
    );
    this.dbClusterSecurityGroup.addIngressRule(
      this.clientSecurityGroup,
      ec2.Port.tcp(POSTGRES_PORT),
      "Connections from clients",
    );
    this.dbClusterSecurityGroup.addIngressRule(
      this.dbClusterSecurityGroup,
      ec2.Port.allTcp(),
      "Within-cluster comms",
    );

    const rdsSubnetGroup = new rds.SubnetGroup(this, "RDSSubnetGroup", {
      description: "Langfuse OLTP DB subnets",
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });

    const dbSecret = new rds.DatabaseSecret(this, "DBSecret", {
      username: "postgres",
      dbname: "postgres",
      excludeCharacters: " %+~`#$&*()|[]{}.,:;-<>?!'/@\"\\", // (Also exclude . and ,)
    });
    NagSuppressions.addResourceSuppressions(dbSecret, [
      {
        id: "AwsSolutions-SMG4",
        // To support this, we'd need to automatically force restart of the Langfuse web & worker
        // containers when rotation happens.
        // See: https://repost.aws/questions/QUYHw--TXvTTewJeVsT2T5QA/
        reason: "Secret rotation not implemented",
      },
    ]);

    const rdsCredentials = rds.Credentials.fromSecret(dbSecret);

    const rdsEngine = rds.DatabaseClusterEngine.auroraPostgres({
      version: rds.AuroraPostgresEngineVersion.VER_15_4,
    });

    const clusterParamGroup = new rds.ParameterGroup(
      this,
      "ClusterParamGroup",
      {
        engine: rdsEngine,
        description: "Cluster parameters for Langfuse OLTP database",
        parameters: {
          log_min_duration_statement: "15000",
          default_transaction_isolation: "read committed",
          client_encoding: "UTF8",
        },
      },
    );

    const instanceParamGroup = new rds.ParameterGroup(
      this,
      "InstanceParamGroup",
      {
        engine: rdsEngine,
        description: "Instance parameters for Langfuse OLTP database",
        parameters: {
          log_min_duration_statement: "15000",
          default_transaction_isolation: "read committed",
        },
      },
    );

    this.dbCluster = new rds.DatabaseCluster(this, "Cluster", {
      engine: rdsEngine,
      credentials: rdsCredentials,
      writer: rds.ClusterInstance.provisioned("writer", {
        instanceType,
        parameterGroup: instanceParamGroup,
        autoMinorVersionUpgrade: false,
      }),
      readers: [
        rds.ClusterInstance.provisioned("reader", {
          instanceType,
          parameterGroup: instanceParamGroup,
          autoMinorVersionUpgrade: false,
        }),
      ],
      parameterGroup: clusterParamGroup,
      cloudwatchLogsRetention: logs.RetentionDays.FIVE_DAYS,
      // clusterIdentifier: dbClusterName,
      subnetGroup: rdsSubnetGroup,
      backup: {
        retention: cdk.Duration.days(3),
        preferredWindow: "03:00-04:00",
      },
      securityGroups: [this.dbClusterSecurityGroup],
      storageEncrypted: true,
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.dbCluster).add(tag.key, tag.value),
      );
    }
    NagSuppressions.addResourceSuppressions(this.dbCluster, [
      {
        id: "AwsSolutions-RDS6",
        reason: "Langfuse can't use IAM auth for RDS (we think)",
      },
      {
        id: "AwsSolutions-RDS10",
        reason: "OK to delete traces for demo environment",
      },
    ]);
  }

  /**
   * AWS Secrets Manager Secret containing access credentials to the database
   */
  public get secret() {
    return this.dbCluster.secret!;
  }
}
