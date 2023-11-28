import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface LambdaIamProps extends cdk.StackProps {
  readonly roleName: string;
}

const defaultProps: Partial<LambdaIamProps> = {};

export class LambdaIamConstruct extends Construct {
  public lambdaRole: cdk.aws_iam.Role;

  constructor(scope: Construct, name: string, props: LambdaIamProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const lambdaRole = new cdk.aws_iam.Role(this, "LambdaRole", {
      roleName: props.roleName,
      assumedBy: new cdk.aws_iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')]
    });
    
    new cdk.CfnOutput(this, "LambdaRoleArn", {
      value: lambdaRole.roleArn,
    });

    this.lambdaRole = lambdaRole;
  }
}