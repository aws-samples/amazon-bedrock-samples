import * as cdk from "aws-cdk-lib";
import * as lambdaPython from "@aws-cdk/aws-lambda-python-alpha";
import { Construct } from "constructs";

export interface LambdaProps extends cdk.StackProps {
  readonly lambdaRoleName: string;
  readonly lambdaFile: string;
  readonly lambdaName: string;
  readonly iamRole: cdk.aws_iam.Role;
}

const defaultProps: Partial<LambdaProps> = {};

export class LambdaConstruct extends Construct {
  public lambdaArn: string;

  constructor(scope: Construct, name: string, props: LambdaProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const bedrockAgentLambda = new lambdaPython.PythonFunction(this, "BedrockAgentLambda", {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_10,
      handler: "lambda_handler",
      index: props.lambdaFile,
      entry: "lib/assets/lambdas/agent",
      timeout: cdk.Duration.seconds(300),
      role: props.iamRole
    });

    bedrockAgentLambda.grantInvoke(new cdk.aws_iam.ServicePrincipal("bedrock.amazonaws.com"));

    new cdk.CfnOutput(this, "BedrockAgentLambdaArn", {
      value: bedrockAgentLambda.functionArn,
    });

    this.lambdaArn = bedrockAgentLambda.functionArn;
  }
}