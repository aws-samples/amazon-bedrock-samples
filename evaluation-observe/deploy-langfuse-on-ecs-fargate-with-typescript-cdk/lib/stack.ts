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
      cognitoUserPool,
      tags,
      vpc: vpcInfra.vpc,
    });

    new cdk.CfnOutput(this, "LangfuseUrl", {
      value: langfuse.url,
    });
  }
}
