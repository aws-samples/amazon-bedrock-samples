import os
import json
import shutil
import sqlite3
from datetime import datetime

def get_available_vacations_days(employee_id):
    # Connect to the SQLite database
    conn = sqlite3.connect('/tmp/employee_database.db')
    c = conn.cursor()

    if employee_id:

        # Fetch the available vacation days for the employee
        c.execute("""
            SELECT employee_vacation_days_available
            FROM vacations
            WHERE employee_id = ?
            ORDER BY year DESC
            LIMIT 1
        """, (employee_id,))

        available_vacation_days = c.fetchone()

        if available_vacation_days:
            available_vacation_days = available_vacation_days[0]  # Unpack the tuple
            print(f"Available vacation days for employed_id {employee_id}: {available_vacation_days}")
            conn.close()
            return available_vacation_days
        else:
            return_msg = f"No vacation data found for employed_id {employee_id}"
            print(return_msg)
            return return_msg
            conn.close()
    else:
        raise Exception(f"No employeed id provided")

    # Close the database connection
    conn.close()
    
    
def reserve_vacation_time(employee_id, start_date, end_date):
    # Connect to the SQLite database

    conn = sqlite3.connect('/tmp/employee_database.db')
    c = conn.cursor()
    try:
        # Calculate the number of vacation days
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        vacation_days = (end_date - start_date).days + 1

        # Get the current year
        current_year = start_date.year

        # Check if the employee exists
        c.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        employee = c.fetchone()
        if employee is None:
            return_msg = f"Employee with ID {employee_id} does not exist."
            print(return_msg)
            conn.close()
            return return_msg

        # Check if the vacation days are available for the employee in the current year
        c.execute("SELECT employee_vacation_days_available FROM vacations WHERE employee_id = ? AND year = ?", (employee_id, current_year))
        available_days = c.fetchone()
        if available_days is None or available_days[0] < vacation_days:
            return_msg = f"Employee with ID {employee_id} does not have enough vacation days available for the requested period."
            print(return_msg)
            conn.close()
            return return_msg

        # Insert the new vacation into the planned_vacations table
        c.execute("INSERT INTO planned_vacations (employee_id, vacation_start_date, vacation_end_date, vacation_days_taken) VALUES (?, ?, ?, ?)", (employee_id, start_date, end_date, vacation_days))

        # Update the vacations table with the new vacation days taken
        c.execute("UPDATE vacations SET employee_vacation_days_taken = employee_vacation_days_taken + ?, employee_vacation_days_available = employee_vacation_days_available - ? WHERE employee_id = ? AND year = ?", (vacation_days, vacation_days, employee_id, current_year))

        conn.commit()
        print(f"Vacation saved successfully for employee with ID {employee_id} from {start_date} to {end_date}.")
        # Close the database connection
        conn.close()
        return f"Vacation saved successfully for employee with ID {employee_id} from {start_date} to {end_date}."
    except Exception as e:
        raise Exception(f"Error occurred: {e}")
        conn.rollback()
        # Close the database connection
        conn.close()
        return f"Error occurred: {e}"
        

def lambda_handler(event, context):
    original_db_file = 'employee_database.db'
    target_db_file = '/tmp/employee_database.db'
    if not os.path.exists(target_db_file):
        shutil.copy2(original_db_file, target_db_file)
    
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    responseBody =  {
        "TEXT": {
            "body": "Error, no function was called"
        }
    }


    
    if function == 'get_available_vacations_days':
        employee_id = None
        for param in parameters:
            if param["name"] == "employee_id":
                employee_id = param["value"]

        if not employee_id:
            raise Exception("Missing mandatory parameter: employee_id")
        vacation_days = get_available_vacations_days(employee_id)
        responseBody =  {
            'TEXT': {
                "body": f"available vacation days for employed_id {employee_id}: {vacation_days}"
            }
        }
    elif function == 'reserve_vacation_time':
        employee_id = None
        start_date = None
        end_date = None
        for param in parameters:
            if param["name"] == "employee_id":
                employee_id = param["value"]
            if param["name"] == "start_date":
                start_date = param["value"]
            if param["name"] == "end_date":
                end_date = param["value"]
            
        if not employee_id:
            raise Exception("Missing mandatory parameter: employee_id")
        if not start_date:
            raise Exception("Missing mandatory parameter: start_date")
        if not end_date:
            raise Exception("Missing mandatory parameter: end_date")
        
        completion_message = reserve_vacation_time(employee_id, start_date, end_date)
        responseBody =  {
            'TEXT': {
                "body": completion_message
            }
        }  
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(function_response))

    return function_response
