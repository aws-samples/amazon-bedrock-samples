// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as servicediscovery from "aws-cdk-lib/aws-servicediscovery";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

// Local Dependencies:
import { CacheCluster } from "./cache";
import { ClickHouseDeployment } from "./clickhouse";
import { addLangfuseCognitoClient, CognitoOAuthSecret } from "./cognito";
import { PublicVpcLoadBalancer } from "./load-balancer";
import { OLTPDatabase } from "./oltp";
import { LangfuseWebService } from "./web";
import { LangfuseWorkerService } from "./worker";

export interface ILangfuseDeploymentProps {
  /**
   * AWS VPC in which to deploy
   *
   * Note that while this solution deploys Langfuse's components within your VPC, it does not
   * *fully* isolate all components' communication to only private subnets: For example, AWS
   * services (such as ECR container pulls, Secrets Manager secret fetches) are generally invoked
   * via their public endpoints, not service VPC endpoints.
   */
  vpc: ec2.IVpc;
  /**
   * The compute and memory capacity of the nodes for Langfuse's (Redis/Valkey) cache
   *
   * @see http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticache-replicationgroup.html#cfn-elasticache-replicationgroup-cachenodetype
   * @see https://langfuse.com/self-hosting/infrastructure/cache
   *
   * @default "cache.t3.small"
   */
  cacheNodeType?: string;
  /**
   * Highly recommended: Use Amazon Cognito for authentication instead of Langfuse's default
   *
   * The user pool must have been configured with a "domain" to work properly. See
   * `cognito.BasicCognitoUserPoolWithDomain` for a simple example.
   *
   * @example new cognito.BasicCognitoUserPoolWithDomain(this, "UserPool").userPool
   *
   * @default - Use Langfuse's built-in authentication, ⚠️ with open sign-up by default!
   */
  cognitoUserPool?: cognito.UserPool;
  /**
   * CPU allocation for the ECS Fargate container running Langfuse's (ClickHouse) OLAP RDBMS
   *
   * (1024 = 1 full vCPU)
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   * @see https://langfuse.com/self-hosting/infrastructure/clickhouse
   *
   * @default 1024
   */
  clickHouseCpu?: number;
  /**
   * Extra environment variables to configure on ClickHouse services' containers
   */
  clickHouseEnvironment?: { [key: string]: string };
  /**
   * Memory allocation for the ECS Fargate container running Langfuse's (ClickHouse) OLAP RDBMS
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 8192
   */
  clickHouseMemoryMiB?: number;
  /**
   * RDS instance type for Langfuse's OLTP (Postgres) database
   *
   * @see https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_rds.DatabaseInstance.html
   * @see https://langfuse.com/self-hosting/infrastructure/postgres
   *
   * @default "r6g.large"
   */
  dbNodeType?: ec2.InstanceType;
  /**
   * Extra environment variables to configure on Langfuse services' containers
   */
  langfuseEnvironment?: { [key: string]: string };
  /**
   * Name to use for the private DNS namespace created for service discovery
   *
   * This namespace is used for different ECS-deployed services in the solution to contact each
   * other: For example Langfuse web & worker services calling to ClickHouse.
   *
   * @default "langfuse.local"
   */
  privateDnsNamespaceName?: string;
  /**
   * Tags to apply across created resources
   */
  tags?: cdk.Tag[];
  /**
   * CPU allocation for the ECS Fargate container running the Langfuse web service
   *
   * (1024 = 1 full vCPU)
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 2048
   */
  webServiceCpu?: number;
  /**
   * Memory allocation for the ECS Fargate container running the Langfuse web service
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 4096
   */
  webServiceMemoryMiB?: number;
  /**
   * CPU allocation for the ECS Fargate container running the Langfuse async worker service
   *
   * (1024 = 1 full vCPU)
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 2048
   */
  workerCpu?: number;
  /**
   * Memory allocation for the ECS Fargate container running the Langfuse async worker service
   *
   * @see https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html#fargate-tasks-size
   *
   * @default 4096
   */
  workerMemoryMiB?: number;
}

/**
 * Construct to deploy Langfuse using ECS Fargate and native AWS database services
 *
 * This is a basic pattern intended for initial experimentation with Langfuse and not scaled
 * production deployments: Auto-scaling is not configured across all of the different services
 * created. For more information on best-practices for hosting Langfuse, see:
 * https://langfuse.com/self-hosting
 */
export class LangfuseDeployment extends Construct {
  public readonly ecsCluster: ecs.ICluster;
  public readonly dnsNamespace: servicediscovery.PrivateDnsNamespace;

  private loadBalancer: PublicVpcLoadBalancer;

  constructor(scope: Construct, id: string, props: ILangfuseDeploymentProps) {
    super(scope, id);
    const privateDnsNamespaceName =
      props.privateDnsNamespaceName || "langfuse.local";

    this.ecsCluster = new ecs.Cluster(this, "ECSCluster", {
      vpc: props.vpc,
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.ecsCluster).add(tag.key, tag.value),
      );
    }

    this.dnsNamespace = new servicediscovery.PrivateDnsNamespace(
      this,
      "PrivateDNS",
      {
        name: privateDnsNamespaceName,
        description: "Langfuse Service Discovery namespace",
        vpc: props.vpc,
      },
    );
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.dnsNamespace).add(tag.key, tag.value),
      );
    }
    const clickHouseService = this.dnsNamespace.createService("ClickHouseDNS", {
      name: "clickhouse",
      dnsRecordType: servicediscovery.DnsRecordType.A,
      dnsTtl: cdk.Duration.seconds(10),
      customHealthCheck: {
        failureThreshold: 1,
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.dnsNamespace).add(tag.key, tag.value),
      );
    }

    const cacheCluster = new CacheCluster(this, "CacheCluster", {
      cacheNodeType: props.cacheNodeType || "cache.t3.small",
      vpc: props.vpc,
      tags: props.tags,
    });

    const bucket = new s3.Bucket(this, "bucket", {
      autoDeleteObjects: true,
      blockPublicAccess: {
        blockPublicAcls: true,
        blockPublicPolicy: true,
        ignorePublicAcls: true,
        restrictPublicBuckets: true,
      },
      cors: [],
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      minimumTLSVersion: 1.2,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    NagSuppressions.addResourceSuppressions(bucket, [
      {
        id: "AwsSolutions-S1",
        reason: "Not logging access on Langfuse artifacts bucket",
      },
    ]);
    if (props.tags) {
      props.tags.forEach((tag) => cdk.Tags.of(bucket).add(tag.key, tag.value));
    }

    this.loadBalancer = new PublicVpcLoadBalancer(this, "LoadBalancer", {
      vpc: props.vpc,
      tags: props.tags,
    });
    NagSuppressions.addResourceSuppressions(this.loadBalancer.loadBalancer, [
      {
        id: "AwsSolutions-ELB2",
        reason: "Region is required to enable ELBv2 access logging",
      },
    ]);

    let cognitoClientSecret: secretsmanager.Secret | undefined;
    if (props.cognitoUserPool) {
      const cognitoClient = addLangfuseCognitoClient(
        props.cognitoUserPool,
        "Langfuse",
        {
          baseUrl: this.loadBalancer.url,
        },
      );
      cognitoClientSecret = new CognitoOAuthSecret(this, "CognitoAuthSecret", {
        client: cognitoClient,
        userPool: props.cognitoUserPool,
      });
    }

    const oltpDb = new OLTPDatabase(this, "OLTP", {
      vpc: props.vpc,
      instanceType: props.dbNodeType,
      tags: props.tags,
    });

    const clickhouse = new ClickHouseDeployment(this, "ClickHouse", {
      cluster: this.ecsCluster,
      cloudMapService: clickHouseService,
      cpu: props.clickHouseCpu,
      environment: props.clickHouseEnvironment,
      memoryLimitMiB: props.clickHouseMemoryMiB,
      vpc: props.vpc,
      tags: props.tags,
    });

    const encryptionKeySecret = new secretsmanager.Secret(
      this,
      "EncKeySecret",
      {
        description:
          "Langfuse ENCRYPTION_KEY (Used to encrypt sensitive data. Must be 256 bits, 64 string characters in hex format)",
        generateSecretString: {
          excludeCharacters: "ghijklmnopqrstuvxyz",
          excludePunctuation: true,
          includeSpace: false,
          excludeUppercase: true,
          passwordLength: 64,
        },
      },
    );
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(encryptionKeySecret).add(tag.key, tag.value),
      );
    }
    NagSuppressions.addResourceSuppressions(
      encryptionKeySecret,
      [
        {
          id: "AwsSolutions-SMG4",
          reason:
            "Secret rotation not implemented as Langfuse application requires explicit coordination during credential rotation",
        },
      ],
      true,
    );

    const nextAuthSecret = new secretsmanager.Secret(this, "NextAuthSecret", {
      description:
        "Langfuse NEXTAUTH_SECRET (Used to validate login session cookies)",
      generateSecretString: {
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 50,
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(nextAuthSecret).add(tag.key, tag.value),
      );
    }
    NagSuppressions.addResourceSuppressions(
      nextAuthSecret,
      [
        {
          id: "AwsSolutions-SMG4",
          reason:
            "Secret rotation not implemented as Langfuse requires explicit coordination during credential rotation",
        },
      ],
      true,
    );
    const saltSecret = new secretsmanager.Secret(this, "SaltSecret", {
      description: "Langfuse SALT (Used to salt hashed API keys)",
      generateSecretString: {
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 50,
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(saltSecret).add(tag.key, tag.value),
      );
    }
    NagSuppressions.addResourceSuppressions(
      saltSecret,
      [
        {
          id: "AwsSolutions-SMG4",
          reason:
            "Secret rotation not implemented as Langfuse requires explicit coordination during credential rotation",
        },
      ],
      true,
    );

    new LangfuseWorkerService(this, "Worker", {
      cache: cacheCluster,
      clickhouse,
      cluster: this.ecsCluster,
      cpu: props.workerCpu,
      encryptionKeySecret,
      environment: props.langfuseEnvironment,
      memoryLimitMiB: props.workerMemoryMiB,
      oltpDb,
      s3Bucket: bucket,
      saltSecret,
      vpc: props.vpc,
      s3BatchExportPrefix: "langfuse-exports/",
      tags: props.tags,
    });

    new LangfuseWebService(this, "Web", {
      cache: cacheCluster,
      clickhouse,
      cluster: this.ecsCluster,
      cpu: props.webServiceCpu,
      encryptionKeySecret,
      environment: props.langfuseEnvironment,
      loadBalancer: this.loadBalancer,
      memoryLimitMiB: props.webServiceMemoryMiB,
      nextAuthSecret,
      oltpDb,
      s3Bucket: bucket,
      saltSecret,
      vpc: props.vpc,
      s3BatchExportPrefix: "langfuse-exports/",
      tags: props.tags,
      authCognitoSecret: cognitoClientSecret,
    });
  }

  public get url(): string {
    return this.loadBalancer.url;
  }
}
