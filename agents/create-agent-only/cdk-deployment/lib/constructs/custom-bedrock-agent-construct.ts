import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface CustomResourceProps extends cdk.StackProps {
  readonly s3BucketArn: string;
  readonly s3BucketName: string;
  readonly s3BucketKey: string;
  readonly resourceId: string;
  readonly bedrockAgentRoleArn: string;
  readonly lambdaArn: string;
  readonly agentName: string;
  readonly bedrockAgentRoleName: string;
  readonly modelName: string;
  readonly instruction: string;
  readonly lambdaLayer: cdk.aws_lambda.LayerVersion;
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

    const onEvent = new cdk.aws_lambda.Function(this, 'BedrockAgentCustomResourceFunction', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_10,
      handler: 'bedrock_agent_custom_resource.on_event',
      code: cdk.aws_lambda.Code.fromAsset(path.join(__dirname, '../../assets/custom-resource')),
      architecture: cdk.aws_lambda.Architecture.X86_64,
      layers: [props.lambdaLayer],
      timeout: cdk.Duration.seconds(600),
      environment: {
        RESOURCE_ID: props.resourceId,
        S3_BUCKET: props.s3BucketName,
        S3_BUCKET_KEY: `api-schema/${props.s3BucketKey}`,
        AGENT_NAME: props.agentName,
        BEDROCK_AGENT_ROLE_ARN: props.bedrockAgentRoleArn,
        BEDROCK_AGENT_LAMBDA_ARN: props.lambdaArn,
        MODEL_NAME: props.modelName,
        INSTRUCTION: props.instruction
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
  }
}