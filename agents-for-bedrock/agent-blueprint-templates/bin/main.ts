import * as cdk from 'aws-cdk-lib';
import { AgentWithFunctionDefinitionStack } from '../lib/stacks/01-agent-with-function-definitions/agent-with-function-definition-stack';
import { AgentWithROCStack } from '../lib/stacks/02-agent-with-return-of-control/agent-with-ROC-stack';
import { AgentWithCustomLambdaParserStack } from '../lib/stacks/04-agent-with-lambda-parser/agent-with-lambda-parser-stack';
import { AgentWithSimpleClassificationStack } from '../lib/stacks/05-agent-with-classification-instructions/agent-with-classification-instructions-stack';
import { AgentWithKBandGuardrailsStack } from '../lib/stacks/03-agent-with-kb-and-guardrails/agent-with-kb-and-guardrails-stack';

/* If you don't specify 'env', this stack will be environment-agnostic.
 * Account/Region-dependent features and context lookups will not work,
 * but a single synthesized template can be deployed anywhere. 
 * For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html 
 * The env variables USER_REGION and USER_ACCOUNT are set from the blueprint.sh script
 */
const permissionObject = {
    env: { 
        account: process.env.USER_ACCOUNT, 
        region: process.env.USER_REGION 
    },
};

const app = new cdk.App();

const stackToDeploy = process.env.STACK_TO_DEPLOY;

switch (stackToDeploy) {
    case '01-agent-with-function-definitions':
        new AgentWithFunctionDefinitionStack(app, 'AgentWithFunctionDefinitionStack', permissionObject);
        break;
    case '02-agent-with-return-of-control':
        new AgentWithROCStack(app, 'AgentWithROCStack', permissionObject);
        break;
    case '03-agent-with-kb-and-guardrails':
        new AgentWithKBandGuardrailsStack(app, 'AgentWithKBandGuardrailsStack', permissionObject);
        break;
    case '04-agent-with-lambda-parser':
        new AgentWithCustomLambdaParserStack(app, 'AgentWithCustomLambdaParserStack', permissionObject);
        break;
    case '05-agent-with-classification-instructions':
        new AgentWithSimpleClassificationStack(app, 'AgentWithSimpleClassificationStack', permissionObject);
        break;
    default:
        console.log('No stack to deploy');
}