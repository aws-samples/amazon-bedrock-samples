import json
import uuid
import boto3

def get_named_parameter(event, name):
    """
    Get a parameter from the lambda event
    """
    return next(item for item in event['parameters'] if item['name'] == name)['value']


def book_trip(origin, destination, start_date, end_date, transportation_mode):
    """
    Retrieve details of a restaurant booking
    
    Args:
        booking_id (string): The ID of the booking to retrieve
    """
    booking_id = str(uuid.uuid4())[:8]
    return f"Successfully booked trip from {origin} ({start_date}) to {destination} ({end_date}) via {transportation_mode}. Your booking_id is {booking_id}"

def populate_function_response(event, response_body):
    return {
        'response': {
            'actionGroup': event['actionGroup'], 
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': response_body
                    }
                }
            }
        }
    }


def update_existing_trip_dates(booking_id, new_start_date, new_end_date):
    return f"Successfully updated trip {booking_id}. New departure date: {new_start_date} and new return date: {new_end_date}."

def delete_existing_trip_reservation(booking_id):
    return f"Successfully deleted reservation {booking_id}."

def lambda_handler(event, context):
    # get the action group used during the invocation of the lambda function
    actionGroup = event.get('actionGroup', '')
    
    # name of the function that should be invoked
    function = event.get('function', '')
    
    # parameters to invoke function with
    parameters = event.get('parameters', [])

    if function == 'update_existing_trip_dates':
        booking_id = get_named_parameter(event, "booking_id")
        new_start_date = get_named_parameter(event, "new_start_date")
        new_end_date = get_named_parameter(event, "new_end_date")
        if booking_id and new_start_date and new_end_date:
            response = str(update_existing_trip_dates(booking_id, new_start_date, new_end_date))
            result = json.dumps(response)
        else:
            result = 'Missing booking_id parameter'

    elif function == 'book_trip':
        origin = get_named_parameter(event, "origin")
        destination = get_named_parameter(event, "destination")
        start_date = get_named_parameter(event, "start_date")
        end_date = get_named_parameter(event, "end_date")
        transportation_mode = get_named_parameter(event, "transportation_mode")

        if origin and  destination and start_date and end_date and transportation_mode:
            response = str(book_trip(origin, destination, start_date, end_date, transportation_mode))
            result = json.dumps(response) 
        else:
            result = 'Missing required parameters'
    elif function == 'delete_existing_trip_reservation':
        booking_id = get_named_parameter(event, "booking_id")
        if booking_id and new_start_date and new_end_date:
            response = str(delete_existing_trip_reservation(booking_id))
            result = json.dumps(response)
        else:
            result = 'Missing booking_id parameter'
    else:
        result = 'Invalid function'
    
    action_response = populate_function_response(event, result)

    print(action_response)

    return action_response
