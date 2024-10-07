import { RemovalPolicy } from "aws-cdk-lib";
import { AttributeType, Billing, TableV2 } from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";

export class RestaurantAssistDatabaseStack extends Construct {
    constructor(scope: Construct, id: string) {
        super(scope, id);

        // Create a new DynamoDB table named 'BookingTable'
        new TableV2(this, 'BookingTable', {
            // Define the partition key as 'booking_id' with type string
            partitionKey: { name: 'booking_id', type: AttributeType.STRING },
            // Set the billing mode to on-demand
            billing: Billing.onDemand(),
            // Set the table name explicitly to 'BookingTable'
            tableName: 'BookingTable',
            // Set the removal policy to destroy the table when the stack is deleted
            removalPolicy: RemovalPolicy.DESTROY,
        });
    }
}


