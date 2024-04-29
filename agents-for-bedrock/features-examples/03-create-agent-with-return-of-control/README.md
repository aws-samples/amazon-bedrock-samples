# Create Agents with Return of Control (Function Calling)

In this folder, provide an example of an HR agent using Agents for Amazon Bedrock new capabilities for function definition and return of control for function calling.

The agent allows the employee to `get_available_vacations_days` and `book_vacations` according to the employee's requests.

Both functionalities are implemented in memory in the notebook and would be available in an existant applications for production use cases.

The notebook logic connects with a generated in-memory SQLite database that contains information about employee's available vacation days and planned holidays.

The database structure created is as following:

<img src="images/HR_DB.png" style="width:50%;display:block;margin: 0 auto;">

