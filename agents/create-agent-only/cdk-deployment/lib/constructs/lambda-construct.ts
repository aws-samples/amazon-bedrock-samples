import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { LayerVersion } from "aws-cdk-lib/aws-lambda";

export interface LambdaProps extends cdk.StackProps {
  readonly lambdaName: string;
  readonly iamRole: cdk.aws_iam.Role;
  readonly lambdaLayer: cdk.aws_lambda.LayerVersion;
}

const defaultProps: Partial<LambdaProps> = {};

export class LambdaConstruct extends Construct {
  public lambdaArn: string;

  constructor(scope: Construct, name: string, props: LambdaProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const bedrockAgentLambda = new cdk.aws_lambda.Function(this, "BedrockAgentLambda", {
      functionName: props.lambdaName,
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_10,
      handler: 'create_agent.lambda_handler',
      layers: [props.lambdaLayer],
      code: cdk.aws_lambda.Code.fromAsset(path.join(__dirname, '../../assets/lambda-function-w-dependencies')),
      architecture: cdk.aws_lambda.Architecture.X86_64,
      timeout: cdk.Duration.seconds(600),
      role: props.iamRole
    });

    bedrockAgentLambda.grantInvoke(new cdk.aws_iam.ServicePrincipal("bedrock.amazonaws.com"));

    this.lambdaArn = bedrockAgentLambda.functionArn;
  }
}