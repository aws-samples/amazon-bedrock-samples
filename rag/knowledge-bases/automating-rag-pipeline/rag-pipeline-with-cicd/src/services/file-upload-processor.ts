import { S3 } from 'aws-sdk';

const s3Client = new S3();


const handler = async (event: any): Promise<any> => {
    console.log('Event: ', event);


    // Access the environment variables
    const rawS3BucketARN = process.env.RAW_S3 as string;
    const processedS3BucketARN = process.env.PROCESSED_S3 as string;

    console.log('Raw S3 Bucket ARN: ', rawS3BucketARN);
    console.log('Processed S3 Bucket ARN: ', processedS3BucketARN);

    if (!rawS3BucketARN || !processedS3BucketARN) {
        console.error('Environment variables RAW_S3 and PROCESSED_S3 must be defined');
        return {
            statusCode: 400,
            body: JSON.stringify('Environment variables are not set.'),
        };
    }

    // Check if event.Records is defined and has at least one record
    if (!event.Records || event.Records.length === 0) {
        console.error('No records found in the event.');
        return {
            statusCode: 400,
            body: JSON.stringify('No records found in the event.'),
        };
    }

    // Extract bucket names from ARNs
    const rawS3Bucket = rawS3BucketARN.split(':').pop()!;
    const processedS3Bucket = processedS3BucketARN.split(':').pop()!;
    console.log('Raw S3 Bucket: ', rawS3Bucket);
    console.log('Processed S3 Bucket: ', processedS3Bucket);


    // Extract the file name and event type from the SQS message
    const record = event.Records[0];
    const messageBody = JSON.parse(record.body);
    console.log('Message Body: ', messageBody);
    const { fileName, eventType } = messageBody;

    // Check if the eventType is 'Object Created'
    if (eventType === 'Object Created') {
        console.log(`Processing file: ${fileName}`);
        // Copy the file from the raw S3 bucket to the processed S3 bucket
        console.log(`Copying file ${fileName} from ${rawS3Bucket} to ${processedS3Bucket}`);

        try {
            await s3Client.copyObject({
                Bucket: processedS3Bucket,
                CopySource: `${rawS3Bucket}/${fileName}`,
                Key: fileName,
            }).promise();

            console.log(`File ${fileName} copied successfully to ${processedS3Bucket}`);
        } catch (error) {
            console.error(`Error copying file ${fileName} to ${processedS3Bucket}: ${error}`);
            return {
                statusCode: 500,
                body: JSON.stringify(`Error copying file ${fileName} to ${processedS3Bucket}: ${error}`),
            };
        }
    } else if (eventType === 'Object Deleted') {
        console.log(`Deleting file: ${fileName}`);
        // Delete the file from the processed S3 bucket
        console.log(`Deleting file ${fileName} from ${processedS3Bucket}`);

        try {
            await s3Client.deleteObject({
                Bucket: processedS3Bucket,
                Key: fileName,
            }).promise();

            console.log(`File ${fileName} deleted successfully from ${processedS3Bucket}`);
        } catch (error) {
            console.error(`Error deleting file ${fileName} from ${processedS3Bucket}: ${error}`);
            return {
                statusCode: 500,
                body: JSON.stringify(`Error deleting file ${fileName} from ${processedS3Bucket}: ${error}`),
            };
        }

    } else {
        console.log(`Event type ${eventType} is not supported in file upload processor lambda.`);
        return {
            statusCode: 400,
            body: JSON.stringify(`Event type ${eventType} is not supported in file upload processor lambda.`),
        };
    }

    return {
        statusCode: 200,
        body: JSON.stringify("File upload processor Lambda executed successfully!"),
    };
}

export { handler }