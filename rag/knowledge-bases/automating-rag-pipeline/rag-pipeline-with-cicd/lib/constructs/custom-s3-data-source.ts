import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import { aws_bedrock as bedrockL1 } from 'aws-cdk-lib';
import { IBucket } from 'aws-cdk-lib/aws-s3';
import { IFunction } from 'aws-cdk-lib/aws-lambda';

export interface CustomS3DataSourceProps extends bedrock.S3DataSourceProps {
    intermediateBucket: IBucket;
    transformationLambda: IFunction;
}

export class CustomS3DataSource extends Construct {
    public readonly dataSourceId: string;

    constructor(scope: Construct, id: string, props: CustomS3DataSourceProps) {
        super(scope, id);

        const customTransformationConfiguration = {
            intermediateStorage: {
                s3Location: {
                    uri: `s3://${props.intermediateBucket.bucketName}/`
                }
            },
            transformations: [
                {
                    stepToApply: 'POST_CHUNKING', // Custom chunking logic applied after files are processed by Bedrock
                    transformationFunction: {
                        transformationLambdaConfiguration: {
                            lambdaArn: props.transformationLambda.functionArn // Custom Lambda function for chunking, and other transformations
                        }
                    }
                }
            ]
        };

        // Use 'NONE' chunking strategy so Bedrock treats each file as a chunk
        const kbS3DataSource = new bedrockL1.CfnDataSource(this, 'MyCfnDataSource', {
            knowledgeBaseId: props.knowledgeBase.knowledgeBaseId,
            name: props.dataSourceName,
            dataSourceConfiguration: {
                type: 'S3',
                s3Configuration: {
                    bucketArn: props.bucket.bucketArn,
                },
            },
            vectorIngestionConfiguration: {
                chunkingConfiguration: {
                    chunkingStrategy: 'NONE', // Use 'NONE' since custom chunking is handled by the Lambda function
                },
                customTransformationConfiguration,
            }
        });

        // attrDataSourceId is a property of the CfnDataSource construct that represents the unique identifier of the data source
        // Extract the dataSourceId from the CfnDataSource construct and assign it to the dataSourceId property of the CustomS3DataSource construct
        // Thats why 'this' is used to refer to the current instance of the CustomS3DataSource construct
        this.dataSourceId = kbS3DataSource.attrDataSourceId;  // Expose the dataSourceId as a public property
    }
}
