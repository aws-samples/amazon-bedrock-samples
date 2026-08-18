import { S3, DynamoDB } from 'aws-sdk';

const s3Client = new S3();
const dynamodbClient = new DynamoDB.DocumentClient({ region: 'us-east-1' });

export const handler = async (event: any): Promise<any> => {
    console.log("Event: ", event);

    const rawS3BucketQA = process.env.RAW_S3_QA as string;
    const rawS3BucketProd = process.env.RAW_S3_PROD as string;
    const tableName = process.env.FILE_METADATA_TABLE_NAME as string;

    console.log('Raw S3 Bucket (QA):', rawS3BucketQA);
    console.log('Raw S3 Bucket (Prod):', rawS3BucketProd);
    console.log('File Metadata Table:', tableName);

    if (!rawS3BucketQA || !rawS3BucketProd || !tableName) {
        console.error('Required environment variables are missing.');
        return {
            statusCode: 400,
            body: JSON.stringify('Required environment variables are missing.'),
        };
    }

    try {
        // Step 1: Query DynamoDB for files with ragEvaluationStatus = 'PASSED'
        const passedFiles = await getPassedFilesFromDynamoDB(tableName);
        console.log(`Found ${passedFiles.length} files with RAG status 'PASSED'.`);

        const passedFileSet = new Set(passedFiles.map(file => file.fileId.split('/').pop()));

        // Step 2: List objects in the QA bucket
        const listObjectsResponseQA = await s3Client
            .listObjectsV2({ Bucket: rawS3BucketQA })
            .promise();

        // Step 3: List objects in the Prod bucket
        const listObjectsResponseProd = await s3Client
            .listObjectsV2({ Bucket: rawS3BucketProd })
            .promise();

        const prodObjectsMap = new Map<string, string>();
        if (listObjectsResponseProd.Contents) {
            for (const object of listObjectsResponseProd.Contents) {
                if (object.Key && object.ETag) {
                    prodObjectsMap.set(object.Key, object.ETag);
                }
            }
        }

        // If QA bucket is empty, delete all files from Prod bucket
        if (!listObjectsResponseQA.Contents || listObjectsResponseQA.Contents.length === 0) {
            console.log('QA bucket is empty. Deleting all objects from Prod bucket...');
            await deleteAllObjectsFromProd(listObjectsResponseProd.Contents || []);
            return {
                statusCode: 200,
                body: JSON.stringify('QA bucket is empty. All objects deleted from Prod bucket.'),
            };
        }

        // Create a set of all file names in the QA bucket
        const qaFileSet = new Set<string>(
            listObjectsResponseQA.Contents.map(object => object.Key!)
        );

        // Step 4: Copy only the 'PASSED' files from QA to Prod if needed
        for (const object of listObjectsResponseQA.Contents) {
            if (object.Key && object.ETag && passedFileSet.has(object.Key)) {
                const prodETag = prodObjectsMap.get(object.Key);

                if (!prodETag || prodETag !== object.ETag) {
                    const copyObjectParams: S3.CopyObjectRequest = {
                        Bucket: rawS3BucketProd,
                        CopySource: `${rawS3BucketQA}/${object.Key}`,
                        Key: object.Key,
                    };

                    console.log(`Copying object ${object.Key} from QA to Prod...`);
                    await s3Client.copyObject(copyObjectParams).promise();
                    console.log(`Object ${object.Key} copied successfully.`);
                } else {
                    console.log(`Object ${object.Key} already exists in Prod with the same content. Skipping...`);
                }
            }
        }

        // Step 5: Delete files from Prod that are not in QA bucket
        for (const object of listObjectsResponseProd.Contents || []) {
            if (object.Key && !qaFileSet.has(object.Key)) {
                const deleteObjectParams: S3.DeleteObjectRequest = {
                    Bucket: rawS3BucketProd,
                    Key: object.Key,
                };

                console.log(`Deleting object ${object.Key} from Prod bucket...`);
                await s3Client.deleteObject(deleteObjectParams).promise();
                console.log(`Object ${object.Key} deleted successfully from Prod.`);
            }
        }

        return {
            statusCode: 200,
            body: JSON.stringify('Objects synchronized successfully between QA and Prod.'),
        };
    } catch (error) {
        console.error('Error synchronizing objects:', error);
        return {
            statusCode: 500,
            body: JSON.stringify('Error synchronizing objects.'),
        };
    }
};

// Function to query DynamoDB for files with ragEvaluationStatus = 'PASSED'
async function getPassedFilesFromDynamoDB(tableName: string): Promise<any[]> {
    const params = {
        TableName: tableName,
        FilterExpression: 'ragEvaluationStatus = :status',
        ExpressionAttributeValues: {
            ':status': 'PASSED',
        },
    };

    const result = await dynamodbClient.scan(params).promise();
    return result.Items || [];
}

// Function to delete all objects from the Prod bucket
async function deleteAllObjectsFromProd(objects: S3.ObjectList) {
    const deleteParams: S3.DeleteObjectsRequest = {
        Bucket: process.env.RAW_S3_PROD as string,
        Delete: {
            Objects: objects.map(object => ({ Key: object.Key! })),
        },
    };

    if (deleteParams.Delete.Objects.length > 0) {
        console.log('Deleting all objects from Prod bucket...');
        await s3Client.deleteObjects(deleteParams).promise();
        console.log('All objects deleted from Prod bucket.');
    } else {
        console.log('No objects to delete from Prod bucket.');
    }
}