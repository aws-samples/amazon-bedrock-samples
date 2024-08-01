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

// ../../../../../../../private/var/folders/tz/glqzblbd2ls0q126jlcf60080000gq/T/lambda-code-cLD6aA/index.ts
var lambda_code_cLD6aA_exports = {};
__export(lambda_code_cLD6aA_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(lambda_code_cLD6aA_exports);
var import_client_rds_data = require("@aws-sdk/client-rds-data");
var rdsClient = new import_client_rds_data.RDSDataClient({});
var databaseName = "employeedatabase";
function prepareResponse(resultText, actionGroup, func) {
  const responseBody = {
    TEXT: {
      body: resultText
    }
  };
  const action_response = {
    actionGroup,
    function: func,
    functionResponse: {
      responseBody
    }
  };
  const entire_function_response = {
    response: action_response
  };
  return entire_function_response;
}
async function getAvailableVacationsDays(employeeId, dbClusterArn, dbCredentialsSecretsStoreArn) {
  if (!employeeId) {
    return Promise.reject(new Error("Employee ID is required"));
  }
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
    parameters: [
      {
        name: "employeeId",
        value: { longValue: employeeId }
      }
    ]
  });
  try {
    const response = await rdsClient.send(sqlCommand);
    const records = response.records;
    if (records && records.length > 0) {
      const availableVacationDays = records[0][0].longValue;
      console.log(`Available vacation days for employee ID ${employeeId}: ${availableVacationDays}`);
      const returnMsg = `Available vacation days for employee ID ${employeeId}: ${availableVacationDays}`;
      return returnMsg;
    } else {
      const returnMsg = `No vacation data found for employee ID ${employeeId}`;
      console.log(returnMsg);
      return returnMsg;
    }
  } catch (error) {
    console.error("Error fetching available vacation days:", error);
    throw error;
  }
}
async function reserveVacationTime(employeeId, startDate, endDate, dbClusterArn, dbCredentialsSecretsStoreArn) {
  let vacationDays;
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
    try {
      if (start === null || end === null) {
        const returnMsg2 = "Invalid date format. Please provide dates in the format YYYY-MM-DD.";
        console.log(returnMsg2);
        return returnMsg2;
      } else {
        console.log(`Start date: ${start}, End date: ${end}`);
        const vacationDays3 = Math.ceil((end.getTime() - start.getTime()) / (1e3 * 60 * 60 * 24)) + 1;
        console.log(`Number of vacation days calculated within the reserveVacationTime function: ${vacationDays3}`);
        const currentYear2 = start.getFullYear();
        console.log(`Current year: ${currentYear2}`);
      }
    } catch (error) {
      console.error("Error converting date strings to Date objects:", error);
      throw error;
    }
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
      try {
        const employeeName = checkEmployeeResponse.records[0][1].stringValue;
        console.log(`Employee with ID ${employeeId} and name ${employeeName} exists.`);
      } catch (error) {
        console.error("Error checking employee existence:", error);
        throw error;
      }
    }
    const checkAvailableDaysQuery = "SELECT employee_vacation_days_available FROM vacationsTable WHERE employee_id = :employeeId AND year = :year";
    console.log("Checking available vacation days...");
    const currentYear = start.getFullYear();
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
    const vacationDays2 = Math.ceil((end.getTime() - start.getTime()) / (1e3 * 60 * 60 * 24)) + 1;
    if (!checkAvailableDaysResponse.records || checkAvailableDaysResponse.records.length === 0) {
      const returnMsg2 = `No vacation data found for employee with ID ${employeeId} in the current year.`;
      console.log(returnMsg2);
      return returnMsg2;
    } else {
      try {
        const availableDaysRecord = checkAvailableDaysResponse.records[0][0];
        if (!availableDaysRecord || !availableDaysRecord.longValue) {
          console.error("Error: Invalid response format for available vacation days");
          throw new Error("Invalid response format for available vacation days");
        }
        const availableDays = availableDaysRecord.longValue;
        console.log(`Available vacation days for employee with ID ${employeeId} in ${currentYear}: ${availableDays}`);
        if (availableDays < vacationDays2) {
          const returnMsg2 = `Employee with ID ${employeeId} does not have enough vacation days available for the requested period.`;
          console.log(returnMsg2);
          return returnMsg2;
        }
      } catch (error) {
        console.error("Error checking available vacation days:", error);
        throw error;
      }
    }
    const insertVacationQuery = "INSERT INTO plannedVacationsTable (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (:employeeId, to_date(:startDate, 'YYYY-MM-DD'), to_date(:endDate, 'YYYY-MM-DD'), :vacationDays)";
    console.log("Inserting the new vacation information...");
    let formattedStartDate, formattedEndDate;
    try {
      const startDateObj = new Date(startDate);
      const endDateObj = new Date(endDate);
      if (isNaN(startDateObj.getTime()) || isNaN(endDateObj.getTime())) {
        console.error("Invalid date format in input strings");
        throw new Error("Invalid date format");
      }
      formattedStartDate = startDateObj.toISOString().slice(0, 10);
      formattedEndDate = endDateObj.toISOString().slice(0, 10);
      console.log("Formatted start date:", formattedStartDate);
      console.log("Formatted end date:", formattedEndDate);
    } catch (error) {
      console.error("Error inferring dates:", error);
      throw error;
    }
    const insertVacationCommand = new import_client_rds_data.ExecuteStatementCommand({
      resourceArn: dbClusterArn,
      secretArn: dbCredentialsSecretsStoreArn,
      sql: insertVacationQuery,
      database: databaseName,
      parameters: [
        { name: "employeeId", value: { longValue: employeeId } },
        { name: "startDate", value: { stringValue: formattedStartDate } },
        { name: "endDate", value: { stringValue: formattedEndDate } },
        { name: "vacationDays", value: { longValue: vacationDays2 } }
      ]
    });
    const actualQuery = insertVacationCommand.input?.sql;
    if (actualQuery) {
      const actualQueryWithValues = actualQuery.replace(/\$\([^\)]+\)/g, (match) => {
        const parameterName = match.slice(2, -1);
        const parameterValue = insertVacationCommand.input.parameters?.find(
          (param) => param.name === parameterName
        )?.value;
        if (parameterValue) {
          if (parameterValue.stringValue) {
            return `'${parameterValue.stringValue}'`;
          } else if (parameterValue.longValue) {
            return parameterValue.longValue.toString();
          }
        }
        return match;
      });
      console.log("Actual insertVacationQuery:", actualQueryWithValues);
    } else {
      console.log("insertVacationQuery is undefined");
    }
    await rdsClient.send(insertVacationCommand);
    const updateVacationsQuery = "UPDATE vacationsTable SET employee_vacation_days_taken = employee_vacation_days_taken + :vacationDays, employee_vacation_days_available = employee_vacation_days_available - :vacationDays WHERE employee_id = :employeeId AND year = :year";
    console.log("Updating the vacations table...");
    const updateVacationsCommand = new import_client_rds_data.ExecuteStatementCommand({
      resourceArn: dbClusterArn,
      secretArn: dbCredentialsSecretsStoreArn,
      sql: updateVacationsQuery,
      database: databaseName,
      parameters: [
        { name: "vacationDays", value: { longValue: vacationDays2 } },
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
async function handleRequest(actionGroup, func, parameters, dbClusterArn, dbCredentialsSecretsStoreArn) {
  if (func === "get_available_vacation_days") {
    let employeeId = null;
    for (const param of parameters) {
      if (param.name === "employee_id") {
        employeeId = parseInt(param.value, 10);
        break;
      }
    }
    if (employeeId === null) {
      throw new Error("Error: employee_id parameter is missing");
    }
    const vacationDaysReturnMsg = await getAvailableVacationsDays(employeeId, dbClusterArn, dbCredentialsSecretsStoreArn);
    console.log("vacationDaysReturnMsg:", vacationDaysReturnMsg);
    return prepareResponse(vacationDaysReturnMsg, actionGroup, func);
  } else if (func === "reserve_vacation_time") {
    let employeeId = null;
    let startDate = null;
    let endDate = null;
    for (const param of parameters) {
      if (param.name === "employee_id") {
        employeeId = parseInt(param.value, 10);
      } else if (param.name === "start_date") {
        startDate = param.value;
      } else if (param.name === "end_date") {
        endDate = param.value;
      }
    }
    if (employeeId === null || startDate === null || endDate === null) {
      throw new Error("Error: employee_id, start_date, and end_date parameters are required");
    }
    console.log("Extracted parameters:", "employeeId:", employeeId, "startDate:", startDate, "endDate:", endDate);
    const reservationReturnMsg = await reserveVacationTime(employeeId, startDate, endDate, dbClusterArn, dbCredentialsSecretsStoreArn);
    console.log("reservationReturnMsg:", reservationReturnMsg);
    return prepareResponse(reservationReturnMsg, actionGroup, func);
  } else {
    return prepareResponse("Error, no function was called", actionGroup, func);
  }
}
var handler = async (event, context) => {
  console.log("Received event:", JSON.stringify(event, null, 2));
  console.log("Received context:", JSON.stringify(context, null, 2));
  const dbCredentialsSecretsStoreArn = process.env.SECRET_ARN;
  const dbClusterArn = process.env.CLUSTER_ARN;
  const { agent, actionGroup, function: func, parameters = [], messageVersion } = event;
  console.log("function:", func);
  console.log("Received parameters:", JSON.stringify(parameters, null, 2));
  const finalResponse = await handleRequest(actionGroup, func, parameters, dbClusterArn, dbCredentialsSecretsStoreArn);
  console.log("finalResponse:", JSON.stringify(finalResponse, null, 2));
  return finalResponse;
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
