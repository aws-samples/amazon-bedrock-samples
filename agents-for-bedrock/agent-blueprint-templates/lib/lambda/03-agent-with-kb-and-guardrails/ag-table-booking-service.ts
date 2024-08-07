import { DynamoDBClient, GetItemCommand, PutItemCommand, DeleteItemCommand, DescribeTableCommand, DeleteItemCommandInput } from "@aws-sdk/client-dynamodb";
// import { v4 as uuidv4 } from "uuid";

const ddbClient = new DynamoDBClient({});
const tableName = "BookingTable"; // TODO: Get the table name from Lambda environment variable


/**
 * Describes the DynamoDB table by sending a DescribeTableCommand.
 *
 * @returns The table description object if successful, or null if an error occurs.
 */

async function describeTable() {
    try {
        const response = await ddbClient.send(
            new DescribeTableCommand({
                TableName: tableName,
            })
        );
        console.log("Table description:", JSON.stringify(response, null, 2));
        return response.Table;
    } catch (err) {
        console.error("Error describing table:", err);
        return null;
    }
}

/**
 * Retrieves the booking details for the specified bookingId from the DynamoDB table.
 *
 * @param bookingId - The ID of the booking to retrieve.
 * @returns The booking details object if found, or an object containing a message if not found, or an error object if an error occurs.
 */
async function getBookingDetails(bookingId: string) {
    try {
        const response = await ddbClient.send(
            new GetItemCommand({
                "TableName": tableName,
                "Key": { "booking_id": { "S": bookingId } },
            })
        );

        if (response.Item) {
            console.log("Booking details:", response.Item);
            return response.Item;
        } else {
            console.log(`No booking found with ID ${bookingId}`);
            return { message: `No booking found with ID ${bookingId}` };
        }
    } catch (err) {
        console.error("Error getting booking details:", err);
        return {error: "Error getting booking details"};
    }
}


/**
 * Creates a new booking in the DynamoDB table with the provided details.
 *
 * @param date - The date for the booking.
 * @param name - The name of the customer.
 * @param hour - The hour for the booking.
 * @param numGuests - The number of guests for the booking.
 * @returns An object containing the bookingId if successful, or an error object if an error occurs.
 */
async function createBooking(date: string, name: string, hour: string, numGuests: number) {
    try {
        const bookingId = Math.floor(Math.random() * 1e8).toString().padStart(8, '0');
        // const bookingId = uuidv4().slice(0, 8);
        await ddbClient.send(
            new PutItemCommand({
                TableName: tableName,
                Item: {
                    booking_id: { S: bookingId },
                    date: { S: date },
                    name: { S: name },
                    hour: { S: hour },
                    num_guests: { N: numGuests.toString() },
                },
            })
        );
        console.log(`Table booked successfully for ${name} on ${date} at ${hour} for ${numGuests} guests. Your booking ID is ${bookingId}`);
        return { bookingId };
    } catch (err) {
        console.error("Error creating booking:", err);
        return { error: "Failed to book table" };
    }
}

/**
 * Deletes a booking from the DynamoDB table based on the provided bookingId.
 *
 * @param bookingId - The ID of the booking to delete.
 * @returns An object containing a success message if the booking is deleted, a failure message if the deletion fails, or an error object if an error occurs.
 */
async function deleteBooking(bookingId: string) {
    try {
        // Describe the table to get its schema for troubleshooting purpose
        const tableDescription = await describeTable();
        if (!tableDescription) {
            console.error(`Failed to describe table ${tableName}`);
            return { error: `Failed to describe table ${tableName}` };
        }

        const keySchema = tableDescription.KeySchema;
        console.log(`Table keySchema: ${JSON.stringify(keySchema)}`);

        console.log(`Deleting booking with ID ${bookingId}`);
        console.log(`tableName: ${tableName}`);

        const commandParams: DeleteItemCommandInput = {
            TableName: tableName,
            Key: {
                "booking_id": { S: bookingId },
            },
        };
        console.log(`Key: ${JSON.stringify(commandParams.Key)}`);

        const response = await ddbClient.send(new DeleteItemCommand(commandParams));

        if (response.$metadata.httpStatusCode === 200) {
            return { message: `Booking with ID ${bookingId} deleted successfully` };
        } else {
            return { message: `Failed to delete booking with ID ${bookingId} ` };
        }
    } catch (e) {
        console.error("Error deleting booking:", e);
        return { error: "Error deleting booking" };
    }
}

/**
 * Retrieves the value of a named parameter from the event object.
 *
 * @param event - The event object containing the parameters.
 * @param parameterName - The name of the parameter to retrieve.
 * @returns The value of the parameter if found, or undefined if not found.
 */
function getNamedParameter(event: any, parameterName: string) {
    const parameter = event.parameters.find((p: any) => p.name === parameterName);
    return parameter ? parameter.value : undefined;
}

/**
 * The main Lambda function handler that processes the incoming event and performs the appropriate action based on the provided function and parameters.
 *
 * @param event - The event object containing the action group, function, and parameters.
 * @param _context - The Lambda context object (unused in this implementation).
 * @returns The response object containing the action group, function, and function response.
 */

export const handler = async (event: any, _context: unknown) => {
    const actionGroup = event.actionGroup || "";
    const function_ = event.function || "";
    const parameters = event.parameters || [];

    console.log("Received event:", JSON.stringify(event, null, 2));
    console.log("Action group:", actionGroup);
    console.log("Function:", function_);
    console.log("Parameters:", JSON.stringify(parameters, null, 2));


    if (function_ === "get_booking_details") {
        const bookingId = getNamedParameter(event, "booking_id");
        console.log("Getting booking details for ID:", bookingId);
        if (bookingId) {
            const response = await getBookingDetails(bookingId);
            const responseBody = { TEXT: { body: JSON.stringify(response) } };
            return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
        } else {
            const responseBody = { TEXT: { body: "Missing booking_id parameter" } };
            return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
        }
    } else if (function_ === "create_booking") {
        const date = getNamedParameter(event, "date");
        const name = getNamedParameter(event, "name");
        const hour = getNamedParameter(event, "hour");
        const numGuests = getNamedParameter(event, "num_guests");

        console.log("date:", date);
        console.log("name:", name);
        console.log("hour:", hour);
        console.log("numGuests:", numGuests);

        console.log("Creating booking for:", name, "on", date, "at", hour, "for", numGuests, "guests");

        if (date && hour && numGuests) {
            const response = await createBooking(date, name || "", hour, Number(numGuests));
            const responseBody = { TEXT: { body: JSON.stringify(response) } };
            return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
        } else {
            const responseBody = { TEXT: { body: "Missing required parameters" } };
            return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
        }
    } else if (function_ === "delete_booking") {
        const bookingId = getNamedParameter(event, "booking_id");
        console.log("Deleting booking with ID:", bookingId);
        if (bookingId) {
            const response = await deleteBooking(bookingId);
            const responseBody = { TEXT: { body: JSON.stringify(response) } };
            return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
        } else {
            const responseBody = { TEXT: { body: "Missing booking_id parameter" } };
            return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
        }
    } else {
        const responseBody = { TEXT: { body: "Invalid function" } };
        return handleResponse(actionGroup, function_, responseBody, event.messageVersion);
    }
};


/**
 * Handles the response by creating an action response object with the provided information.
 *
 * @param actionGroup - The action group associated with the response.
 * @param function_ - The function associated with the response.
 * @param responseBody - The response body object.
 * @param messageVersion - The message version associated with the response.
 * @returns The function response object containing the action response and message version.
 */

function handleResponse(actionGroup: string, function_: string, responseBody: any, messageVersion: string) {
    const actionResponse = {
        actionGroup,
        function: function_,
        functionResponse: {
            responseBody,
        },
    };

    const functionResponse = { response: actionResponse, messageVersion };
    console.log("Response:", functionResponse);
    return functionResponse;
}


// function parseHour(hourString: string): number | undefined {
    //     const hourRegex = /^(\d{1,2}):(\d{2})$/;
    //     const match = hourString.match(hourRegex);
    
    //     if (!match) {
    //         console.error(`Invalid hour format: ${hourString}`);
    //         return undefined;
    //     }
    
    //     const [_, hours, minutes] = match.map(Number);
    //     const parsedHour = hours + (minutes / 60);
    
    //     if (parsedHour < 0 || parsedHour >= 24) {
    //         console.error(`Invalid hour value: ${parsedHour}`);
    //         return undefined;
    //     }
    
    //     return parsedHour;
    // }