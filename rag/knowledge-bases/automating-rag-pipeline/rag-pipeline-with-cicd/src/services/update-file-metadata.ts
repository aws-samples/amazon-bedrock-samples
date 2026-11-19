import { DynamoDB } from 'aws-sdk';

const dynamodbClient = new DynamoDB.DocumentClient();
const tableName = process.env.FILE_METADATA_TABLE!;

export const handler = async (): Promise<string> => {
    try {
        // Step 1: Query for new files added (pending ingestion)
        const newFilesResult = await dynamodbClient.query({
            TableName: tableName,
            IndexName: 'fileType-kbIngestionStatus-index',
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
                ':PDF': 'PDF',
            },
        }).promise();

        if (newFilesResult.Items && newFilesResult.Items.length > 0) {
            console.log(`Found ${newFilesResult.Items.length} new items to update to 'complete'.`);

            // Step 2: Update the kbIngestionStatus to 'complete' for each matching item
            for (const item of newFilesResult.Items) {
                await updateKbIngestionStatus(item.fileId, item.fileType, 'complete');
            }
        } else {
            console.log('No new items found matching the filters.');
        }

        // Step 3: Query for deleted files that have kbIngestionStatus as 'complete'
        const deletedFilesResult = await dynamodbClient.query({
            TableName: tableName,
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

        if (deletedFilesResult.Items && deletedFilesResult.Items.length > 0) {
            console.log(`Found ${deletedFilesResult.Items.length} deleted items to update to 'removed'.`);

            // Step 4: Update the kbIngestionStatus to 'removed' for each matching item
            for (const item of deletedFilesResult.Items) {
                await updateKbIngestionStatus(item.fileId, item.fileType, 'removed');
            }
        } else {
            console.log('No deleted items found to update to "removed".');
        }

        //  Return a success message as JSON string
        return JSON.stringify({
            message: 'File metadata updated successfully',
        });
    } catch (error) {
        console.error('Error updating file metadata:', error);
        throw error;
    }
};

// Function to update the kbIngestionStatus to a specified status
async function updateKbIngestionStatus(fileId: string, fileType: string, status: string): Promise<void> {
    try {
        await dynamodbClient.update({
            TableName: tableName,
            Key: {
                fileId: fileId, // Partition key
                fileType: fileType, // Sort key
            },
            UpdateExpression: 'set #kbIngestionStatus = :status',
            ExpressionAttributeNames: {
                '#kbIngestionStatus': 'kbIngestionStatus',
            },
            ExpressionAttributeValues: {
                ':status': status,
            },
        }).promise();
        console.log(`Updated kbIngestionStatus to '${status}' for fileId: ${fileId}, fileType: ${fileType}`);
    } catch (error) {
        console.error(`Error updating kbIngestionStatus to '${status}':`, error);
        throw error;
    }
}
