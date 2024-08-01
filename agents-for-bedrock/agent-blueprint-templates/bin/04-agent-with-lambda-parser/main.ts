#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AgentWithCustomLambdaParserStack } from '../../lib/stacks/04-agent-with-lambda-parser/agent-with-lambda-parser-stack';
// import { HRAssistDataStack } from '../../lib/stacks/01-agent-with-function-definitions/hr-assist-data-stack'

const permissionObject = {
    /* If you don't specify 'env', this stack will be environment-agnostic.
     * Account/Region-dependent features and context lookups will not work,
     * but a single synthesized template can be deployed anywhere. */
    /* Uncomment the next line to specialize this stack for the AWS Account
    * and Region that are implied by the current CLI configuration. */
    // env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },
    /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
    env: { account: '', region: 'us-east-1' },
};

const app = new cdk.App();

// new HRAssistDataStack(app, 'HRAssistDataStack', permissionObject);
new AgentWithCustomLambdaParserStack(app, 'AgentWithCustomLambdaParserStack', permissionObject);
