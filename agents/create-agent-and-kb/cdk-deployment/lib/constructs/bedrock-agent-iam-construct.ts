import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface BedrockIamProps extends cdk.StackProps {
  readonly roleName: string;
  readonly createLambdaArn: string;
  readonly invokeLambdaArn: string;
  readonly s3BucketArn: string;
  readonly bedrockAgentLambdaPolicy: string;
  readonly bedrockAgentS3BucketPolicy: string;
  readonly bedrockAgentBedrockModelPolicy: string;
}

const defaultProps: Partial<BedrockIamProps> = {};

export class BedrockIamConstruct extends Construct {
    public roleArn: string;

  constructor(scope: Construct, name: string, props: BedrockIamProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const bedrockAgentRole = new cdk.aws_iam.Role(this, "BedrockAgentRole", {
      roleName: props.roleName,
      assumedBy: new cdk.aws_iam.ServicePrincipal('bedrock.amazonaws.com'),
    });

    const bedrockAgentLambdaPolicy = new cdk.aws_iam.Policy(this, "BedrockAgentLambdaPolicy", {
      policyName: props.bedrockAgentLambdaPolicy,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [props.createLambdaArn,
                      props.invokeLambdaArn],
          actions: [
            'lambda:InvokeFunction',
        ]})
      ]
    });

    const bedrockAgentS3BucketPolicy = new cdk.aws_iam.Policy(this, "BedrockAgentS3BucketPolicy", {
      policyName: props.bedrockAgentS3BucketPolicy,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [`${props.s3BucketArn}/api-schemas/create-agent-schema.json`,
                      `${props.s3BucketArn}/api-schemas/invoke-create-kb-lambda-schema.json`],
          actions: [
            's3:GetObject',
        ]})
      ]
    });

    const bedrockAgentBedrockModelPolicy = new cdk.aws_iam.Policy(this, "BedrockAgentBedrockModelPolicy", {
      policyName: props.bedrockAgentBedrockModelPolicy,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'bedrock:*',
        ]})
      ]
    });

    bedrockAgentRole.attachInlinePolicy(bedrockAgentLambdaPolicy);
    bedrockAgentRole.attachInlinePolicy(bedrockAgentS3BucketPolicy);
    bedrockAgentRole.attachInlinePolicy(bedrockAgentBedrockModelPolicy);

    this.roleArn = bedrockAgentRole.roleArn;
  }
}