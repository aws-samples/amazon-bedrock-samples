// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export interface ILangfuseVpcInfraProps {
  /**
   * Explicitly specify Availability Zones for the VPC subnets.
   *
   * CloudFront VPC Origins does not support all AZs in every region. In some regions (e.g.
   * ap-northeast-2 Seoul, ap-northeast-1 Tokyo, us-west-1 California, us-east-1 Virginia), one
   * AZ is excluded from CloudFront VPC Origins support. Because AZ IDs map to different AZ names
   * per AWS account in these older regions, CDK's default AZ selection may pick an unsupported AZ
   * causing deployment failures.
   *
   * If you encounter a CloudFront VPC Origins AZ error, use this prop to explicitly specify
   * supported AZs. For example, in ap-northeast-2 (Seoul), exclude the AZ mapped to ID
   * `apne2-az1` in your account:
   * @example ['ap-northeast-2b', 'ap-northeast-2c']
   *
   * See: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html#vpc-origins-supported-regions
   * See: https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html
   *
   * @default CDK selects 2 AZs automatically
   */
  availabilityZones?: string[];
  /**
   * Optional AWS Tags to apply to created resources
   */
  tags?: cdk.Tag[];
}

/**
 * Example construct to deploy shared networking infrastructure for the Langfuse sample
 *
 * You don't need to use this construct if you'd prefer to deploy in your own existing VPC, but can
 * use it as a guide for building a compatible network.
 *
 * Note: VPC Flow Logging is not a hard requirement for the Langfuse solution, but is enabled as a
 * security best-practice for cdk-nag: https://github.com/cdklabs/cdk-nag
 */
export class LangfuseVpcInfra extends Construct {
  public vpc: ec2.IVpc;
  public vpcFlowLog: ec2.FlowLog;
  public vpcFlowLogGroup: logs.ILogGroup;

  constructor(
    scope: Construct,
    id: string,
    props: ILangfuseVpcInfraProps = {},
  ) {
    super(scope, id);

    // maxAzs parameter is not specified by default.
    // The default behavior of the ec2.Vpc construct is to create a VPC with subnets spread across
    // 2 Availability Zones (AZs) when no maxAzs parameter is specified.
    // Each AZ will have one public subnet and one private subnet by default.
    //
    // NOTE: If deploying in a region where CloudFront VPC Origins excludes an AZ (e.g. Seoul,
    // Tokyo, N. California, N. Virginia), pass `availabilityZones` in props to explicitly select
    // supported AZs and avoid deployment failures.
    this.vpc = new ec2.Vpc(this, "Vpc", {
      ...(props.availabilityZones ? { availabilityZones: props.availabilityZones } : {}),
      gatewayEndpoints: {
        S3: {
          service: ec2.GatewayVpcEndpointAwsService.S3,
        },
      },
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.vpc).add(tag.key, tag.value),
      );
    }

    // cdk-nag AwsSolutions-VPC7 rule wants every VPC to have an associated Flow log for debug:
    this.vpcFlowLogGroup = new logs.LogGroup(this, "FlowLogs", {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_MONTH,
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.vpcFlowLogGroup).add(tag.key, tag.value),
      );
    }
    const flowLogRole = new iam.Role(this, "FlowLogRole", {
      assumedBy: new iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(flowLogRole).add(tag.key, tag.value),
      );
    }
    this.vpcFlowLog = new ec2.FlowLog(this, "FlowLog", {
      resourceType: ec2.FlowLogResourceType.fromVpc(this.vpc),
      destination: ec2.FlowLogDestination.toCloudWatchLogs(
        this.vpcFlowLogGroup,
        flowLogRole,
      ),
    });
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.vpcFlowLog).add(tag.key, tag.value),
      );
    }
  }
}
