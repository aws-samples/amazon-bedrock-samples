import json
import logging
import traceback

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Log the entire incoming event
        logger.info(f"Received event: \n{json.dumps(event, indent=2)}")
        
        # Log the type and structure of parameters
        logger.info(f"Parameters type: {type(event.get('parameters'))}")
        logger.info(f"Parameters content: {json.dumps(event.get('parameters', []), indent=2)}")
        
        # Extract amount with detailed logging
        amount = None
        parameters = event.get('parameters', [])
        
        logger.info(f"Processing parameters list of length: {len(parameters)}")
        
        for param in parameters:
            logger.info(f"Processing parameter: {param}")
            if param.get('name') == 'amount':
                try:
                    amount = float(param.get('value', 0))
                    logger.info(f"Successfully extracted amount: {amount}")
                except ValueError as ve:
                    logger.error(f"Error converting amount to float: {str(ve)}")
                    raise
                break
        
        if amount is None:
            logger.error("Amount parameter not found in the request")
            raise ValueError("Amount parameter not found in the request")
        
        # Make decision based on threshold
        status = "not approved" if amount > 300 else "approved"
        logger.info(f"Decision made: {status} for amount {amount}")
        
        body = {
            'status': status,
            'amount': amount
        }
        
        # Build response
        response_body = {
            'application/json': {
                'body': json.dumps(body)
            }
        }

        action_response = {
            'actionGroup': event.get('actionGroup', 'FetchDetails'),
            'apiPath': event.get('apiPath', '/fetch'),
            'httpMethod': event.get('httpMethod', 'GET'),
            'httpStatusCode': 200,
            'responseBody': response_body
        }

        response = {'response': action_response}
        
        # Log the final response
        logger.info(f"Returning successful response: \n{json.dumps(response, indent=2)}")
        return response
        
    except Exception as e:
        # Log the full stack trace
        logger.error(f"Exception occurred: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        error_body = {
            'status': 'error',
            'amount': 0,
            'message': str(e)
        }
        
        response_body = {
            'application/json': {
                'body': json.dumps(error_body)
            }
        }

        action_response = {
            'actionGroup': event.get('actionGroup', 'FetchDetails'),
            'apiPath': event.get('apiPath', '/fetch'),
            'httpMethod': event.get('httpMethod', 'GET'),
            'httpStatusCode': 400,
            'responseBody': response_body
        }

        error_response = {'response': action_response}
        logger.info(f"Returning error response: \n{json.dumps(error_response, indent=2)}")
        return error_response