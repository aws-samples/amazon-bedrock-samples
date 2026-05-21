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
   * To avoid rate limit issues for customers without Docker Hub credentials, we use Bitnami's
   * distribution of ClickHouse on Amazon ECR Public by default. If you configure Docker Hub tokens
   * in the environment where you run 'cdk deploy', you could switch to e.g. 'clickhouse:25'.
   * 
   * Note that this construct actually builds a custom (ECR Private) image from the base you
   * specify here, to configure logging for the target ECS environment.
   * 
   * @default 'public.ecr.aws/bitnami/clickhouse:25'
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

    const vpcInfra = new LangfuseVpcInfra(this, "VpcInfra", { tags });

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
