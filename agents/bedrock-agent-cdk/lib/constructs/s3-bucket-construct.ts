import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface S3Props extends cdk.StackProps {}
  
const defaultProps: Partial<S3Props> = {};

export class S3Construct extends Construct {
  public bucket: cdk.aws_s3.Bucket;
  public bucketName: string;

  constructor(parent: Construct, name: string, props: S3Props) {
    super(parent, name);

    props = { ...defaultProps, ...props };

    const s3Bucket = new cdk.aws_s3.Bucket(this, "Bucket", {
      autoDeleteObjects: true,
      bucketName: `${name}-bucket`,
      blockPublicAccess: cdk.aws_s3.BlockPublicAccess.BLOCK_ALL,
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      enforceSSL: true,
    });

    new cdk.aws_s3_deployment.BucketDeployment(this, "ApiSchemaBucket", {
      sources: [
        cdk.aws_s3_deployment.Source.asset(
            "lib/assets/api-schema"
        ),
      ],
      destinationBucket: s3Bucket,
      destinationKeyPrefix: "api-schema",
    });

    new cdk.CfnOutput(this, `${name}-bucket`, {
      value: `${s3Bucket.bucketName}`,
    });

    this.bucketName = s3Bucket.bucketName;
    this.bucket = s3Bucket;
  }
}