import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface S3Props extends cdk.StackProps {
  readonly assetFullPath?: string;
}
  
const defaultProps: Partial<S3Props> = {};

export class S3Construct extends Construct {
  public bucket: cdk.aws_s3.Bucket;
  public bucketName: string;
  readonly s3Bucket: cdk.aws_s3.Bucket;

  constructor(parent: Construct, name: string, props: S3Props) {
    super(parent, name);

    props = { ...defaultProps, ...props };

    this.s3Bucket = new cdk.aws_s3.Bucket(this, "Bucket", {
      autoDeleteObjects: true,
      bucketName: `${name}-bucket`,
      blockPublicAccess: cdk.aws_s3.BlockPublicAccess.BLOCK_ALL,
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      enforceSSL: true,
    });

    props.assetFullPath && this.deployAsset(this.s3Bucket, props.assetFullPath);

    this.bucketName = this.s3Bucket.bucketName;
    this.bucket = this.s3Bucket;
  }

  private deployAsset(s3Bucket: cdk.aws_s3.Bucket, assetFullPath: string): void {
    new cdk.aws_s3_deployment.BucketDeployment(this, "ApiSchemasBucket", {
      sources: [
        cdk.aws_s3_deployment.Source.asset(
          path.join(__dirname, assetFullPath)
        ),
      ],
      destinationBucket: s3Bucket,
      destinationKeyPrefix: "api-schemas",
    });
  }
}
