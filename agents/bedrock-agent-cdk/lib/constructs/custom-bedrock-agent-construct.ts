import * as cdk from "aws-cdk-lib";
import * as lambdaPython from "@aws-cdk/aws-lambda-python-alpha";
import { Construct } from "constructs";

export interface CustomResourceProps extends cdk.StackProps {
  readonly s3BucketArn: string;
  readonly s3BucketName: string;
  readonly s3BucketKey: string;
  readonly collectionId: string;
  readonly bedrockAgentRoleArn: string;
  readonly lambdaArn: string;
  readonly agentName: string;
  readonly bedrockAgentRoleName: string;
}

const defaultProps: Partial<CustomResourceProps> = {};

export class CustomBedrockAgentConstruct extends Construct {

  constructor(scope: Construct, name: string, props: CustomResourceProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const awsAccountId = cdk.Stack.of(this).account;

    const bedrockAgentCustomResourceRole = new cdk.aws_iam.Role(this, 'bedrockAgentCustomResourceRole', {
      assumedBy: new cdk.aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    bedrockAgentCustomResourceRole.addToPolicy(new cdk.aws_iam.PolicyStatement({
      actions: ['*'],
      resources: 
        ['arn:aws:bedrock:*', props.s3BucketArn, `arn:aws:iam::${awsAccountId}:role/${props.bedrockAgentRoleName}`]
    }));

    const layer = new cdk.aws_lambda.LayerVersion(this, 'BedrockAgentLayer', {
      code: cdk.aws_lambda.Code.fromAsset('lib/assets/lambda-layer/agents-layer.zip'),
      compatibleRuntimes: [cdk.aws_lambda.Runtime.PYTHON_3_10],
    });

    const onEvent = new lambdaPython.PythonFunction(this, 'BedrockAgentCustomResourceFunction', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_10,
      handler: 'on_event',
      index: "cdk-resource-bedrock-agent.py",
      entry: "lib/assets/lambdas",
      architecture: cdk.aws_lambda.Architecture.X86_64,
      layers: [layer],
      timeout: cdk.Duration.seconds(300),
      environment: {
        COLLECTION_ID: props.collectionId,
        S3_BUCKET: props.s3BucketName,
        AGENT_NAME: props.agentName,
        BEDROCK_AGENT_ROLE_ARN: props.bedrockAgentRoleArn,
        BEDROCK_AGENT_LAMBDA_ARN: props.lambdaArn,
        S3_BUCKET_KEY: `api-schema/${props.s3BucketKey}`
      },
      role: bedrockAgentCustomResourceRole
    });

    const bedrockAgentCustomResourceProvider = new cdk.custom_resources.Provider(this, 'BedrockCustomResourceProvider', {
      onEventHandler: onEvent,
      logRetention: cdk.aws_logs.RetentionDays.ONE_DAY
    });

    new cdk.CustomResource(this, 'BedrockCustomResource', {
      serviceToken: bedrockAgentCustomResourceProvider.serviceToken
    });
    
    new cdk.CfnOutput(this, "BedrockAgentFunctionArn", {
      value: onEvent.functionArn,
    });
  }
}