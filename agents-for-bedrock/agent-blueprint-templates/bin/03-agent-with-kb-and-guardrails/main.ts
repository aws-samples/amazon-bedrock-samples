import * as cdk from 'aws-cdk-lib';
import { AgentWithKBandGuardrailsStack } from '../../lib/stacks/03-agent-with-kb-and-guardrails/agent-with-kb-and-guardrails-stack';
// import { RestaurantAssistDatabaseStack } from '../../lib/stacks/03-agent-with-kb-and-guardrails/restaurant-assist-database-stack';

const permissionObject = {
    /* If you don't specify 'env', this stack will be environment-agnostic.
     * Account/Region-dependent features and context lookups will not work,
     * but a single synthesized template can be deployed anywhere. */
    /* Uncomment the next line to specialize this stack for the AWS Account
    * and Region that are implied by the current CLI configuration. */
    // env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },
    /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
    env: { account: '533267284022', region: 'us-east-1' },
};

const app = new cdk.App();

new AgentWithKBandGuardrailsStack(app, 'AgentWithKBandGuardrailsStack', permissionObject)
// new RestaurantAssistDatabaseStack(app, 'RestaurantAssistDatabaseStack', permissionObject)
