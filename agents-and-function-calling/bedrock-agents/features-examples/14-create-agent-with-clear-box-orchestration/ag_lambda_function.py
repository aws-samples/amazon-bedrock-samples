import os
import json
import shutil
import sqlite3
from datetime import datetime

def get_available_vacations_days(employee_id):
    
    if employee_id:

        available_vacation_days = 10

        if available_vacation_days:
            print(f"Available vacation days for employed_id {employee_id}: {available_vacation_days}")
            return available_vacation_days
        else:
            return_msg = f"No vacation data found for employed_id {employee_id}"
            print(return_msg)
            return return_msg
    else:
        raise Exception(f"No employeed id provided")

    # Close the database connection
    conn.close()
    
    
def reserve_vacation_time(employee_id, start_date, end_date):
    # Get the current year
    current_year = start_date.year

    # Check if the employee exists
    if employee is None:
        return_msg = f"Employee with ID {employee_id} does not exist."
        print(return_msg)
        return return_msg

    if available_days is None or available_days[0] < vacation_days:
        return_msg = f"Employee with ID {employee_id} does not have enough vacation days available for the requested period."
        print(return_msg)
        return return_msg

    print(f"Vacation saved successfully for employee with ID {employee_id} from {start_date} to {end_date}.")
    return f"Vacation saved successfully for employee with ID {employee_id} from {start_date} to {end_date}."
        

def lambda_handler(event, context):
    
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
