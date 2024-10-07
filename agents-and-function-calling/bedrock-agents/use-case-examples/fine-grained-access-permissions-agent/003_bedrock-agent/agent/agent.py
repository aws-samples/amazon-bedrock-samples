import json
import boto3
import os
import logging
import cognitojwt


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

verified_permissions_client = boto3.client("verifiedpermissions")


def get_named_parameter(event, name):
    return next(item for item in event['parameters'] if item['name'] == name)['value']


def list_claims(event):
    # TODO: Implement logic to retrieve and return a list of claims
    dummy_claims = [
        {
            "id": 1,
            "claimAmount": 1000.0,
            "claimDescription": "Dummy claim 1",
            "claimStatus": "approved"
        },
        {
            "id": 2,
            "claimAmount": 2500.75,
            "claimDescription": "Dummy claim 2",
            "claimStatus": "pending"
        }
    ]
    return dummy_claims


def get_claim(event):
    claim_id = int(get_named_parameter(event, 'claimId'))
    # TODO: Implement logic to retrieve and return a claim by ID
    dummy_claim = {
        "id": claim_id,
        "claimAmount": 1000.0,
        "claimDescription": "Dummy claim 1",
        "claimStatus": "approved"
    }
    return dummy_claim


def update_claim(event):
    claim_id = int(get_named_parameter(event, 'claimId'))
    # TODO: Implement logic to update and return a claim by ID
    dummy_claim = {
        "id": claim_id,
        "claimAmount": 3000.0,
        "claimDescription": "Updated dummy claim",
        "claimStatus": "approved"
    }
    return dummy_claim


def lambda_handler(event, context):
    logger.info(f'event: {event}')
    logger.info(f'context: {context}')

    # sessionAttributes contain the authorization_header which is later retrieved to validate the request. This is the JWT token.
    sessionAttributes = event.get("sessionAttributes")
    
    # print("sessionAttributes:", sessionAttributes)
    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']
    http_method = event['httpMethod'].upper()
    action_id = getActionID(api_path, http_method)

    auth, reason = verifyAccess(sessionAttributes, action_id)
    print("auth",auth)
    print("reason",reason)


    if auth == "ALLOW":
        if api_path == '/listClaims' and http_method == 'GET':
            result = list_claims(event)
        elif api_path == '/getClaim/{claimId}' and http_method == 'GET':
            result = get_claim(event)
        elif api_path == '/updateClaim/{claimId}' and http_method == 'PUT':
            result = update_claim(event)
        else:
            response_code = 404
            result = f"Unrecognized api path: {action_group}::{api_path}"

        response_body = {
            'application/json': {
                'body': result
            }
        }
    else:  # auth == "DENY"
        response_code = 401
        response_body = {
            'application/json': {
                'body': reason
            }
        }

    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': response_code,
        'responseBody': response_body
    }

    api_response = {'messageVersion': '1.0', 'response': action_response}
    return api_response


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

    return auth, reason


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