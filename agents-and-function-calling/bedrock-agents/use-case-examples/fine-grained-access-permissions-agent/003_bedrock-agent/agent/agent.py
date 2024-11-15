import json
import boto3
import os
import logging
import cognitojwt

# Enhanced logging configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

verified_permissions_client = boto3.client("verifiedpermissions")

def get_named_parameter(event, name):
    logger.info(f"Retrieving parameter: {name} from event")
    value = next(item for item in event['parameters'] if item['name'] == name)['value']
    logger.info(f"Retrieved parameter value: {value}")
    return value

def list_claims(event, user_info):
    # This function retrieves claims based on user role, filtering for adjusters by region.
    # TODO: Implement logic to retrieve and return a list of claims from DynamoDB.
    # For now, we'll use dummy claims for demonstration purposes.
    logger.info(f"Entering list_claims function with user_info: {user_info}")
    dummy_claims = [
        {
            "id": 1,
            "claimAmount": 1000.0,
            "claimDescription": "Dummy claim 1",
            "claimStatus": "approved",
            "region": "northeast"
        },
        {
            "id": 2,
            "claimAmount": 2500.75,
            "claimDescription": "Dummy claim 2",
            "claimStatus": "pending",
            "region": "northwest"
        }
    ]
    logger.info(f"Retrieved dummy claims: {dummy_claims}")
    
    user_role = user_info.get('role')
    user_region = user_info.get('region')
    logger.info(f"Processing claims for user_role: {user_role}, region: {user_region}")

    # Adjusters can only access claims in their assigned region
    if user_role == 'ClaimsAdjuster':
        logger.info("Filtering claims for adjuster role")
        filtered_claims = [claim for claim in dummy_claims if claim['region'] == user_region]
        logger.info(f"Filtered claims count: {len(filtered_claims)}")
        return filtered_claims
    else:
        # Non-adjusters (assumed to be admins) can access all claims
        logger.info("Returning all claims for admin role")
        return dummy_claims

def get_claim(event, user_info):
    # This function retrieves a claim by ID and applies role-based access control.
    logger.info(f"Entering get_claim function with user_info: {user_info}")
    claim_id = int(get_named_parameter(event, 'claimId'))
    logger.info(f"Retrieving claim with ID: {claim_id}")

    # TODO: Implement logic to retrieve a claim by ID from DynamoDB.
    # For now, we'll use a dummy claim for demonstration purposes.
    dummy_claim = {
        "id": claim_id,
        "claimAmount": 1000.0,
        "claimDescription": "Dummy claim 1",
        "claimStatus": "approved",
        "region": "northeast"
    }
    logger.info(f"Retrieved dummy claim: {dummy_claim}")

    user_role = user_info.get('role')
    user_region = user_info.get('region')
    logger.info(f"Checking access for user_role: {user_role}, region: {user_region}")

    if user_role == 'ClaimsAdjuster':
        # Adjusters can only access claims in their assigned region
        if dummy_claim['region'] == user_region:
            logger.info("Access granted: Claim region matches adjuster region")
            return dummy_claim
        else:
            logger.warning("Access denied: Claim region does not match adjuster region")
            return None
    else:
        # Non-adjusters (assumed to be admins) can access all claims
        logger.info("Access granted: Admin role")
        return dummy_claim


    # TODO: Implement error handling for cases where the claim doesn't exist


def update_claim(event, user_info):
    # This method allows adjusters to update claims they are managing.
    # It assumes any calling method has already validated the adjuster's region.
    logger.info(f"Entering update_claim function with user_info: {user_info}")
    
    claim_id = int(get_named_parameter(event, 'claimId'))
    logger.info(f"Updating claim with ID: {claim_id}")

    # Using dummy claim data for demonstration purpose (to be replaced by database retrieval).
    dummy_claim = {
        "id": claim_id,
        "claimAmount": 3000.0,
        "claimDescription": "Updated dummy claim",
        "claimStatus": "approved",
        "region": "northeast"
    }

    # Here we would normally retrieve the existing claim from the database but for now, we use the dummy claim.
    existing_claim = dummy_claim  # Placeholder: Replace this with actual database retrieval logic.
    logger.info(f"Retrieved existing claim: {existing_claim}")

    # Since the adjuster's region is already validated in the calling method,
    # we can proceed to update the claim data. Assuming we're updating to some new values:
    updated_claim = {
        "id": existing_claim['id'],
        "claimAmount": existing_claim['claimAmount'] + 500.0,  # Example update
        "claimDescription": "Further updated dummy claim",
        "claimStatus": "approved",
        "region": existing_claim['region']
    }

    # TODO: Implement logic to save the updated claim to the database.
    logger.info(f"Updated claim: {updated_claim}")
    return updated_claim  # Return the updated claim to confirm the changes.

def lambda_handler(event, context):
    logger.info(f"Lambda handler invoked with event: {event}")
    try:
        # sessionAttributes contain the authorization_header which is later retrieved to validate the request. 
        # This is the JWT token.
        sessionAttributes = event.get("sessionAttributes")
        logger.info(f"Session attributes retrieved: {sessionAttributes}")

        action_group = event['actionGroup']
        api_path = event['apiPath']
        http_method = event['httpMethod'].upper()
        action_id = getActionID(api_path, http_method)
        logger.info(f"Processing request - Path: {api_path}, Method: {http_method}, Action ID: {action_id}")

        user_info, auth, reason = verifyAccess(sessionAttributes, action_id)
        logger.info(f"Access verification result - Auth: {auth}, Reason: {reason}")

        if auth == "ALLOW":
            response_code = 200
            if api_path == '/listClaims' and http_method == 'GET':
                claims = list_claims(event, user_info)
                # Return the raw claims data without any text formatting
                result = claims
            elif api_path == '/getClaim/{claimId}' and http_method == 'GET':
                result = get_claim(event, user_info)
            elif api_path == '/updateClaim/{claimId}' and http_method == 'PUT':
                result = update_claim(event, user_info)
            else:
                response_code = 404
                result = {"error": f"Unrecognized api path: {action_group}::{api_path}"}
                logger.error(f"Unrecognized API path: {api_path}")
        else:
            response_code = 401
            result = {"error": reason}
            logger.warning(f"Access denied: {reason}")

        response_body = {
            'application/json': {
                'body': result  # Don't use json.dumps here as it's not needed
            }
        }

        api_response = {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': response_code,
                'responseBody': response_body
            }
        }
        logger.info(f"Returning response with status code: {response_code}")
        return api_response
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        raise


def verifyAccess(sessionAttributes, action_id):
    # Initialize variables
    auth = "DENY"
    reason = ""
    user_info = None

    # Check if session attributes are present
    if not sessionAttributes:
        reason = "Missing session attributes"
    else:
        authorization_header = sessionAttributes.get("authorization_header")
        if not authorization_header:
            reason = "Missing user token"
        else:
            # Verify the JWT token and get user information
            user_info = verifyJWT_getUserInfo(authorization_header)
            if not user_info:
                reason = "Invalid or expired Token"
            else:
                # Check if the user is authorized for the given action
                is_authorized = handle_is_authorized(user_info, action_id)
                print("is_authorized=",is_authorized)
                decision = is_authorized.get('decision')
                if decision == "ALLOW":
                    auth = "ALLOW"
                else:
                    reason = "Unauthorized request"

    return user_info, auth, reason


def verifyJWT_getUserInfo(token):
    logger.info("in get_user_info function")
    """
    Validate JWT claims & retrieve user identifier along with additional claims
    """
    try:
        # Decode and verify the JWT using the AWS Cognito JWT library
        verified_user = cognitojwt.decode(
            token, os.environ["AWS_REGION"], os.environ["USER_POOL_ID"]
        )
    except (cognitojwt.CognitoJWTException, ValueError) as error:
        # Log any JWT validation errors
        logger.error(f"JWT validation error: {error}")
        return {}
    
    # Log the verified user information
    logger.info(f"verified_user: {verified_user}")
    
    # Extract relevant user information from the verified JWT
    user_info = {
        "username": verified_user.get("cognito:username"),
        "region": verified_user.get("custom:region"),
        "role": verified_user.get("custom:role")
    }

    # Log the extracted user information
    logger.info(f"user_info: {user_info}")

    # Return the user information
    return user_info


def getActionID(api_path, http_method):
    action_id = None

    if api_path == '/listClaims':
        action_id = "ListClaims"
    elif api_path.startswith('/getClaim/') and http_method == 'GET':
        action_id = "GetClaim"
    elif api_path.startswith('/updateClaim/') and http_method == 'PUT':
        action_id = "UpdateClaim"
    else:
        raise ValueError("Unknown API path or HTTP method")

    return action_id


def handle_is_authorized(user_info, action_id):
    
    operation_mapping = {
        "ListClaims": "application",
        "GetClaim": "claim",
        "UpdateClaim": "claim"
    }
    
    #Derive the Resource type based on the action; If List Claims, we get list of all claims from resource type Application; If GetClaim/UpdateClaim, resource type is claim
    resource_type = operation_mapping[action_id]

     # 1. Construct the authorization request   
    authz_request = construct_authz_request_from_token(user_info, action_id, resource_type)

    # authz_request = construct_authz_request_from_token(user_info, action_id)
    # authz_request = construct_authz_request_from_token_claim(user_info, action_id)
    
    logger.info(f"Authorization request: {authz_request}")

    # 2. Make the `is_authorized` call to Amazon Verified Permissions.
    avp_response = verified_permissions_client.is_authorized(**authz_request)
    logger.info(f"Authorization response: {avp_response}")

    return avp_response
    
def construct_authz_request_from_token(user_info, action_id, resource_type):
    resource_mapping = {
        "application": {
            "entity_type": "avp::claim::app::Application",
            "entity_id": "application-attrs",
            "resource": {
                "entityType": "avp::claim::app::Application",
                "entityId": "application-attrs"
            }
        },
        "claim": {
            "entity_type": "avp::claim::app::Claim",
            "entity_id": "custom-attr-1",
            "resource": {
                "entityType": "avp::claim::app::Claim",
                "entityId": "custom-attr-1"
            }
        }
    }

    resource_entity = resource_mapping.get(resource_type, {})

    entities = [
        {
            "identifier": {
                "entityType": "avp::claim::app::User",
                "entityId": user_info["username"]
            },
            "attributes": {
                "custom": {
                    "record": {
                        "region": {
                            "string": user_info["region"]
                        }
                    }
                }
            },
            "parents": [
                {
                    "entityType": "avp::claim::app::Role",
                    "entityId": user_info["role"]
                }
            ]
        },
        {
            "identifier": {
                "entityType": resource_entity.get("entity_type", ""),
                "entityId": resource_entity.get("entity_id", "")
            },
            "attributes": {
                "owner": {
                    "entityIdentifier": {
                        "entityType": "avp::claim::app::User",
                        "entityId": user_info["username"]
                    }
                },
                "region": {
                    "string": user_info["region"]
                }
            },
            "parents": []
        }
    ]

    return {
        "policyStoreId": os.environ.get("POLICY_STORE_ID"),
        "principal": {
            "entityType": "avp::claim::app::User",
            "entityId": user_info["username"]
        },
        "action": {
            "actionType": "avp::claim::app::Action",
            "actionId": action_id
        },
        "resource": resource_entity.get("resource", {}),
        "entities": {"entityList": entities}
    }