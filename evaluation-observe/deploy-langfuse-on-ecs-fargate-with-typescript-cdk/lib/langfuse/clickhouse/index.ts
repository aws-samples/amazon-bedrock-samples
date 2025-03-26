// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// NodeJS Built-Ins:
import * as path from "path";

// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecrassets from "aws-cdk-lib/aws-ecr-assets";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as servicediscovery from "aws-cdk-lib/aws-servicediscovery";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

// Local Dependencies:
import { ECRRepoAndDockerImage } from "../ecr";
import { EFSWithSecurityGroups } from "./efs";

export interface IClickHouseDeploymentProps {
  /**
   * ECS Cluster within which to deploy
   */
  cluster: ecs.ICluster;
  /**
   * AWS VPC in which to deploy ClickHouse
   */
  vpc: ec2.IVpc;
  /**
   * Cloud Map service to provide private DNS visibility between components
   *
   * If this is not set, you won't be able to access URL properties of the construct.
   *
   * @default None
   */
  cloudMapService?: servicediscovery.IService;
  /**
   * ECS Fargate CPU allocation for the ClickHouse container.
   *
   * https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 1024
   */
  cpu?: number;
  /**
   * Extra environment variables to configure on the service's containers
   */
  environment?: { [key: string]: string };
  /**
   * ECS Fargate CPU allocation for the ClickHouse container.
   *
   * https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 8192
   */
  memoryLimitMiB?: number;
  /**
   * Name of the ECS FargateService to create
   *
   * @default "clickhouse"
   */
  serviceName?: string;
  /**
   * AWS Tags to apply to created resources (ECS tasks, ECR images, Secrets, etc)
   */
  tags?: cdk.Tag[];
  /**
   * Released version of ClickHouse to deploy
   *
   * @default "25.1"
   */
  version?: string;
}

// Refer to: https://clickhouse.com/docs/en/guides/sre/network-ports
interface IPortSpec {
  port: number;
  description: string;
  internal: boolean;
  protocol: ecs.Protocol;
}
const CLICKHOUSE_PORT_HTTP: IPortSpec = {
  port: 8123,
  description: "ClickHouse HTTP interface",
  internal: false,
  protocol: ecs.Protocol.TCP,
};
const CLICKHOUSE_PORT_NATIVE: IPortSpec = {
  port: 9000,
  description: "ClickHouse native interface",
  internal: false,
  protocol: ecs.Protocol.TCP,
};
const CLICKHOUSE_PORTS = [
  CLICKHOUSE_PORT_HTTP,
  {
    port: 2181,
    description: "Zookeeper default port",
    internal: true,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 8443,
    description: "ClickHouse HTTPS interface",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  CLICKHOUSE_PORT_NATIVE,
  {
    port: 9004,
    description: "ClickHouse MySQL emulation",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9005,
    description: "ClickHouse Postgres emulation",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9009,
    description: "ClickHouse interserver interface",
    internal: true,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9010,
    description: "ClickHouse interserver SSL interface",
    internal: true,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9011,
    description: "ClickHouse native proxy v1",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9019,
    description: "ClickHouse JDBC bridge",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9100,
    description: "ClickHouse gRPC interface",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9181,
    description: "ClickHouse keeper",
    internal: true,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9234,
    description: "ClickHouse keeper raft",
    internal: true,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9363,
    description: "ClickHouse Prometheus metrics",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9281,
    description: "ClickHouse keeper SSL",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 9440,
    description: "ClickHouse native SSL",
    internal: false,
    protocol: ecs.Protocol.TCP,
  },
  {
    port: 42000,
    description: "ClickHouse graphite",
    internal: true,
    protocol: ecs.Protocol.TCP,
  },
];

/**
 * Construct to deploy ClickHouse OLAP DBMS on ECS Fargate
 *
 * This is a basic pattern aimed at experimentation, not scaled production usage: Multi-instance
 * scale out and password rotation are not yet enabled.
 *
 * For more information on best practices, see: https://clickhouse.com/docs/install
 */
export class ClickHouseDeployment extends Construct {
  public readonly clientSecurityGroup: ec2.SecurityGroup;
  public readonly fargateService: ecs.FargateService;
  public readonly nodeSecurityGroup: ec2.SecurityGroup;
  public readonly secret: secretsmanager.Secret;
  private cloudMapService?: servicediscovery.IService;

  private readonly efs: EFSWithSecurityGroups;

  constructor(scope: Construct, id: string, props: IClickHouseDeploymentProps) {
    super(scope, id);

    const cpu = props.cpu || 1024;
    const memoryLimitMiB = props.memoryLimitMiB || 8192;
    const serviceName = props.serviceName || "clickhouse";
    const version = props.version || "25.1";

    this.secret = new secretsmanager.Secret(this, "Secret", {
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          database: "default",
          user: "clickhouse",
        }),
        generateStringKey: "password",
        excludePunctuation: true,
        passwordLength: 24,
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(this.secret).add(tag.key, tag.value);
      });
    }
    NagSuppressions.addResourceSuppressions(this.secret, [
      {
        id: "AwsSolutions-SMG4",
        // To support this, we'd need to automatically force restart of the Langfuse web & worker
        // containers when rotation happens
        // See: https://repost.aws/questions/QUYHw--TXvTTewJeVsT2T5QA/
        reason: "Rotation of ClickHouse secret not implemented",
      },
    ]);

    // Unfortunately the ClickHouse configuration files are baked into the container image, so we
    // need to build a custom image to make overrides for nice ECS deployment:
    const customImage = new ecrassets.DockerImageAsset(this, "CustomImage", {
      directory: path.join(
        __dirname,
        "..",
        "..",
        "..",
        "assets",
        "clickhouse-container",
      ),
      platform: ecrassets.Platform.LINUX_AMD64,
      buildArgs: {
        BASE_IMAGE: `clickhouse:${version}`,
      },
    });

    const deployedImage = new ECRRepoAndDockerImage(this, "ECR", {
      // If the custom image config overrides aren't needed, a straight `clickhouse:${version}`
      // dockerImageName would work here:
      dockerImageName: customImage.imageUri,
      ecrImageTag: version,
      tags: props.tags,
    });

    this.efs = new EFSWithSecurityGroups(this, "EFS", {
      vpc: props.vpc,
      tags: props.tags,
    });

    // Role used by ECS e.g. for pulling the container image, starting up.
    const taskExecutionRole = new iam.Role(this, "ECSTaskExecutionRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      // service-role/AmazonECSTaskExecutionRolePolicy grants pulling *all* images which is broad:
      inlinePolicies: {
        Logs: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              resources: ["*"],
              actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
            }),
          ],
        }),
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(taskExecutionRole).add(tag.key, tag.value);
      });
    }
    this.secret.grantRead(taskExecutionRole);
    deployedImage.repository.grantPull(taskExecutionRole);
    NagSuppressions.addResourceSuppressions(
      taskExecutionRole,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Allow writing logs to any group/stream",
        },
      ],
      true,
    );

    // Role assumed by the running Clickhouse container itself:
    const taskRole = new iam.Role(this, "ECSTaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });
    if (props.tags) {
      props.tags.forEach((tag) => {
        cdk.Tags.of(taskRole).add(tag.key, tag.value);
      });
    }
    this.efs.fileSystem.grantRootAccess(taskRole);

    const CLICKHOUSE_VOLUME_NAME = "clickhouse_data";
    const taskDefinition = new ecs.FargateTaskDefinition(this, "ECSTaskDef", {
      family: "clickhouse",
      cpu,
      memoryLimitMiB,
      executionRole: taskExecutionRole,
      taskRole: taskRole,
      volumes: [
        {
          name: CLICKHOUSE_VOLUME_NAME,
          efsVolumeConfiguration: {
            fileSystemId: this.efs.fileSystem.fileSystemId,
            rootDirectory: "/",
          },
        },
      ],
      runtimePlatform: {
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
        cpuArchitecture: ecs.CpuArchitecture.X86_64,
      },
    });
    if (props.tags) {
      // (ECS Cluster tags don't auto-propagate to running tasks)
      props.tags.forEach((tag) =>
        cdk.Tags.of(taskDefinition).add(tag.key, tag.value),
      );
    }

    const container = taskDefinition.addContainer("ClickhouseContainer", {
      containerName: "clickhouse",
      image: ecs.ContainerImage.fromEcrRepository(
        deployedImage.repository,
        deployedImage.imageTag,
      ),
      cpu,
      environment: props.environment,
      memoryLimitMiB,
      secrets: {
        CLICKHOUSE_DB: ecs.Secret.fromSecretsManager(this.secret, "database"),
        CLICKHOUSE_USER: ecs.Secret.fromSecretsManager(this.secret, "user"),
        CLICKHOUSE_PASSWORD: ecs.Secret.fromSecretsManager(
          this.secret,
          "password",
        ),
      },
      healthCheck: {
        command: [
          "CMD-SHELL",
          `wget --no-verbose --tries=1 --spider http://localhost:${CLICKHOUSE_PORT_HTTP.port}/ping || exit 1`,
        ],
        interval: cdk.Duration.minutes(2),
        retries: 3,
        startPeriod: cdk.Duration.minutes(4),
        timeout: cdk.Duration.seconds(10),
      },
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: "clickhouse",
        logRetention: logs.RetentionDays.ONE_MONTH,
      }),
      portMappings: CLICKHOUSE_PORTS.map((p) => ({
        containerPort: p.port,
        hostPort: p.port,
        protocol: p.protocol,
      })),
      ulimits: [
        {
          name: ecs.UlimitName.NOFILE,
          softLimit: 65535,
          hardLimit: 65535,
        },
      ],
    });
    container.node.addDependency(deployedImage.deployment);
    container.addMountPoints({
      containerPath: "/var/lib/clickhouse",
      readOnly: false,
      sourceVolume: CLICKHOUSE_VOLUME_NAME,
    });

    this.clientSecurityGroup = new ec2.SecurityGroup(this, "ClientSG", {
      vpc: props.vpc,
      allowAllOutbound: false,
      description: "Clients connecting to ClickHouse",
    });
    cdk.Tags.of(this.clientSecurityGroup).add("Name", "clickhouse-clients");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.clientSecurityGroup).add(tag.key, tag.value),
      );
    }

    this.nodeSecurityGroup = new ec2.SecurityGroup(this, "NodeSG", {
      vpc: props.vpc,
      // We currently rely on allowAllOutbound for ECS service nodes, because haven't set up VPC
      // endpoints for all relevant services e.g. ECR, Secrets Manager, EFS and their various DNS.
      allowAllOutbound: true,
      description: "Nodes in ClickHouse service cluster",
    });
    cdk.Tags.of(this.nodeSecurityGroup).add("Name", "clickhouse-nodes");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.nodeSecurityGroup).add(tag.key, tag.value),
      );
    }

    // All ClickHouse ports allowed within the node security group itself:
    CLICKHOUSE_PORTS.forEach((p) => {
      this.nodeSecurityGroup.addIngressRule(
        this.nodeSecurityGroup,
        ec2.Port.tcp(p.port),
        p.description,
      );
      this.nodeSecurityGroup.addEgressRule(
        this.nodeSecurityGroup,
        ec2.Port.tcp(p.port),
        p.description,
      );
    });
    // Only external ports can be connected inbound from clients group:
    CLICKHOUSE_PORTS.filter((p) => !p.internal).forEach((p) => {
      this.nodeSecurityGroup.addIngressRule(
        this.clientSecurityGroup,
        ec2.Port.tcp(p.port),
        p.description,
      );
      this.clientSecurityGroup.addEgressRule(
        this.nodeSecurityGroup,
        ec2.Port.tcp(p.port),
        p.description,
      );
    });

    this.fargateService = new ecs.FargateService(this, "FargateService", {
      serviceName,
      cluster: props.cluster,
      taskDefinition: taskDefinition,
      desiredCount: 1,
      maxHealthyPercent: 100,
      minHealthyPercent: 0,
      propagateTags: ecs.PropagatedTagSource.SERVICE,
      securityGroups: [this.nodeSecurityGroup, this.efs.clientSecurityGroup],
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });
    cdk.Tags.of(this.fargateService).add("Name", serviceName);
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.fargateService).add(tag.key, tag.value),
      );
    }

    this.cloudMapService = props.cloudMapService;
    if (props.cloudMapService) {
      this.fargateService.associateCloudMapService({
        service: props.cloudMapService,
        containerPort:
          this.fargateService.taskDefinition.defaultContainer!.containerPort,
      });
    }
  }

  public get url() {
    if (!this.cloudMapService) {
      throw new Error(
        "URLs are not available when cloudMapService not provided",
      );
    }
    return `http://${this.cloudMapService.serviceName}.${this.cloudMapService.namespace.namespaceName}:${CLICKHOUSE_PORT_HTTP.port}`;
  }

  public get migrationUrl() {
    if (!this.cloudMapService) {
      throw new Error(
        "URLs are not available when cloudMapService not provided",
      );
    }
    return `clickhouse://${this.cloudMapService.serviceName}.${this.cloudMapService.namespace.namespaceName}:${CLICKHOUSE_PORT_NATIVE.port}`;
  }
}
