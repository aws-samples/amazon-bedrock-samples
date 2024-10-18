import { S3 } from 'aws-sdk';

const s3Client = new S3();

export const handler = async (event: any): Promise<any> => {

    console.log("Event: ", event);
    // Access the environment variables
    // const rawS3BucketQA = process.env.PROCESSED_S3_QA as string;
    // const rawS3BucketProd = process.env.PROCESSED_S3_PROD as string;

    const rawS3BucketQA = process.env.RAW_S3_QA as string;
    const rawS3BucketProd = process.env.RAW_S3_PROD as string;

    console.log('Raw S3 Bucket QA: ', rawS3BucketQA);
    console.log('Raw S3 Bucket Prod: ', rawS3BucketProd);

    if (!rawS3BucketQA || !rawS3BucketProd) {
        console.error('Required environment variables are missing.');
        return {
            statusCode: 400,
            body: JSON.stringify('Required environment variables are missing.'),
        };
    }

    try {
        // List all objects in the QA bucket
        const listObjectsParamsQA: S3.ListObjectsV2Request = {
            Bucket: rawS3BucketQA
        };

        const listObjectsResponseQA = await s3Client.listObjectsV2(listObjectsParamsQA).promise();

        if (!listObjectsResponseQA.Contents || listObjectsResponseQA.Contents.length === 0) {
            console.log('No objects found in the QA bucket.');
            return {
                statusCode: 200,
                body: JSON.stringify('No objects found in the QA bucket.'),
            };
        }

        // List all objects in the Prod bucket
        const listObjectsParamsProd: S3.ListObjectsV2Request = {
            Bucket: rawS3BucketProd
        };

        const listObjectsResponseProd = await s3Client.listObjectsV2(listObjectsParamsProd).promise();
        const prodObjectsMap = new Map<string, string>();

        // Build a map of keys and ETags for objects in the Prod bucket
        if (listObjectsResponseProd.Contents) {
            for (const object of listObjectsResponseProd.Contents) {
                if (object.Key && object.ETag) {
                    prodObjectsMap.set(object.Key, object.ETag);
                }
            }
        }

        // Create a set of all the file names in the QA bucket for easy comparison
        const qaFileSet = new Set<string>();
        for (const object of listObjectsResponseQA.Contents) {
            if (object.Key) {
                qaFileSet.add(object.Key);
            }
        }

        // Iterate over each object in the QA bucket and copy it to the Prod bucket if it doesn't exist or has different content
        for (const object of listObjectsResponseQA.Contents) {
            if (object.Key && object.ETag) {
                const prodETag = prodObjectsMap.get(object.Key);

                // Copy the object only if it does not exist in Prod or if the ETags (checksums) are different
                if (!prodETag || prodETag !== object.ETag) {
                    const copyObjectParams: S3.CopyObjectRequest = {
                        Bucket: rawS3BucketProd,
                        CopySource: `${rawS3BucketQA}/${object.Key}`, // The source object key from the QA bucket
                        Key: object.Key, // Copy to the same key in the Prod bucket
                    };

                    console.log(`Copying object ${object.Key} from QA to Prod bucket...`);

                    await s3Client.copyObject(copyObjectParams).promise();
                    console.log(`Object ${object.Key} copied successfully.`);
                } else {
                    console.log(`Object ${object.Key} already exists in Prod with the same content. Skipping...`);
                }
            }
        }

        // Delete objects in the Prod bucket that are not present in the QA bucket
        for (const object of listObjectsResponseProd.Contents || []) {
            if (object.Key && !qaFileSet.has(object.Key)) {
                const deleteObjectParams: S3.DeleteObjectRequest = {
                    Bucket: rawS3BucketProd,
                    Key: object.Key
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
