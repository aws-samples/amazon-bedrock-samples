import { S3Event, S3Handler } from 'aws-lambda';
import { DynamoDB, S3 } from 'aws-sdk';

const dynamodbClient = new DynamoDB.DocumentClient();
const s3Client = new S3();
const tableName = process.env.FILE_METADATA_TABLE_NAME!;


export const handler: S3Handler = async (event: S3Event) => {
    console.log('Received S3 event:', JSON.stringify(event, null, 2));

    try {
        for (const record of event.Records) {
            const bucketName = record.s3.bucket.name;
            const objectKey = decodeURIComponent(record.s3.object.key.replace(/\+/g, ' '));
            const eventType = record.eventName;
            console.log(`Processing S3 event: ${eventType} for ${objectKey} in bucket ${bucketName}`);

            if (eventType.startsWith('ObjectRemoved')) {
                console.log(`Received ObjectRemoved event for ${objectKey} in bucket ${bucketName}`);
                // Update the status of the file to 'deleted' in DynamoDB
                await updateFileStatus(bucketName, objectKey, 'deleted');
            } else if (eventType.startsWith('ObjectCreated')) {

                const fileSize = record.s3.object.size;

                // Determine fileType based on the bucket name
                const fileType = bucketName.includes('raw-data-source') ? 'raw' : 'processed';
                console.log(`Checking ${fileType} file: ${objectKey} from bucket: ${bucketName}`);

                // Extract file format based on the file extension
                const fileFormat = getFileFormat(objectKey);
                console.log(`File format: ${fileFormat}`);

                // Check if the associated metadata file exists in S3
                const metadataFileKey = `${objectKey}.metadata.json`;
                const metadataExists = await checkMetadataFileExists(bucketName, metadataFileKey);

                // Determine the kbIngestionStatus based on the fileType
                const kbIngestionStatus = fileType === 'raw' ? 'not applicable' : 'pending';

                // Construct metadata to be saved in DynamoDB
                const fileMetadata = {
                    fileId: `${bucketName}/${objectKey}`, // Unique file identifier
                    fileType: fileType, // 'raw' or 'processed'
                    bucketName: bucketName,
                    fileName: objectKey,
                    fileSize: fileSize,
                    fileFormat: fileFormat, // File format (e.g., PDF, PPTX)
                    metadataFileExists: metadataExists, // Boolean indicating if associated metadata.json exists
                    lastModified: new Date().toISOString(),
                    status: 'active', // Status of the file (active, deleted), set the initial status to 'active'; when a new file is added, the status is set to 'active'
                    kbIngestionStatus: kbIngestionStatus, // Set based on fileType: 'not applicable' for raw, 'pending' for processed
                    ragEvaluationStatus: 'pending', // Status of the RAG evaluation (pending, passed, failed)
                    ragEvaluationTimestamp: '', // Timestamp when RAG evaluation was performed

                };

                // Save the metadata in DynamoDB
                await dynamodbClient.put({
                    TableName: tableName,
                    Item: fileMetadata,
                }).promise();
            }
        }
    } catch (error) {
        console.error('Error processing S3 event:', error);
        throw error;
    }
};

// Extracts file format from the file extension in the object key
function getFileFormat(objectKey: string): string {
    const extension = objectKey.split('.').pop() || '';
    switch (extension.toLowerCase()) {
        case 'pdf':
            return 'PDF';
        case 'ppt':
        case 'pptx':
            return 'PowerPoint';
        case 'doc':
        case 'docx':
            return 'Word Document';
        case 'xls':
        case 'xlsx':
            return 'Excel Spreadsheet';
        case 'csv':
            return 'CSV';
        case 'txt':
            return 'Text File';
        // Add more cases for other file formats as needed
        default:
            return 'Unknown';
    }
}

// Checks if the associated metadata file exists in the S3 bucket
async function checkMetadataFileExists(bucketName: string, metadataFileKey: string): Promise<boolean> {
    try {
        // Use headObject to check if the metadata file exists
        await s3Client.headObject({ Bucket: bucketName, Key: metadataFileKey }).promise();
        return true; // Metadata file exists
    } catch (error) {
        if ((error as any).code === 'NotFound') {
            return false; // Metadata file does not exist
        }
        console.error('Error checking metadata file:', error);
        throw error;
    }
}


// Updates the status of the file in DynamoDB
async function updateFileStatus(bucketName: string, objectKey: string, status: string): Promise<void> {
    try {
        // Determine fileType based on the bucket name
        const fileType = bucketName.includes('raw-data-source') ? 'raw' : 'processed';

        // Given your DynamoDB table schema, it uses a composite primary key consisting of a partition key fileId and a sort key fileType. Therefore, when you're performing any update, get, or delete operations on the items in this table, you must include both the fileId and fileType as part of the key.
        // Update DynamoDB with both partition key and sort key
        await dynamodbClient.update({
            TableName: tableName,
            Key: {
                fileId: `${bucketName}/${objectKey}`, // Partition key
                fileType: fileType, // Sort key
            },
            UpdateExpression: 'set #s = :status',
            ExpressionAttributeNames: { '#s': 'status' },
            ExpressionAttributeValues: { ':status': status },
        }).promise();
        console.log(`Updated status to '${status}' for fileId: ${bucketName}/${objectKey}, fileType: ${fileType}`);
    } catch (error) {
        console.error('Error updating file status:', error);
        throw error;
    }
}


// Updates the ingestionStatus of the file in DynamoDB
async function updateIngestionStatus(bucketName: string, objectKey: string, status: string): Promise<void> {
    const fileType = bucketName.includes('raw-data-source') ? 'raw' : 'processed';

    try {
        await dynamodbClient.update({
            TableName: tableName,
            Key: {
                fileId: `${bucketName}/${objectKey}`, // Partition key
                fileType: fileType, // Sort key
            },
            UpdateExpression: 'set ingestionStatus = :status',
            ExpressionAttributeValues: { ':status': status },
        }).promise();
        console.log(`Updated ingestionStatus to '${status}' for fileId: ${bucketName}/${objectKey}, fileType: ${fileType}`);
    } catch (error) {
        console.error('Error updating ingestion status:', error);
        throw error;
    }
}

