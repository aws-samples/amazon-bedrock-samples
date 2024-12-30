import { RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Bucket, BlockPublicAccess } from 'aws-cdk-lib/aws-s3';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';

export interface S3BucketStackProps extends StackProps {
    codePipelineName: string;
    stageName: string;
}

export class S3BucketStack extends Stack {

    constructor(scope: Construct, id: string, props: S3BucketStackProps) {
        super(scope, id, props);

        // Create the S3 bucket for Lambda packages
        const lambdaPackageBucket = new Bucket(this, 'LambdaPackageBucket', {
            // bucketName: "cdk-multimodal-rag-bedrock-customlambda-package-bucket",
            versioned: true, // Enable versioning
            removalPolicy: RemovalPolicy.DESTROY, // Cleanup bucket in dev environments
            blockPublicAccess: BlockPublicAccess.BLOCK_ALL, // Ensure no public access
            autoDeleteObjects: true, // Automatically delete objects when the bucket is deleted
        });

        // Store the bucket name in SSM Parameter Store
        new StringParameter(this, 'LambdaPackageBucketNameParameter', {
            parameterName: `/${props.codePipelineName}/${props.stageName}/lambda-package-bucket-name`,
            stringValue: lambdaPackageBucket.bucketName,
        });


    }
}
