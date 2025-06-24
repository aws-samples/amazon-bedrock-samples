#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { AwsSolutionsChecks } from "cdk-nag";
import { LangfuseDemoStack } from "../lib/stack";

const app = new cdk.App();
new LangfuseDemoStack(app, "LangfuseDemo", {
  // This stack cannot be synthesized as environment-agnostic (skipping `env`) when
  // `useCognitoAuth` is `true`, because it needs to create a unique domain prefix for Cognito and
  // uses the target Account ID and Region to do this.
  // Here we use the settings implied by the current CLI configuration:
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  // Alternatively, uncomment the next line if you know exactly what Account and Region you
  // want to deploy the stack to:
  // env: { account: '123456789012', region: 'us-east-1' },
  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */

  // Env var is expected to be 'cognito' or 'langfuse' - with cognito as the default:
  useCognitoAuth:
    (process.env.LANGFUSE_AUTH_TYPE || "cognito").toLowerCase() == "cognito",
});

cdk.Aspects.of(app).add(new AwsSolutionsChecks());
