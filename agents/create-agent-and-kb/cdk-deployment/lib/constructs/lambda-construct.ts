import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface LambdaProps extends cdk.StackProps {
  readonly lambdaName: string;
  readonly handler: string;
  readonly functionPath: string;
  readonly grantInvokeService: string;
  readonly iamRole: cdk.aws_iam.Role;
  readonly lambdaLayer: cdk.aws_lambda.LayerVersion;
  readonly timeout: cdk.Duration;
}

const defaultProps: Partial<LambdaProps> = {};

export class LambdaConstruct extends Construct {
  public lambdaArn: string;
  public lambda: cdk.aws_lambda.Function;

  constructor(scope: Construct, name: string, props: LambdaProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const bedrockAgentLambda = new cdk.aws_lambda.Function(this, "BedrockAgentLambda", {
      functionName: props.lambdaName,
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_10,
      handler: props.handler,
      layers: [props.lambdaLayer],
      code: cdk.aws_lambda.Code.fromAsset(path.join(__dirname, props.functionPath)),
      architecture: cdk.aws_lambda.Architecture.X86_64,
      timeout: props.timeout,
      role: props.iamRole
    });

    bedrockAgentLambda.grantInvoke(new cdk.aws_iam.ServicePrincipal(props.grantInvokeService));

    this.lambdaArn = bedrockAgentLambda.functionArn;
    this.lambda = bedrockAgentLambda;
  }
}