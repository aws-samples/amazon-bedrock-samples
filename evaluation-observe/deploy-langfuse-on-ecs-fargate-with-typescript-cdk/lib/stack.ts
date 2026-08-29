// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

// Local Dependencies:
import { LangfuseDeployment, LangfuseVpcInfra } from "./langfuse";
import { BasicCognitoUserPoolWithDomain } from "./langfuse/cognito";

export interface ILangfuseDemoStackProps extends cdk.StackProps {
  /**
   * Source container image (including version) for ClickHouse
   *
   * We use Altinity's stable ClickHouse distribution on Amazon ECR Public by default to avoid
   * Docker Hub rate limits for customers without Docker Hub credentials. (Bitnami's distribution,
   * previously used here, is no longer published on ECR Public.) You can also use the official
   * Docker Hub image (e.g. 'clickhouse/clickhouse-server:25') if you configure Docker Hub
   * credentials in the environment where you run 'cdk deploy'.
   *
   * Note that this construct actually builds a custom (ECR Private) image from the base you
   * specify here, to configure logging for the target ECS environment.
   *
   * @default 'public.ecr.aws/altinity/clickhouse/clickhouse-server:25.8.28'
   */
  clickHouseImage?: string;
  /**
   * Source container image (including version) for main Langfuse web service container
   *
   * We use GitHub Container Registry by default, but you could also consider Docker Hub with e.g.
   * 'langfuse/langfuse:3'
   *
   * @default 'ghcr.io/langfuse/langfuse:3'
   */
  langfuseWebImage?: string;
  /**
   * Source container image (including version) for Langfuse background worker container
   *
   * We use GitHub Container Registry by default, but you could also consider Docker Hub with e.g.
   * 'langfuse/langfuse-worker:3'
   *
   * @default 'ghcr.io/langfuse/langfuse-worker:3'
   */
  langfuseWorkerImage?: string;
  /**
   * Explicitly specify Availability Zones for the VPC.
   *
   * CloudFront VPC Origins does not support all AZs in every region. In some regions (e.g.
   * ap-northeast-2 Seoul, ap-northeast-1 Tokyo, us-west-1 California, us-east-1 Virginia), one
   * AZ is excluded. Because AZ IDs map to different names per AWS account in these older regions,
   * CDK's default AZ selection may pick an unsupported AZ causing deployment failures.
   *
   * If you encounter a CloudFront VPC Origins AZ error, use this prop to explicitly specify
   * supported AZs. For example, in ap-northeast-2 (Seoul), exclude the AZ mapped to ID
   * `apne2-az1` in your account:
   * @example ['ap-northeast-2b', 'ap-northeast-2c']
   *
   * @default CDK selects 2 AZs automatically
   */
  availabilityZones?: string[];
  /**
   * Set `true` to create and use Amazon Cognito User Pool for authentication
   *
   * @default - Langfuse native auth will be used - ⚠️ with open sign-up!
   */
  useCognitoAuth?: boolean;
}

/**
 * A basic deployment of the Langfuse construct pattern for demos
 */
export class LangfuseDemoStack extends cdk.Stack {
  constructor(
    scope: Construct,
    id: string,
    props: ILangfuseDemoStackProps = {},
  ) {
    super(scope, id, props);

    const tags = [new cdk.Tag("project", "langfuse-demo")];

    const vpcInfra = new LangfuseVpcInfra(this, "VpcInfra", {
      availabilityZones: props.availabilityZones,
      tags,
    });

    let cognitoUserPool;
    if (props.useCognitoAuth) {
      cognitoUserPool = new BasicCognitoUserPoolWithDomain(
        this,
        "LangfuseCognito",
      ).userPool;
      // Also output the pool ID to help admins identify the correct one in console:
      new cdk.CfnOutput(this, "CognitoUserPoolId", {
        value: cognitoUserPool.userPoolId,
      });
    }

    // The code that defines your stack goes here
    const langfuse = new LangfuseDeployment(this, "Langfuse", {
      clickHouseImage: props.clickHouseImage,
      cognitoUserPool,
      langfuseWebImage: props.langfuseWebImage,
      langfuseWorkerImage: props.langfuseWorkerImage,
      tags,
      vpc: vpcInfra.vpc,
    });

    new cdk.CfnOutput(this, "LangfuseUrl", {
      value: langfuse.url,
    });
  }
}
