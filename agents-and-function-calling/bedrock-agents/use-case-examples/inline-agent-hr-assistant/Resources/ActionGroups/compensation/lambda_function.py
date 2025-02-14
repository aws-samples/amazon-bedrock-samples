import json
import logging
import random
import string

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def generate_ticket_number():
    """Generate a random ticket number in the format: 8 random characters + 3 numbers"""
    # Generate 8 random letters
    letters = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=8))
    # Generate 3 random numbers
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{letters}{numbers}"

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: \n{json.dumps(event, indent=2)}")
        
        # Generate dynamic ticket number
        ticket_number = generate_ticket_number()
        
        # Message with dynamic ticket number
        message = f"Your request has been submitted and a ticket has been created for the HR compensation team. You can visit the ticket or ask me for an update on the ticket. Ticket number: {ticket_number}"
        
        body = {
            'status': 'success',
            'message': message,
            'ticket_number': ticket_number  # Including ticket number separately if needed
        }

        # Build response
        response_body = {
            'application/json': {
                'body': json.dumps(body)
            }
        }

        action_response = {
            'actionGroup': event.get('actionGroup', 'CompensationManagement'),
            'apiPath': event.get('apiPath', '/compensation'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': response_body
        }

        final_response = {'response': action_response}
        logger.info(f"Returning successful response: \n{json.dumps(final_response, indent=2)}")
        return final_response

    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        
        error_body = {
            'status': 'error',
            'message': str(e)
        }
        
        response_body = {
            'application/json': {
                'body': json.dumps(error_body)
            }
        }

        action_response = {
            'actionGroup': event.get('actionGroup', 'CompensationManagement'),
            'apiPath': event.get('apiPath', '/compensation'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 400,
            'responseBody': response_body
        }

        error_response = {'response': action_response}
        logger.info(f"Returning error response: \n{json.dumps(error_response, indent=2)}")
        return error_response