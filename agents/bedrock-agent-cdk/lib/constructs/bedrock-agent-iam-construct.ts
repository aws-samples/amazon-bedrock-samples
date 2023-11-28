import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface BedrockIamProps extends cdk.StackProps {
  readonly roleName: string;
  readonly lambdaRoleArn: string;
  readonly s3BucketArn: string;
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
      policyName: "BedrockAgentLambdaPolicy",
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [props.lambdaRoleArn],
          actions: [
            '*',
        ]})
      ]
    });

    const bedrockAgentS3BucketPolicy = new cdk.aws_iam.Policy(this, "BedrockAgentS3BucketPolicy", {
      policyName: "BedrockAgentS3BucketPolicy",
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [props.s3BucketArn, `${props.s3BucketArn}/*`],
          actions: [
            '*',
        ]})
      ]
    });

    const bedrockAgentBedrockModelPolicy = new cdk.aws_iam.Policy(this, "BedrockAgentBedrockModelPolicy", {
      policyName: "BedrockAgentBedrockModelPolicy",
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'bedrock:*',
        ]})
      ]
    });


    bedrockAgentBedrockModelPolicy.node.addDependency(bedrockAgentRole);
    bedrockAgentLambdaPolicy.node.addDependency(bedrockAgentRole);
    bedrockAgentS3BucketPolicy.node.addDependency(bedrockAgentRole);

    bedrockAgentRole.attachInlinePolicy(bedrockAgentLambdaPolicy);
    bedrockAgentRole.attachInlinePolicy(bedrockAgentS3BucketPolicy);
    bedrockAgentRole.attachInlinePolicy(bedrockAgentBedrockModelPolicy);
    
    new cdk.CfnOutput(this, "BedrockAgentRoleArn", {
      value: bedrockAgentRole.roleArn,
    });

    this.roleArn = bedrockAgentRole.roleArn;
  }
}