import {
  Stack,
  type StackProps,
  CfnOutput,
  RemovalPolicy,
  Arn,
} from 'aws-cdk-lib';
import type { Construct } from 'constructs';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction, OutputFormat } from 'aws-cdk-lib/aws-lambda-nodejs';
import { LogGroup, RetentionDays } from 'aws-cdk-lib/aws-logs';
import { CfnAgent } from 'aws-cdk-lib/aws-bedrock';
import {
  Effect,
  PolicyDocument,
  PolicyStatement,
  Role,
  ServicePrincipal,
} from 'aws-cdk-lib/aws-iam';
import { NagSuppressions } from 'cdk-nag';

export class BedrockAgentsStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const region = this.node.tryGetContext('region') || 'us-west-2';
    const modelId =
      this.node.tryGetContext('modelId') || 'amazon.nova-pro-v1:0';
    const geoChars = region.split('-')[0] as string;

    const fnName = 'BedrockAgentsFn';
    const logGroup = new LogGroup(this, 'MyLogGroup', {
      logGroupName: `/aws/lambda/${fnName}`,
      removalPolicy: RemovalPolicy.DESTROY,
      retention: RetentionDays.ONE_DAY,
    });
    const fn = new NodejsFunction(this, 'MyFunction', {
      functionName: fnName,
      logGroup,
      runtime: Runtime.NODEJS_22_X,
      entry: './src/weather.ts',
      handler: 'handler',
      bundling: {
        minify: true,
        mainFields: ['module', 'main'],
        sourceMap: true,
        format: OutputFormat.ESM,
      },
    });
    fn.addToRolePolicy(
      new PolicyStatement({
        actions: ['geo-places:Autocomplete', 'geo-places:GetPlace'],
        resources: [`arn:aws:geo-places:${region}::provider/default`],
        effect: Effect.ALLOW,
      })
    );
    // biome-ignore lint/style/noNonNullAssertion: we know the IAM role exists
    NagSuppressions.addResourceSuppressions(fn.role!, [
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'We are intentionally using the AWS Lambda managed policy for this sample',
      },
    ]);

    const agentRole = new Role(this, 'MyAgentRole', {
      assumedBy: new ServicePrincipal('bedrock.amazonaws.com'),
      description: 'Role for Bedrock weather agent',
      inlinePolicies: {
        bedrock: new PolicyDocument({
          statements: [
            new PolicyStatement({
              actions: ['bedrock:*'],
              resources: [
                Arn.format(
                  {
                    service: 'bedrock',
                    resource: `foundation-model/${modelId}`,
                    region: `${geoChars}-*`,
                    account: '',
                  },
                  Stack.of(this)
                ),
                Arn.format(
                  {
                    service: 'bedrock',
                    resource: 'inference-profile/*',
                    region: `${geoChars}-*`,
                    account: '*',
                  },
                  Stack.of(this)
                ),
              ],
            }),
          ],
        }),
      },
    });
    NagSuppressions.addResourceSuppressions(agentRole, [
      {
        id: 'AwsSolutions-IAM5',
        reason:
          'We are intentionally using a wildcard resource and action to allow customers to fine-tune permissions as needed and as called out in the README.',
      },
    ]);

    const agent = new CfnAgent(this, 'MyCfnAgent', {
      agentName: 'weatherAgent',
      actionGroups: [
        {
          actionGroupName: 'weatherActionGroup',

          actionGroupExecutor: {
            lambda: fn.functionArn,
          },
          functionSchema: {
            functions: [
              {
                name: 'getWeatherForCity',
                description: 'Get weather for a specific city',
                parameters: {
                  city: {
                    type: 'string',
                    description: 'The name of the city to get the weather for',
                    required: true,
                  },
                },
              },
            ],
          },
        },
      ],
      agentResourceRoleArn: agentRole.roleArn,
      autoPrepare: true,
      description: 'A simple weather agent',
      foundationModel: `arn:aws:bedrock:${region}:${Stack.of(this).account}:inference-profile/${geoChars}.${modelId}`,
      instruction:
        'You are a weather forecast news anchor. You will be asked to provide a weather forecast for one or more cities. You will provide a weather forecast for each city as if you were a TV news anchor. While doing so, include the region or country of the city received from the tool. You will provide the forecast in a conversational tone, as if you were speaking to a viewer on a TV news program.',
    });
    fn.addPermission('BedrockAgentInvokePermission', {
      principal: new ServicePrincipal('bedrock.amazonaws.com'),
      action: 'lambda:InvokeFunction',
      sourceAccount: this.account,
      sourceArn: `arn:aws:bedrock:${this.region}:${this.account}:agent/${agent.attrAgentId}`,
    });

    new CfnOutput(this, 'FunctionArn', {
      value: fn.functionArn,
    });
  }
}
