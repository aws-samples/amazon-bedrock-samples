import * as path from 'path';
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface LambdaLayerProps extends cdk.StackProps {}

const defaultProps: Partial<LambdaLayerProps> = {};

export class LambdaLayerConstruct extends Construct {
  public lambdaLayer: cdk.aws_lambda.LayerVersion;

  constructor(scope: Construct, name: string, props: LambdaLayerProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const lambdaLayer = new cdk.aws_lambda.LayerVersion(this, 'BedrockAgentLayer', {
        code: cdk.aws_lambda.Code.fromAsset(path.join(__dirname, '../../assets/lambda-layer/agents-layer.zip')),
        compatibleRuntimes: [cdk.aws_lambda.Runtime.PYTHON_3_10],
      });

    this.lambdaLayer = lambdaLayer;
  }
}