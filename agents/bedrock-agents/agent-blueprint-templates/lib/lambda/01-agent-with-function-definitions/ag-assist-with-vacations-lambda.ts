import { Context, Handler } from "aws-lambda";
import { RDSDataClient, ExecuteStatementCommand } from "@aws-sdk/client-rds-data";

const rdsClient = new RDSDataClient({});
const databaseName = 'employeedatabase';

interface Parameter {
    name: string;
    stringValue?: string;
    longValue?: number;
}

function prepareResponse(resultText: string, actionGroup: any, func: any): any {
    // Prepare the response body
    const responseBody = {
        TEXT: {
        body: resultText,
        },
    };

    // Prepare the action response
    const action_response = {
        actionGroup: actionGroup,
        function: func,
        functionResponse: {
        responseBody: responseBody,
        },
    };

    // Prepare the entire function response
    const entire_function_response = {
        response: action_response,
    };

    return entire_function_response;
}

// Function to retrieve vacations days for a given employee
async function getAvailableVacationsDays(employeeId: number,  dbClusterArn: string | undefined, dbCredentialsSecretsStoreArn: string | undefined): Promise<string> {
    // Implement the logic to retrieve the available vacation days for the given employee ID
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

    const sqlCommand = new ExecuteStatementCommand({
        resourceArn: dbClusterArn,
        secretArn: dbCredentialsSecretsStoreArn,
        sql: sql,
        database: databaseName,
        parameters: [
            {
                name: "employeeId",
                value: { longValue: employeeId },
            },
        ],
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



async function reserveVacationTime(employeeId: number, startDate: string, endDate: string,  dbClusterArn: string | undefined, dbCredentialsSecretsStoreArn: string | undefined): Promise<string> {

    // Declare currentYear as a global variable within the function scope
    // let currentYear, vacationDays;
    let vacationDays: number; // Declare vacationDays as a global variable within the function scope


    function convertStringToDate(dateString: string): string | null {
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
        // Calculate the number of vacation days
        // the Date constructor in TypeScript expects either a string, a number, or a Date object as an argument. However, the convertStringToDate function can return either a string or 
        // null, which is causing the type mismatch. To fix this issue, added a type guard to check if the return value of convertStringToDate is not null
        // before creating the Date object. 
        const convertedStartDate = convertStringToDate(startDate);
        const convertedEndDate = convertStringToDate(endDate);

        const start = convertedStartDate !== null ? new Date(convertedStartDate) : null;       
        const end = convertedEndDate !== null ? new Date(convertedEndDate) : null;

        try {
            if (start === null || end === null) {
                const returnMsg = "Invalid date format. Please provide dates in the format YYYY-MM-DD.";
                console.log(returnMsg);
                return returnMsg;
            }
            else {
                console.log(`Start date: ${start}, End date: ${end}`);
                const vacationDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                console.log(`Number of vacation days calculated within the reserveVacationTime function: ${vacationDays}`);
                const currentYear = start.getFullYear();
                console.log(`Current year: ${currentYear}`);
            }
        }
        catch (error) {
            console.error("Error converting date strings to Date objects:", error);
            throw error;
        }



    
        // Check if the employee exists
        const checkEmployeeQuery = "SELECT * FROM employeesTable WHERE employee_id = :employeeId";
        console.log("Checking if the employee exists...");
        const checkEmployeeCommand = new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: checkEmployeeQuery,
            database: databaseName,
            parameters: [{ name: 'employeeId', value: { longValue: employeeId } }],
        });

        const checkEmployeeResponse = await rdsClient.send(checkEmployeeCommand);
        if (!checkEmployeeResponse.records || checkEmployeeResponse.records.length === 0) {
            const returnMsg = `Employee with ID ${employeeId} does not exist.`;
            console.log(returnMsg);
            return returnMsg;
        } else {
            try {
                const employeeName = checkEmployeeResponse.records[0][1].stringValue;
                console.log(`Employee with ID ${employeeId} and name ${employeeName} exists.`);
            } catch (error) {
                console.error("Error checking employee existence:", error);
                throw error;
            }
        }

        // Check if the vacation days are available for the employee in the current year
        const checkAvailableDaysQuery = "SELECT employee_vacation_days_available FROM vacationsTable WHERE employee_id = :employeeId AND year = :year";
        console.log("Checking available vacation days...");
        const currentYear = start.getFullYear();
        const checkAvailableDaysCommand = new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: checkAvailableDaysQuery,
            database: databaseName,
            parameters: [
                { name: 'employeeId', value: { longValue: employeeId } },
                { name: 'year', value: { longValue: currentYear } },
            ],
        });

        const checkAvailableDaysResponse = await rdsClient.send(checkAvailableDaysCommand);

        const vacationDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
        if (!checkAvailableDaysResponse.records || checkAvailableDaysResponse.records.length === 0) {   // Adding a null check before accessing the longValue property 
            const returnMsg = `No vacation data found for employee with ID ${employeeId} in the current year.`;
            console.log(returnMsg);
            return returnMsg;
        } else {
            try {
                const availableDaysRecord = checkAvailableDaysResponse.records[0][0];
                if (!availableDaysRecord || !availableDaysRecord.longValue) {
                    console.error("Error: Invalid response format for available vacation days");
                    throw new Error("Invalid response format for available vacation days");
                }
                const availableDays = availableDaysRecord.longValue;
                console.log(`Available vacation days for employee with ID ${employeeId} in ${currentYear}: ${availableDays}`);
                if (availableDays < vacationDays) {
                    const returnMsg = `Employee with ID ${employeeId} does not have enough vacation days available for the requested period.`;
                    console.log(returnMsg);
                    return returnMsg;
                }
            } catch (error) {
                console.error("Error checking available vacation days:", error);
                throw error;
            }
        }

        // ! Insert the new vacation into the planned_vacations table
        const insertVacationQuery = "INSERT INTO plannedVacationsTable (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (:employeeId, to_date(:startDate, 'YYYY-MM-DD'), to_date(:endDate, 'YYYY-MM-DD'), :vacationDays)";

        console.log("Inserting the new vacation information...");

        // Infer and format the dates
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

        const insertVacationCommand = new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: insertVacationQuery,
            database: databaseName,
            parameters: [
                { name: 'employeeId', value: { longValue: employeeId } },
                { name: 'startDate', value: { stringValue: formattedStartDate } },
                { name: 'endDate', value: { stringValue: formattedEndDate } },
                { name: 'vacationDays', value: { longValue: vacationDays } },
            ],
        });

        // Log the actual query
        const actualQuery = insertVacationCommand.input?.sql;
        if (actualQuery) {
            // Log the actual query that contains the values of the parameter
            const actualQueryWithValues = actualQuery.replace(/\$\([^\)]+\)/g, (match: string) => {
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

        // Execute the query
        await rdsClient.send(insertVacationCommand);




        // Update the vacations table with the new vacation days taken
        const updateVacationsQuery = "UPDATE vacationsTable SET employee_vacation_days_taken = employee_vacation_days_taken + :vacationDays, employee_vacation_days_available = employee_vacation_days_available - :vacationDays WHERE employee_id = :employeeId AND year = :year";
        console.log("Updating the vacations table...");
        const updateVacationsCommand = new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: updateVacationsQuery,
            database: databaseName,
            parameters: [
                { name: 'vacationDays', value: { longValue: vacationDays } },
                { name: 'employeeId', value: { longValue: employeeId } },
                { name: 'year', value: { longValue: currentYear } },
            ],
        });

        await rdsClient.send(updateVacationsCommand);

        const returnMsg = `Vacation saved successfully for employee with ID ${employeeId} from ${startDate} to ${endDate}.`;
        console.log(returnMsg);
        return returnMsg;
    } catch (error) {
        console.error("Error occurred with reserveVacationTime:", error);
        throw error;
    }
};

async function handleRequest(actionGroup: string, func: string, parameters: any[], dbClusterArn: string | undefined, dbCredentialsSecretsStoreArn: string | undefined) {
    if (func === "get_available_vacation_days") {
        let employeeId: number | null = null;

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
        console.log('vacationDaysReturnMsg:', vacationDaysReturnMsg);
        return prepareResponse(vacationDaysReturnMsg, actionGroup, func);

    } else if (func === "reserve_vacation_time") {
        let employeeId: number | null = null;
        let startDate: string | null = null;
        let endDate: string | null = null;

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

        console.log('Extracted parameters:', 'employeeId:', employeeId, 'startDate:', startDate, 'endDate:', endDate)
        const reservationReturnMsg = await reserveVacationTime(employeeId, startDate, endDate, dbClusterArn, dbCredentialsSecretsStoreArn);
        console.log('reservationReturnMsg:', reservationReturnMsg);
        return prepareResponse(reservationReturnMsg, actionGroup, func);
    } else {
        return prepareResponse("Error, no function was called", actionGroup, func);
    }

}



export const handler: Handler = async (event: any, context: Context) => {

    // Log the received event and context for debugging purposes
    console.log('Received event:', JSON.stringify(event, null, 2));
    console.log('Received context:', JSON.stringify(context, null, 2));

    const dbCredentialsSecretsStoreArn = process.env.SECRET_ARN
    const dbClusterArn = process.env.CLUSTER_ARN

    // Destructure the required properties from the event object
    const { agent, actionGroup, function: func, parameters = [], messageVersion } = event;
    console.log('function:', func);
    console.log('Received parameters:', JSON.stringify(parameters, null, 2));

    const finalResponse = await handleRequest(actionGroup, func, parameters, dbClusterArn, dbCredentialsSecretsStoreArn)
    console.log('finalResponse:', JSON.stringify(finalResponse, null, 2));


    return finalResponse

};
