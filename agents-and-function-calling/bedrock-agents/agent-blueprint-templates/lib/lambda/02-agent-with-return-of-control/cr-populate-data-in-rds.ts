import { Context, Handler } from "aws-lambda";
import { RDSDataClient, ExecuteStatementCommand } from "@aws-sdk/client-rds-data";
import { faker } from '@faker-js/faker';


const rdsClient = new RDSDataClient({});
const databaseName = 'employeedatabase';


let dbClusterArn;
let dbCredentialsSecretsStoreArn;
export const handler: Handler = async (event: any, context: Context) => {

    const secretArn = process.env.SECRET_ARN
    const resourceArn = process.env.CLUSTER_ARN
    if (secretArn === undefined || resourceArn === undefined) {
        throw new Error('Missing environment variables');
      } else {
        dbCredentialsSecretsStoreArn = secretArn;
        dbClusterArn = resourceArn;
        // console.log('dbCredentialsSecretsStoreArn', dbCredentialsSecretsStoreArn);
        // console.log('dbClusterArn', dbClusterArn);
        console.log('databaseName', databaseName);
        console.log('Successfully retrieved environment variables');
      };

    // Delete the tables if they already exist
    const deleteEmployeesTableSql = `DROP TABLE IF EXISTS employeesTable CASCADE;`;
    const deleteVacationsTableSql = `DROP TABLE IF EXISTS vacationsTable CASCADE;`;
    const deletePlannedVacationsTableSql = `DROP TABLE IF EXISTS plannedVacationsTable CASCADE;`;

    const deleteEmployeesTableCommand = new ExecuteStatementCommand({
        resourceArn: dbClusterArn,
        secretArn: dbCredentialsSecretsStoreArn,
        sql: deleteEmployeesTableSql,
        database: databaseName,
    });

    const deleteVacationsTableCommand = new ExecuteStatementCommand({
        resourceArn: dbClusterArn,
        secretArn: dbCredentialsSecretsStoreArn,
        sql: deleteVacationsTableSql,
        database: databaseName,
    });

    const deletePlannedVacationsTableCommand = new ExecuteStatementCommand({
        resourceArn: dbClusterArn,
        secretArn: dbCredentialsSecretsStoreArn,
        sql: deletePlannedVacationsTableSql,
        database: databaseName,
    });

    try {
        await rdsClient.send(deleteEmployeesTableCommand);
        await rdsClient.send(deleteVacationsTableCommand);
        await rdsClient.send(deletePlannedVacationsTableCommand);
        console.log('Tables deleted successfully');
    } catch (error) {
        console.error('Error deleting tables:', error);
    }


    // Create the tables if they do not exist
    const createEmployeesTableSql = `CREATE TABLE IF NOT EXISTS employeesTable (
                                        employee_id SERIAL PRIMARY KEY,
                                        employee_name TEXT,
                                        employee_job_title TEXT,
                                        employee_start_date TEXT,
                                        employee_employment_status TEXT
                                        )`;

    try {
        await rdsClient.send(new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: createEmployeesTableSql,
            database: databaseName,
        }));
        console.log('Employees table created successfully');
    } catch (error) {
        console.error('Error creating employees table:', error);
    }

    const createVacationsTableSql = `CREATE TABLE IF NOT EXISTS vacationsTable (
                                        employee_id INTEGER,
                                        year INTEGER,
                                        employee_total_vacation_days INTEGER,
                                        employee_vacation_days_taken INTEGER,
                                        employee_vacation_days_available INTEGER,
                                        FOREIGN KEY (employee_id) REFERENCES employeesTable (employee_id)
                                        )`;

    
    try {
        await rdsClient.send(new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: createVacationsTableSql,
            database: databaseName,
        }));
        console.log('Vacations table created successfully');
    } catch (error) {
        console.error('Error creating vacations table:', error);
    }
    
    const createPlannedVacationsTableSql = `CREATE TABLE IF NOT EXISTS plannedVacationsTable (
                                                employee_id INTEGER,
                                                vacation_start_date DATE,
                                                vacation_end_date DATE,
                                                vacation_days_taken INTEGER,
                                                FOREIGN KEY (employee_id) REFERENCES employeesTable (employee_id)
                                                )`;
    
    try {
        await rdsClient.send(new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: createPlannedVacationsTableSql,
            database: databaseName,
        }));
        console.log('Planned vacations table created successfully');
    } catch (error) {
        console.error('Error creating planned vacations table:', error);
    }




    // Populate tables with sample data
    const jobTitles = ['Manager', 'Developer', 'Designer', 'Analyst', 'Accountant', 'Software Engineer'];
    const employmentStatuses = ['Active', 'Inactive'];

    for (let i = 1; i <= 10; i++) {
        const employeeId = i;
        const name = faker.person.fullName()
        const jobTitle = jobTitles[Math.floor(Math.random() * jobTitles.length)];
        const startDate = `2015-${Math.floor(Math.random() * 12) + 1}-${Math.floor(Math.random() * 28) + 1}`;
        const employmentStatus = employmentStatuses[Math.floor(Math.random() * employmentStatuses.length)];

        
        const insertSql = `
        INSERT INTO employeesTable (employee_id, employee_name, employee_job_title, employee_start_date, employee_employment_status)
        VALUES (:employeeId, :name, :jobTitle, :startDate, :employmentStatus)
        ON CONFLICT (employee_id) DO UPDATE SET
        employee_name = :name,
        employee_job_title = :jobTitle,
        employee_start_date = :startDate,
        employee_employment_status = :employmentStatus
        `;

        const insertCommand = new ExecuteStatementCommand({
            resourceArn: dbClusterArn,
            secretArn: dbCredentialsSecretsStoreArn,
            sql: insertSql,
            database: databaseName,
            parameters: [
              { name: 'employeeId', value: { longValue: employeeId } },
              { name: 'name', value: { stringValue: name } },
              { name: 'jobTitle', value: { stringValue: jobTitle } },
              { name: 'startDate', value: { stringValue: startDate } },
              { name: 'employmentStatus', value: { stringValue: employmentStatus } },
            ],
          });

        try {
        const response = await rdsClient.send(insertCommand);
        console.log(`Updated employeesTable for employee ${name} with ID ${employeeId}`);
        } catch (error) {
        console.error("Error inserting employee:", error);
        }


        // Generate vacation data for the current employee
        const currentYear = new Date().getFullYear();
        for (let year = currentYear; year >= currentYear - 3; year--) {
            
            // console.log(year);
            const totalVacationDays = Math.floor(Math.random() * 30) + 1;
            const daysTaken = Math.floor(Math.random() * totalVacationDays);
            const daysAvailable = totalVacationDays - daysTaken;
            const insertVacationSql = `
                INSERT INTO vacationsTable (employee_id, year, employee_total_vacation_days, employee_vacation_days_taken, employee_vacation_days_available)
                VALUES (${employeeId}, ${year}, ${totalVacationDays}, ${daysTaken}, ${daysAvailable})
            `;

            try {
                const response = await rdsClient.send(new ExecuteStatementCommand({
                    resourceArn: dbClusterArn,
                    secretArn: dbCredentialsSecretsStoreArn,
                    sql: insertVacationSql,
                    database: databaseName,
                }));
                console.log(`Updated vacationsTable for employee ${employeeId} and year ${year}`);
            } catch (error) {
                console.error("Error inserting vacation data:", error);
            }


            // Generate some planned vacations for the current employee and year
            for (let i = 0; i < Math.floor(Math.random() * 3); i++) {
                const startDate = new Date(year, Math.floor(Math.random() * 12), Math.floor(Math.random() * 28) + 1);

                const endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + Math.floor(Math.random() * 15) + 1); // Random number of days between 1 and 15

                const daysTaken = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)); // Calculate the number of days taken

                const insertPlannedVacationSql = `
                    INSERT INTO plannedVacationsTable (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken)
                    VALUES (${employeeId}, '${startDate.toISOString().split('T')[0]}', '${endDate.toISOString().split('T')[0]}', ${daysTaken})
                `;

                try {
                    const response = await rdsClient.send(new ExecuteStatementCommand({
                        resourceArn: dbClusterArn,
                        secretArn: dbCredentialsSecretsStoreArn,
                        sql: insertPlannedVacationSql,
                        database: databaseName,
                    }));
                    console.log(`Updated plannedVacationsTable for employee ${employeeId} and year ${year}`);
                } catch (error) {
                    console.error("Error inserting planned vacation:", error);
                }
            }
    

        }

    }

};