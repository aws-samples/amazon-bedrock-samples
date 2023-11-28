import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface CreateKbLambdaIamProps extends cdk.StackProps {
  readonly roleName: string;
  readonly lambdaAllowPolicyName: string;
  readonly bedrockAllowPolicyName: string;
  readonly iamAllowPolicyName: string;
  readonly opensearchAllowPolicyName: string;
}

const defaultProps: Partial<CreateKbLambdaIamProps> = {};

export class CreateKbLambdaIamConstruct extends Construct {
  public lambdaRole: cdk.aws_iam.Role;

  constructor(scope: Construct, name: string, props: CreateKbLambdaIamProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const lambdaRole = new cdk.aws_iam.Role(this, "CreateKbLambdaRole", {
      roleName: props.roleName,
      assumedBy: new cdk.aws_iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')]
    });

    const lambdaAllowPolicy = new cdk.aws_iam.Policy(this, "lambdaAllowPolicy", {
      policyName: props.lambdaAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'lambda:GetFunctionConfiguration'
          ],
        })
      ]
    });

    const iamAllowPolicy = new cdk.aws_iam.Policy(this, "CreateKbiamAllowPolicy", {
      policyName: props.iamAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'iam:PassRole',
            'iam:CreateRole',
            'iam:AttachRolePolicy',
            'iam:GetRole',
            'iam:CreatePolicy'
          ],
        })
      ]
    });

    const bedrockAllowPolicy = new cdk.aws_iam.Policy(this, "bedrockAllowPolicy", {
      policyName: props.bedrockAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'bedrock:*'
          ],
        })
      ]
    });

    const opensearchAllowPolicy = new cdk.aws_iam.Policy(this, "opensearchAllowPolicy", {
      policyName: props.opensearchAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            "aoss:CreateAccessPolicy",
            "aoss:CreateSecurityPolicy",
            "aoss:CreateDomain",
            "aoss:CreateCollection",
            "aoss:BatchGetCollection",
            "aoss:APIAccessAll"
          ]
        })
      ]
    });
    
    lambdaRole.attachInlinePolicy(opensearchAllowPolicy);
    lambdaRole.attachInlinePolicy(lambdaAllowPolicy);
    lambdaRole.attachInlinePolicy(bedrockAllowPolicy);
    lambdaRole.attachInlinePolicy(iamAllowPolicy);

    this.lambdaRole = lambdaRole;
  }
}