import { DynamoDB } from "aws-sdk";

const dynamodbClient = new DynamoDB.DocumentClient();
const FILE_METADATA_TABLE = process.env.FILE_METADATA_TABLE;

// Lambda handler to check for file modifications (new files added or existing files deleted)
export const handler = async (): Promise<any> => {
    try {
        // Query the DynamoDB GSI for new files added
        const newFilesResult = await dynamodbClient.query({
            TableName: FILE_METADATA_TABLE as string,
            IndexName: 'fileType-kbIngestionStatus-index', // Specify the GSI name
            KeyConditionExpression: '#fileType = :processed and #kbIngestionStatus = :pending',
            FilterExpression: '#status = :active and #fileFormat = :PDF',
            ExpressionAttributeNames: {
                '#fileType': 'fileType',
                '#kbIngestionStatus': 'kbIngestionStatus',
                '#status': 'status',
                '#fileFormat': 'fileFormat',
            },
            ExpressionAttributeValues: {
                ':processed': 'processed',
                ':pending': 'pending',
                ':active': 'active',
                ':PDF': 'PDF', // Match the FilterExpression placeholder
            },
        }).promise();

        // Query the DynamoDB GSI for deleted files
        const deletedFilesResult = await dynamodbClient.query({
            TableName: FILE_METADATA_TABLE as string,
            IndexName: 'fileType-kbIngestionStatus-index',
            KeyConditionExpression: '#fileType = :processed and #kbIngestionStatus = :complete',
            FilterExpression: '#status = :deleted',
            ExpressionAttributeNames: {
                '#fileType': 'fileType',
                '#kbIngestionStatus': 'kbIngestionStatus',
                '#status': 'status',
            },
            ExpressionAttributeValues: {
                ':processed': 'processed',
                ':complete': 'complete',
                ':deleted': 'deleted',
            },
        }).promise();

        // Determine if there are any new files added or existing files deleted
        const modificationsExist = (newFilesResult.Items && newFilesResult.Items.length > 0) ||
            (deletedFilesResult.Items && deletedFilesResult.Items.length > 0);

        // Return true if any modifications (new additions or deletions) are found
        return {
            fileModificationsExist: modificationsExist,
        };
    } catch (error) {
        console.error('Error checking for file modifications for KB ingestion:', error);
        throw error;
    }
};
