// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

// Local Dependencies:
import { CacheCluster } from "./cache";
import { ClickHouseDeployment } from "./clickhouse";
import { ECRRepoAndDockerImage } from "./ecr";
import { OLTPDatabase } from "./oltp";

/**
 * Shared construct properties for Langfuse services (shared between web and worker)
 */
export interface ILangfuseServiceSharedProps {
  /**
   * (Redis/Valkey) cache infrastructure
   */
  cache: CacheCluster;
  /**
   * (ClickHouse) OLAP infrastructure
   */
  clickhouse: ClickHouseDeployment;
  /**
   * ECS Cluster within which to deploy
   */
  cluster: ecs.ICluster;
  /**
   * Secrets Manager Secret to use for Langfuse ENCRYPTION_KEY configuration
   *
   * See: https://langfuse.com/self-hosting/configuration
   */
  encryptionKeySecret: secretsmanager.ISecret;
  /**
   * (Postgres) OLTP database infrastructure
   */
  oltpDb: OLTPDatabase;
  /**
   * S3 bucket for Langfuse artifacts (shared between different artifact types)
   */
  s3Bucket: s3.IBucket;
  /**
   * Secrets Manager Secret to use for Langfuse SALT configuration
   *
   * See: https://langfuse.com/self-hosting/configuration
   */
  saltSecret: secretsmanager.ISecret;
  /**
   * AWS VPC in which to deploy
   */
  vpc: ec2.IVpc;
  /**
   * CPU allocation for the service's ECS Fargate container(s)
   *
   * 1024 = 1 full vCPU
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 2048
   */
  cpu?: number;
  /**
   * Set true to enable Langfuse's telemetry (turned off by default)
   *
   * @default false
   */
  enableLangfuseTelemetry?: boolean;
  /**
   * Set true to enable Langfuse's experimental features
   *
   * @default false
   */
  enableLangfuseExperimentalFeatures?: boolean;
  /**
   * Extra environment variables to configure on the service's containers
   */
  environment?: { [key: string]: string };
  /**
   * Source container image tag (version) for the service
   *
   * @default '3'
   */
  imageTag?: string;
  /**
   * Memory allocation for the service's ECS Fargate container(s)
   *
   * https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 4096
   */
  memoryLimitMiB?: number;
  /**
   * Desired number of container replicas to run
   *
   * @default 1
   */
  numReplicas?: number;
  /**
   * S3 key prefix for storing Langfuse batch exports.
   *
   * Langfuse batch exports will be disabled if this property is not provided. If set, it must end
   * with a '/'.
   *
   * @default None (batch export disabled)
   */
  s3BatchExportPrefix?: string;
  /**
   * S3 key prefix for uploading Langfuse Events
   *
   * @default "langfuse-events/"
   */
  s3EventUploadPrefix?: string;
  /**
   * S3 key prefix for uploading Langfuse Media
   *
   * @default "langfuse-media/"
   */
  s3MediaUploadPrefix?: string;
  /**
   * AWS Tags to apply to created resources (task definition, role, etc)
   */
  tags?: cdk.Tag[];
}

export interface ILangfuseServiceBaseProps extends ILangfuseServiceSharedProps {
  /**
   * How ECS health-checks should run for this service
   */
  healthCheck: ecs.HealthCheck;
  /**
   * Source container image name for the service
   */
  imageName: string;
  /**
   * Port mappings required for this service
   */
  portMappings?: ecs.PortMapping[];
  /**
   * Extra Secrets Manager Secrets required for this particular service's containers
   */
  secrets?: { [key: string]: cdk.aws_ecs.Secret };
  /**
   * Name of the service, used in ECS family name and various descriptions etc
   *
   * Should be alphanumeric and reasonably short. We typically expect it's either
   * 'web' (for the web server) or 'worker' (for the async worker)
   */
  serviceName: string;
}

/**
 * Base class for a Langfuse service (shared between web & worker)
 */
export class LangfuseServiceBase extends Construct {
  public readonly fargateService: ecs.FargateService;

  constructor(scope: Construct, id: string, props: ILangfuseServiceBaseProps) {
    super(scope, id);

    const cpu = props.cpu || 2048;
    const imageTag = props.imageTag || "3";
    const memoryLimitMiB = props.memoryLimitMiB || 4096;
    const numReplicas = props.numReplicas || 1;
    const s3EventUploadPrefix = props.s3EventUploadPrefix || "langfuse-events/";
    const s3MediaUploadPrefix = props.s3MediaUploadPrefix || "langfuse-media/";
    if (props.s3BatchExportPrefix && !props.s3BatchExportPrefix.endsWith("/")) {
      throw new Error(
        `s3BatchExportPrefix, if provided, must end with a '/'. Got: ${props.s3BatchExportPrefix}`,
      );
    }

    const image = new ECRRepoAndDockerImage(this, "ECR", {
      dockerImageName: `${props.imageName}:${imageTag}`,
      ecrImageTag: imageTag,
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
    image.repository.grantPull(taskExecutionRole);
    props.clickhouse.secret.grantRead(taskExecutionRole);
    props.oltpDb.secret.grantRead(taskExecutionRole);
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

    const taskRole = new iam.Role(this, "ECSTaskRole", {
      // roleName: `ECSTaskRole-${this.stackName}`,
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: `Role for Langfuse ${props.serviceName} container(s)`,
    });
    props.s3Bucket.grantReadWrite(taskRole, s3EventUploadPrefix + "*");
    props.s3Bucket.grantReadWrite(taskRole, s3MediaUploadPrefix + "*");
    if (props.s3BatchExportPrefix) {
      props.s3Bucket.grantReadWrite(taskRole, props.s3BatchExportPrefix + "*");
    }
    NagSuppressions.addResourceSuppressions(
      taskRole,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Allow all S3 paths under given prefixes",
        },
      ],
      true,
    );

    const taskDefinition = new ecs.FargateTaskDefinition(this, "ECSTaskDef", {
      executionRole: taskExecutionRole,
      family: `langfuse-${props.serviceName}`,
      cpu,
      memoryLimitMiB,
      taskRole,
    });
    if (props.tags) {
      // (ECS Cluster tags don't auto-propagate to running tasks)
      props.tags.forEach((tag) =>
        cdk.Tags.of(taskDefinition).add(tag.key, tag.value),
      );
    }

    // Environment Variables for the container
    // https://langfuse.com/self-hosting/configuration#environment-variables
    const dockerRunArgs = this.node.tryGetContext(
      `langfuse_${props.serviceName}_env`,
    );
    const taskEnv = {
      ...dockerRunArgs,

      CLICKHOUSE_MIGRATION_URL: props.clickhouse.migrationUrl,
      CLICKHOUSE_URL: props.clickhouse.url,
      CLICKHOUSE_CLUSTER_ENABLED: "false",

      // DATABASE_ARGS?

      REDIS_HOST: props.cache.cluster.attrPrimaryEndPointAddress,
      REDIS_PORT: props.cache.cluster.attrPrimaryEndPointPort,
      REDIS_TLS_ENABLED: "true",

      LANGFUSE_S3_EVENT_UPLOAD_BUCKET: props.s3Bucket.bucketName,
      LANGFUSE_S3_EVENT_UPLOAD_PREFIX: s3EventUploadPrefix,
      LANGFUSE_S3_EVENT_UPLOAD_REGION: cdk.Stack.of(this).region,

      LANGFUSE_S3_MEDIA_UPLOAD_BUCKET: props.s3Bucket.bucketName,
      LANGFUSE_S3_MEDIA_UPLOAD_PREFIX: s3MediaUploadPrefix,
      LANGFUSE_S3_MEDIA_UPLOAD_REGION: cdk.Stack.of(this).region,

      LANGFUSE_S3_BATCH_EXPORT_ENABLED: props.s3BatchExportPrefix
        ? "true"
        : "false",

      HOSTNAME: "0.0.0.0",
      LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES:
        props.enableLangfuseExperimentalFeatures ? "true" : "false",
      NODE_ENV: "production",
      TELEMETRY_ENABLED: props.enableLangfuseTelemetry ? "true" : "false",
      ...(props.environment || {}),
    };
    if (props.s3BatchExportPrefix) {
      taskEnv.LANGFUSE_S3_BATCH_EXPORT_BUCKET = props.s3Bucket.bucketName;
      taskEnv.LANGFUSE_S3_BATCH_EXPORT_PREFIX = props.s3BatchExportPrefix;
      taskEnv.LANGFUSE_S3_BATCH_EXPORT_REGION = cdk.Stack.of(this).region;
    }

    taskDefinition.addContainer("Container", {
      containerName: `langfuse-${props.serviceName}`,
      image: ecs.ContainerImage.fromEcrRepository(
        image.repository,
        image.imageTag,
      ),
      // essential: true,
      environment: taskEnv,
      healthCheck: props.healthCheck,
      secrets: {
        CLICKHOUSE_DB: ecs.Secret.fromSecretsManager(
          props.clickhouse.secret,
          "database",
        ),
        CLICKHOUSE_PASSWORD: ecs.Secret.fromSecretsManager(
          props.clickhouse.secret,
          "password",
        ),
        CLICKHOUSE_USER: ecs.Secret.fromSecretsManager(
          props.clickhouse.secret,
          "user",
        ),
        DATABASE_HOST: ecs.Secret.fromSecretsManager(
          props.oltpDb.secret,
          "host",
        ),
        DATABASE_PORT: ecs.Secret.fromSecretsManager(
          props.oltpDb.secret,
          "port",
        ),
        DATABASE_USERNAME: ecs.Secret.fromSecretsManager(
          props.oltpDb.secret,
          "username",
        ),
        DATABASE_PASSWORD: ecs.Secret.fromSecretsManager(
          props.oltpDb.secret,
          "password",
        ),
        DATABASE_NAME: ecs.Secret.fromSecretsManager(
          props.oltpDb.secret,
          "dbname",
        ),
        ENCRYPTION_KEY: ecs.Secret.fromSecretsManager(
          props.encryptionKeySecret,
        ),
        REDIS_AUTH: ecs.Secret.fromSecretsManager(props.cache.authSecret),
        SALT: ecs.Secret.fromSecretsManager(props.saltSecret),
        ...(props.secrets || {}),
      },
      logging: ecs.LogDriver.awsLogs({
        streamPrefix: `langfuse-${props.serviceName}`,
        logRetention: logs.RetentionDays.ONE_MONTH,
      }),
      portMappings: props.portMappings,
    });
    NagSuppressions.addResourceSuppressions(taskDefinition, [
      {
        id: "AwsSolutions-ECS2",
        reason: "Secrets are separated from non-secret environment variables",
      },
    ]);

    const awsAccessSG = new ec2.SecurityGroup(this, "AWSAccess", {
      vpc: props.vpc,
      // We currently rely on allowAllOutbound for ECS service nodes, because haven't set up VPC
      // endpoints for all relevant services e.g. ECR, Secrets Manager, EFS and their various DNS.
      allowAllOutbound: true,
      description:
        "Open outbound access for Langfuse containers to reach non-VPC AWS service endpoints",
    });
    cdk.Tags.of(awsAccessSG).add(
      "Name",
      `langfuse-${props.serviceName}-awsaccess`,
    );
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(awsAccessSG).add(tag.key, tag.value),
      );
    }

    this.fargateService = new ecs.FargateService(this, "FargateService", {
      serviceName: `langfuse_${props.serviceName}`,
      cluster: props.cluster,
      taskDefinition,
      desiredCount: numReplicas,
      minHealthyPercent: 50,
      propagateTags: ecs.PropagatedTagSource.SERVICE,
      securityGroups: [
        awsAccessSG,
        props.cache.clientSecurityGroup,
        props.clickhouse.clientSecurityGroup,
        props.oltpDb.clientSecurityGroup,
      ],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
    });
    cdk.Tags.of(this.fargateService).add(
      "Name",
      `langfuse_${props.serviceName}`,
    );
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.fargateService).add(tag.key, tag.value),
      );
    }
  }
}
