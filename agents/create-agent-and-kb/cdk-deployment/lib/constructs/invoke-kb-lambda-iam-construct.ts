import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface InvokeKbLambdaIamProps extends cdk.StackProps {
  readonly roleName: string;
  readonly eventBusAllowPolicyName: string;
  readonly eventBusArn: string;
}

const defaultProps: Partial<InvokeKbLambdaIamProps> = {};

export class InvokeKbLambdaIamConstruct extends Construct {
  public lambdaRole: cdk.aws_iam.Role;

  constructor(scope: Construct, name: string, props: InvokeKbLambdaIamProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const lambdaRole = new cdk.aws_iam.Role(this, "InvokeCreateKbLambdaRole", {
      roleName: props.roleName,
      assumedBy: new cdk.aws_iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')]
    });

    const eventBusAllowPolicy = new cdk.aws_iam.Policy(this, "EventBusAllowPolicy", {
      policyName: props.eventBusAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [props.eventBusArn],
          actions: ['events:PutEvents'],
        })
      ]
    });

    lambdaRole.attachInlinePolicy(eventBusAllowPolicy);

    this.lambdaRole = lambdaRole;
  }
}