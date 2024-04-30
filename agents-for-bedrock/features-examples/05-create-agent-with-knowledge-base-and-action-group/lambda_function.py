import json
import uuid
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('restaurant_bookings')

def get_booking_details(booking_id):
    try:
        response = table.get_item(Key={'booking_id': booking_id})
        if 'Item' in response:
            return response['Item']
        else:
            return {'message': f'No booking found with ID {booking_id}'}
    except Exception as e:
        return {'error': str(e)}

def create_booking(date, hour, num_guests):
    try:
        booking_id = str(uuid.uuid4())[:8]
        table.put_item(
            Item={
                'booking_id': booking_id,
                'date': date,
                'hour': hour,
                'num_guests': num_guests
            }
        )
        return {'booking_id': booking_id}
    except Exception as e:
        return {'error': str(e)}

def delete_booking(booking_id):
    try:
        response = table.delete_item(Key={'booking_id': booking_id})
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {'message': f'Booking with ID {booking_id} deleted successfully'}
        else:
            return {'message': f'Failed to delete booking with ID {booking_id}'}
    except Exception as e:
        return {'error': str(e)}

def lambda_handler(event, context):
    actionGroup = event.get('actionGroup', '')
    function = event.get('function', '')
    parameters = event.get('parameters', [])

    if function == 'get_booking_details':
        booking_id = None
        for param in parameters:
            if param["name"] == "booking_id":
                booking_id = param["value"]

        if booking_id:
            response = str(get_booking_details(booking_id))
            responseBody = {'TEXT': {'body': json.dumps(response)}}
        else:
            responseBody = {'TEXT': {'body': 'Missing booking_id parameter'}}

    elif function == 'create_booking':
        date = None
        hour = None
        num_guests = None
        for param in parameters:
            if param["name"] == "date":
                date = param["value"]
            if param["name"] == "hour":
                hour = param["value"]
            if param["name"] == "num_guests":
                num_guests = int(param["value"])

        if date and hour and num_guests:
            response = str(create_booking(date, hour, num_guests))
            responseBody = {'TEXT': {'body': json.dumps(response)}}
        else:
            responseBody = {'TEXT': {'body': 'Missing required parameters'}}

    elif function == 'delete_booking':
        booking_id = None
        for param in parameters:
            if param["name"] == "booking_id":
                booking_id = param["value"]

        if booking_id:
            response = str(delete_booking(booking_id))
            responseBody = {'TEXT': {'body': json.dumps(response)}}
        else:
            responseBody = {'TEXT': {'body': 'Missing booking_id parameter'}}

    else:
        responseBody = {'TEXT': {'body': 'Invalid function'}}

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
