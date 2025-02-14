import json
import logging
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock function to get leave balance - replace with actual implementation
def get_leave_balance():
    return 25

def normalize_action(action):
    """Normalize the action string by replacing spaces with underscores and converting to lowercase"""
    if action:
        return action.lower().replace(' ', '_')
    return None

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: \n{json.dumps(event, indent=2)}")
        
        # Extract parameters
        parameters = event.get('parameters', [])
        action = None
        days = None
        
        # Extract and validate parameters
        for param in parameters:
            if param.get('name') == 'action':
                action = normalize_action(param.get('value'))
                logger.info(f"Extracted action: {action}")
            elif param.get('name') == 'days':
                try:
                    days = int(param.get('value', 0))
                    logger.info(f"Extracted days: {days}")
                except ValueError:
                    logger.error("Invalid days value")
                    raise ValueError("Days must be a valid number")

        # Normalize action value
        if action == 'request':
            action = 'apply'
            
        logger.info(f"Normalized action: {action}")

        # Validate action
        if action not in ['check_balance', 'apply']:
            logger.error(f"Invalid action type: {action}")
            raise ValueError("Invalid action type")

        # Get current balance
        current_balance = get_leave_balance()
        logger.info(f"Current balance: {current_balance}")

        # Process the request
        if action == 'check_balance':
            body = {
                'status': 'info',
                'message': f'Your current leave balance is {current_balance} days.'
            }
            logger.info("Processing check_balance request")
        elif action == 'apply':
            if days is None:
                logger.error("Days parameter missing for apply action")
                raise ValueError("Please specify the number of days you'd like to take off")
            
            if days > current_balance:
                logger.error(f"Insufficient balance. Requested: {days}, Available: {current_balance}")
                raise ValueError(f"Unable to process request: You have {current_balance} days available, but requested {days} days")
            
            new_balance = current_balance - days
            
            if days >= 15:
                # For long vacation requests (15 days or more)
                ticket_id = "VAC-" + str(hash(str(event)))[-6:]
                body = {
                    'status': 'pending',
                    'message': f'Your {days}-day leave request requires manager approval. Current balance: {current_balance} days. Tracking ID: {ticket_id}',
                    'ticket_url': f"https://vacation-system.example.com/tickets/{ticket_id}"
                }
            else:
                body = {
                    'status': 'approved',
                    'message': f'Your {days}-day leave request is approved. New balance: {new_balance} days.'
                }

        logger.info(f"Generated response body: {json.dumps(body, indent=2)}")

        # Build response
        response_body = {
            'application/json': {
                'body': json.dumps(body)
            }
        }

        action_response = {
            'actionGroup': event.get('actionGroup', 'VacationManagement'),
            'apiPath': event.get('apiPath', '/vacation'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': response_body
        }

        final_response = {'response': action_response}
        logger.info(f"Returning successful response: \n{json.dumps(final_response, indent=2)}")
        return final_response

    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
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
            'actionGroup': event.get('actionGroup', 'VacationManagement'),
            'apiPath': event.get('apiPath', '/vacation'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 400,
            'responseBody': response_body
        }

        error_response = {'response': action_response}
        logger.info(f"Returning error response: \n{json.dumps(error_response, indent=2)}")
        return error_response