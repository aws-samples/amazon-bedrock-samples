"use strict";
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

// lib/lambda/02-agent-with-return-of-control/assist-with-vacation-lambda.ts
var assist_with_vacation_lambda_exports = {};
__export(assist_with_vacation_lambda_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(assist_with_vacation_lambda_exports);
var import_client_rds_data = require("@aws-sdk/client-rds-data");
var rdsClient = new import_client_rds_data.RDSDataClient({});
var databaseName = "employeedatabase";
async function getAvailableVacationsDays(employeeId, dbClusterArn, dbCredentialsSecretsStoreArn) {
  const sql = `
        SELECT employee_vacation_days_available
        FROM vacationsTable
        WHERE employee_id = :employeeId
        ORDER BY year DESC
        LIMIT 1
    `;
  const sqlCommand = new import_client_rds_data.ExecuteStatementCommand({
    resourceArn: dbClusterArn,
    secretArn: dbCredentialsSecretsStoreArn,
    sql,
    database: databaseName,
    parameters: [{ name: "employeeId", value: { longValue: employeeId } }]
  });
  try {
    console.log("Executing SQL command:", sqlCommand);
    const response = await rdsClient.send(sqlCommand);
    console.log("SQL command response:", response);
    const records = response.records;
    if (records && records.length > 0) {
      const availableVacationDays = records[0][0].longValue;
      return `Available vacation days for employee ID ${employeeId}: ${availableVacationDays}`;
    } else {
      return `No vacation data found for employee ID ${employeeId}`;
    }
  } catch (error) {
    console.error("Error fetching available vacation days:", error);
    throw error;
  }
}
async function reserveVacationTime(employeeId, startDate, endDate, dbClusterArn, dbCredentialsSecretsStoreArn) {
  function convertStringToDate(dateString) {
    const parsedDate = Date.parse(dateString);
    if (isNaN(parsedDate)) {
      console.error(`Invalid date string: ${dateString}`);
      return null;
    }
    const date = new Date(parsedDate);
    const formattedDate = date.toISOString().slice(0, 10);
    return formattedDate;
  }
  try {
    const convertedStartDate = convertStringToDate(startDate);
    const convertedEndDate = convertStringToDate(endDate);
    const start = convertedStartDate !== null ? new Date(convertedStartDate) : null;
    const end = convertedEndDate !== null ? new Date(convertedEndDate) : null;
    if (start === null || end === null) {
      const returnMsg2 = "Invalid date format. Please provide dates in the format YYYY-MM-DD.";
      console.log(returnMsg2);
      return returnMsg2;
    }
    console.log(`Start date: ${start}, End date: ${end}`);
    const vacationDays = Math.ceil((end.getTime() - start.getTime()) / (1e3 * 60 * 60 * 24)) + 1;
    console.log(`Number of vacation days calculated within the reserveVacationTime function: ${vacationDays}`);
    const currentYear = start.getFullYear();
    console.log(`Current year: ${currentYear}`);
    const checkEmployeeQuery = "SELECT * FROM employeesTable WHERE employee_id = :employeeId";
    console.log("Checking if the employee exists...");
    const checkEmployeeCommand = new import_client_rds_data.ExecuteStatementCommand({
      resourceArn: dbClusterArn,
      secretArn: dbCredentialsSecretsStoreArn,
      sql: checkEmployeeQuery,
      database: databaseName,
      parameters: [{ name: "employeeId", value: { longValue: employeeId } }]
    });
    const checkEmployeeResponse = await rdsClient.send(checkEmployeeCommand);
    if (!checkEmployeeResponse.records || checkEmployeeResponse.records.length === 0) {
      const returnMsg2 = `Employee with ID ${employeeId} does not exist.`;
      console.log(returnMsg2);
      return returnMsg2;
    } else {
      const employeeName = checkEmployeeResponse.records[0][1].stringValue;
      console.log(`Employee with ID ${employeeId} and name ${employeeName} exists.`);
    }
    const checkAvailableDaysQuery = "SELECT employee_vacation_days_available FROM vacationsTable WHERE employee_id = :employeeId AND year = :year";
    console.log("Checking available vacation days...");
    const checkAvailableDaysCommand = new import_client_rds_data.ExecuteStatementCommand({
      resourceArn: dbClusterArn,
      secretArn: dbCredentialsSecretsStoreArn,
      sql: checkAvailableDaysQuery,
      database: databaseName,
      parameters: [
        { name: "employeeId", value: { longValue: employeeId } },
        { name: "year", value: { longValue: currentYear } }
      ]
    });
    const checkAvailableDaysResponse = await rdsClient.send(checkAvailableDaysCommand);
    if (!checkAvailableDaysResponse.records || checkAvailableDaysResponse.records.length === 0) {
      const returnMsg2 = `No vacation data found for employee with ID ${employeeId} in the current year.`;
      console.log(returnMsg2);
      return returnMsg2;
    } else {
      const availableDaysRecord = checkAvailableDaysResponse.records[0][0];
      if (!availableDaysRecord || !availableDaysRecord.longValue) {
        console.error("Error: Invalid response format for available vacation days");
        throw new Error("Invalid response format for available vacation days");
      }
      const availableDays = availableDaysRecord.longValue;
      console.log(`Available vacation days for employee with ID ${employeeId} in ${currentYear}: ${availableDays}`);
      if (availableDays < vacationDays) {
        const returnMsg2 = `Employee with ID ${employeeId} does not have enough vacation days available for the requested period.`;
        console.log(returnMsg2);
        return returnMsg2;
      }
    }
    const insertVacationQuery = "INSERT INTO plannedVacationsTable (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (:employeeId, to_date(:startDate, 'YYYY-MM-DD'), to_date(:endDate, 'YYYY-MM-DD'), :vacationDays)";
    console.log("Inserting the new vacation information...");
    const formattedStartDate = start.toISOString().slice(0, 10);
    const formattedEndDate = end.toISOString().slice(0, 10);
    console.log("Formatted start date:", formattedStartDate);
    console.log("Formatted end date:", formattedEndDate);
    const insertVacationCommand = new import_client_rds_data.ExecuteStatementCommand({
      resourceArn: dbClusterArn,
      secretArn: dbCredentialsSecretsStoreArn,
      sql: insertVacationQuery,
      database: databaseName,
      parameters: [
        { name: "employeeId", value: { longValue: employeeId } },
        { name: "startDate", value: { stringValue: formattedStartDate } },
        { name: "endDate", value: { stringValue: formattedEndDate } },
        { name: "vacationDays", value: { longValue: vacationDays } }
      ]
    });
    await rdsClient.send(insertVacationCommand);
    const updateVacationsQuery = "UPDATE vacationsTable SET employee_vacation_days_taken = employee_vacation_days_taken + :vacationDays, employee_vacation_days_available = employee_vacation_days_available - :vacationDays WHERE employee_id = :employeeId AND year = :year";
    console.log("Updating the vacations table...");
    const updateVacationsCommand = new import_client_rds_data.ExecuteStatementCommand({
      resourceArn: dbClusterArn,
      secretArn: dbCredentialsSecretsStoreArn,
      sql: updateVacationsQuery,
      database: databaseName,
      parameters: [
        { name: "vacationDays", value: { longValue: vacationDays } },
        { name: "employeeId", value: { longValue: employeeId } },
        { name: "year", value: { longValue: currentYear } }
      ]
    });
    await rdsClient.send(updateVacationsCommand);
    const returnMsg = `Vacation saved successfully for employee with ID ${employeeId} from ${startDate} to ${endDate}.`;
    console.log(returnMsg);
    return returnMsg;
  } catch (error) {
    console.error("Error occurred with reserveVacationTime:", error);
    throw error;
  }
}
async function handleRequest(func, parameters, dbClusterArn, dbCredentialsSecretsStoreArn) {
  console.log("Handling request for function:", func, "with parameters:", parameters);
  if (func === "get_available_vacation_days") {
    const employeeIdParam = parameters.find((param) => param.name === "employee_id");
    if (!employeeIdParam || !employeeIdParam.value) {
      const errorMessage = "Error: employee_id parameter is missing";
      console.error(errorMessage);
      throw new Error(errorMessage);
    }
    const employeeId = parseInt(employeeIdParam.value, 10);
    return getAvailableVacationsDays(employeeId, dbClusterArn, dbCredentialsSecretsStoreArn);
  } else if (func === "reserve_vacation_time") {
    const employeeIdParam = parameters.find((param) => param.name === "employee_id");
    const startDateParam = parameters.find((param) => param.name === "start_date");
    const endDateParam = parameters.find((param) => param.name === "end_date");
    if (!employeeIdParam || !employeeIdParam.value || !startDateParam || !startDateParam.value || !endDateParam || !endDateParam.value) {
      const errorMessage = "Error: employee_id, start_date, and end_date parameters are required";
      console.error(errorMessage);
      throw new Error(errorMessage);
    }
    const employeeId = parseInt(employeeIdParam.value, 10);
    const startDate = startDateParam.value;
    const endDate = endDateParam.value;
    return reserveVacationTime(employeeId, startDate, endDate, dbClusterArn, dbCredentialsSecretsStoreArn);
  } else {
    const errorMessage = "Error, no function was called";
    console.error(errorMessage);
    return errorMessage;
  }
}
async function handler(event) {
  const dbClusterArn = process.env.CLUSTER_ARN;
  const dbCredentialsSecretsStoreArn = process.env.SECRET_ARN;
  try {
    if (event.httpMethod === "GET") {
      const employeeId = parseInt(event.queryStringParameters?.employee_id || "0", 10);
      if (!employeeId) {
        return {
          statusCode: 400,
          body: JSON.stringify({ message: "employee_id query parameter is required" })
        };
      }
      const result = await getAvailableVacationsDays(employeeId, dbClusterArn, dbCredentialsSecretsStoreArn);
      return {
        statusCode: 200,
        body: JSON.stringify({ message: result })
      };
    } else if (event.httpMethod === "POST") {
      const body = JSON.parse(event.body || "{}");
      const func = body.func;
      const parameters = body.parameters;
      if (!func || !parameters) {
        return {
          statusCode: 400,
          body: JSON.stringify({ message: "func and parameters are required in the body" })
        };
      }
      const result = await handleRequest(func, parameters, dbClusterArn, dbCredentialsSecretsStoreArn);
      return {
        statusCode: 200,
        body: JSON.stringify({ message: result })
      };
    } else {
      return {
        statusCode: 405,
        body: JSON.stringify({ message: "Method Not Allowed" })
      };
    }
  } catch (error) {
    console.error("Error handling request:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Internal Server Error" })
    };
  }
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
