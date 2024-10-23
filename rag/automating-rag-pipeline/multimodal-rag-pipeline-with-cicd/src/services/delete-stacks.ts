import { CloudFormation, S3 } from 'aws-sdk';

const regions = ['us-east-1', 'us-west-2'];  // TODO: Remove hardcoding

export const handler = async (event: any) => {
    console.log('Event:', event);

    // Perform the deletion in both regions
    const deletePromises = regions.map(region => deleteResourcesInRegion(region));

    // Wait for all deletions across both regions to complete
    await Promise.all(deletePromises);
    console.log('All delete requests across regions sent.');
};

// Function to delete stacks and S3 buckets in a specific region
const deleteResourcesInRegion = async (region: string) => {
    console.log(`Processing region: ${region}`);

    // Create CloudFormation and S3 clients for the specified region
    const cloudFormationClient = new CloudFormation({ region });
    const s3Client = new S3({ region });

    // Delete stacks
    await deleteStacksInRegion(cloudFormationClient, region);

    // Delete S3 buckets
    await deleteS3BucketsInRegion(s3Client, region);
};

// Function to delete stacks in a specific region
const deleteStacksInRegion = async (cloudFormationClient: CloudFormation, region: string) => {
    console.log(`Deleting stacks in region: ${region}`);

    const stacks = await cloudFormationClient.listStacks().promise();
    console.log(`Stacks in ${region}:`, stacks);

    // Filter stacks that start with 'QA-' or 'Prod-' and are not already deleted
    const appStacks = stacks.StackSummaries?.filter(stack =>
        (stack.StackName?.startsWith('QA') || stack.StackName?.startsWith('Prod')) || stack.StackName?.startsWith('PostQAApproval')
        && stack.StackStatus !== 'DELETE_COMPLETE'
    );

    console.log(`App Stacks in ${region}:`, appStacks);

    // Trigger deletion for all matching stacks in parallel in this region
    const deletePromises = appStacks!.map(stack => {
        console.log(`Initiating deletion for stack: ${stack.StackName} in region ${region}`);
        return deleteStackWithRetry(cloudFormationClient, stack.StackName!);
    });

    // Wait for all deletion operations to be initiated
    await Promise.all(deletePromises);
    console.log(`All delete requests sent for stacks in region: ${region}`);
};

// Function to delete S3 buckets in a specific region
const deleteS3BucketsInRegion = async (s3Client: S3, region: string) => {
    console.log(`Deleting S3 buckets in region: ${region}`);

    const buckets = await s3Client.listBuckets().promise();
    console.log(`Buckets:`, buckets);

    // Filter buckets that start with 'codepipelinestack'
    const targetBuckets = buckets.Buckets?.filter(bucket =>
        bucket.Name?.startsWith('codepipelinestack')
    );

    console.log(`Target Buckets in ${region}:`, targetBuckets);

    // Trigger deletion for all matching buckets in parallel in this region
    const deletePromises = targetBuckets!.map(bucket => {
        console.log(`Initiating deletion for bucket: ${bucket.Name} in region ${region}`);
        return deleteBucketWithRetry(s3Client, bucket.Name!);
    });

    // Wait for all deletion operations to be initiated
    await Promise.all(deletePromises);
    console.log(`All delete requests sent for buckets in region: ${region}`);
};

// Retry mechanism for deleting a stack
const deleteStackWithRetry = async (
    cloudFormationClient: CloudFormation,
    stackName: string,
    retries: number = 5,
    delay: number = 10000
) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            await cloudFormationClient.deleteStack({ StackName: stackName }).promise();
            console.log(`Delete request successfully sent for stack: ${stackName}`);

            // Wait for the stack to be deleted
            await waitForStackDeletion(cloudFormationClient, stackName);
            return; // Exit the loop if successful
        } catch (error) {
            console.error(`Attempt ${attempt} to delete stack ${stackName} failed:`, error);
            if (attempt < retries) {
                console.log(`Retrying in ${delay / 1000} seconds...`);
                await new Promise(resolve => setTimeout(resolve, delay)); // Wait before retrying
            } else {
                console.error(`Failed to delete stack ${stackName} after ${retries} attempts.`);
            }
        }
    }
};

// Function to wait for stack deletion
const waitForStackDeletion = async (cloudFormationClient: CloudFormation, stackName: string) => {
    while (true) {
        const stackStatus = await cloudFormationClient.describeStacks({ StackName: stackName }).promise();
        const status = stackStatus.Stacks?.[0].StackStatus;

        if (status === 'DELETE_COMPLETE') {
            console.log(`Stack ${stackName} successfully deleted.`);
            return;
        } else if (status === 'DELETE_FAILED') {
            throw new Error(`Failed to delete stack ${stackName}.`);
        } else {
            console.log(`Waiting for stack ${stackName} to be deleted. Current status: ${status}`);
            await new Promise(resolve => setTimeout(resolve, 10000)); // Wait before checking again
        }
    }
};

// Retry mechanism for deleting a bucket
const deleteBucketWithRetry = async (
    s3Client: S3,
    bucketName: string,
    retries: number = 5,
    delay: number = 10000
) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            // Empty the bucket before deleting
            const objects = await s3Client.listObjectsV2({ Bucket: bucketName }).promise();
            if (objects.Contents && objects.Contents.length > 0) {
                const deleteParams = {
                    Bucket: bucketName,
                    Delete: { Objects: objects.Contents.map(obj => ({ Key: obj.Key! })) }
                };
                await s3Client.deleteObjects(deleteParams).promise();
                console.log(`Deleted objects in bucket: ${bucketName}`);
            }

            await s3Client.deleteBucket({ Bucket: bucketName }).promise();
            console.log(`Delete request successfully sent for bucket: ${bucketName}`);
            return; // Exit the loop if successful
        } catch (error) {
            console.error(`Attempt ${attempt} to delete bucket ${bucketName} failed:`, error);
            if (attempt < retries) {
                console.log(`Retrying in ${delay / 1000} seconds...`);
                await new Promise(resolve => setTimeout(resolve, delay)); // Wait before retrying
            } else {
                console.error(`Failed to delete bucket ${bucketName} after ${retries} attempts.`);
            }
        }
    }
};