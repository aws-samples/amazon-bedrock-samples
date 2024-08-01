var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// ../../../../../../../private/var/folders/tz/glqzblbd2ls0q126jlcf60080000gq/T/lambda-code-HthcY4/index.ts
var lambda_code_HthcY4_exports = {};
__export(lambda_code_HthcY4_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(lambda_code_HthcY4_exports);
var import_client_dynamodb = require("@aws-sdk/client-dynamodb");
var ddbClient = new import_client_dynamodb.DynamoDBClient({});
var tableName = "BookingTable";
async function describeTable() {
  try {
    const response = await ddbClient.send(
      new import_client_dynamodb.DescribeTableCommand({
        TableName: tableName
      })
    );
    console.log("Table description:", JSON.stringify(response, null, 2));
    return response.Table;
  } catch (err) {
    console.error("Error describing table:", err);
    return null;
  }
}
async function getBookingDetails(bookingId) {
  try {
    const response = await ddbClient.send(
      new import_client_dynamodb.GetItemCommand({
        "TableName": tableName,
        "Key": { "booking_id": { "S": bookingId } }
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
    return { error: "Error getting booking details" };
  }
}
async function createBooking(date, name, hour, numGuests) {
  try {
    const bookingId = Math.floor(Math.random() * 1e8).toString().padStart(8, "0");
    await ddbClient.send(
      new import_client_dynamodb.PutItemCommand({
        TableName: tableName,
        Item: {
          booking_id: { S: bookingId },
          date: { S: date },
          name: { S: name },
          hour: { S: hour },
          num_guests: { N: numGuests.toString() }
        }
      })
    );
    console.log(`Table booked successfully for ${name} on ${date} at ${hour} for ${numGuests} guests. Your booking ID is ${bookingId}`);
    return { bookingId };
  } catch (err) {
    console.error("Error creating booking:", err);
    return { error: "Failed to book table" };
  }
}
async function deleteBooking(bookingId) {
  try {
    const tableDescription = await describeTable();
    if (!tableDescription) {
      console.error(`Failed to describe table ${tableName}`);
      return { error: `Failed to describe table ${tableName}` };
    }
    const keySchema = tableDescription.KeySchema;
    console.log(`Table keySchema: ${JSON.stringify(keySchema)}`);
    console.log(`Deleting booking with ID ${bookingId}`);
    console.log(`tableName: ${tableName}`);
    const commandParams = {
      TableName: tableName,
      Key: {
        "booking_id": { S: bookingId }
      }
    };
    console.log(`Key: ${JSON.stringify(commandParams.Key)}`);
    const response = await ddbClient.send(new import_client_dynamodb.DeleteItemCommand(commandParams));
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
function getNamedParameter(event, parameterName) {
  const parameter = event.parameters.find((p) => p.name === parameterName);
  return parameter ? parameter.value : void 0;
}
var handler = async (event, _context) => {
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
function handleResponse(actionGroup, function_, responseBody, messageVersion) {
  const actionResponse = {
    actionGroup,
    function: function_,
    functionResponse: {
      responseBody
    }
  };
  const functionResponse = { response: actionResponse, messageVersion };
  console.log("Response:", functionResponse);
  return functionResponse;
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
