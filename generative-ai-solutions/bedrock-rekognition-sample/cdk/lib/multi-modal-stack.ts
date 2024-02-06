import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { S3EventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { EventType } from 'aws-cdk-lib/aws-s3';
import { LambdaFunction } from 'aws-cdk-lib/aws-events-targets';

export class MultiModal extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bucket = new cdk.aws_s3.Bucket(this, 'multi-modal-landing-bucket', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      versioned: true
    });

    const lambda = new PythonFunction(this, 'lambda', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_11,
      entry: "lib/lambda",
      index: 'rek-bedrock.py',
      handler: 'lambda_handler',
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      environment: {
        PHOTO_BUCKET: bucket.bucketName,
        DYNAMODB_TABLE: 'restaurant-results-table'
      }
    });

    lambda.addEventSource(new S3EventSource(bucket, {
      events: [EventType.OBJECT_CREATED]
    }));

    bucket.grantReadWrite(lambda);
    // add permissions to the lambda function to access rekognition
    lambda.addToRolePolicy(new cdk.aws_iam.PolicyStatement({
      actions: ["rekognition:DetectText", "bedrock:InvokeModel"],
      resources: ["*"]
    }));

    const table = new cdk.aws_dynamodb.Table(this, 'restaurant-results-table', {
      tableName: 'restaurant-results-table',
      partitionKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST
    });

    // add permissions to the lambda function to access the dynamodb table
    table.grantFullAccess(lambda);

  }
}
