

import json
import uuid

def get_named_parameter(event, name):
    """
    Get a parameter from the lambda event
    """
    return next(item for item in event['parameters'] if item['name'] == name)['value']

def get_account_balance(user_id):
    balance = {
        1: 1240.00,
        2: 3214.00,
        3: 2132.00,
        4: 3213.32,
        5: 10000.00,
        6: 12133.00,
        7: 302.32,
        8: 232.32,
        9: 12356.23,
        10: 23232.32
    }
    random_id = str(uuid.uuid1().int)
    user_id = int(random_id[:1])

    print(user_id)
    user_balance = balance[int(user_id)]
    return f"Your current account balance is {user_balance}" 

def book_appointment(user_id, appointment_category, date, hour):
    return f"Appointment booked with success for {date} at {hour}!"

def lambda_handler(event, context):
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])

    if function == "get_account_balance":
        user_id = get_named_parameter(event, "user_id")
        text = get_account_balance(user_id)
    elif function == "book_appointment":
        user_id = get_named_parameter(event, "user_id")
        appointment_category = get_named_parameter(event, "appointment_category")
        date = get_named_parameter(event, "date")
        hour = get_named_parameter(event, "hour")
        text = book_appointment(user_id, appointment_category, date, hour)


    # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
    responseBody =  {
        "TEXT": {
            "body": text
        }
    }

    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(response))

    return response
