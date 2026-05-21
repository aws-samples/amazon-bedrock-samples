import json
import os
import sys
from http import HTTPStatus
from typing import Dict, List, Literal

import boto3
import requests
import streamlit as st
from botocore.exceptions import ClientError, NoCredentialsError
from jwt import JWT
from loguru import logger

client_id = os.getenv("COGNITO_CLIENT_ID") or (
    sys.argv[1] if len(sys.argv) > 1 else None
)
api_endpoint = os.getenv("API_ENDPOINT") or (sys.argv[2] if len(sys.argv) > 2 else None)

# Validate that we got the values from either source
if not client_id or not api_endpoint:
    print("Error: Required values not provided")
    print("Please either set COGNITO_CLIENT_ID and API_ENDPOINT environment variables")
    print("or provide them as command line arguments:")
    print(f"Usage: {sys.argv[0]} <cognito_client_id> <api_endpoint>")
    sys.exit(1)


def authenticate_user(username, password):
    """Authenticate user"""
    try:
        client = boto3.client("cognito-idp")

        auth_params = {"USERNAME": username, "PASSWORD": password}

        response = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters=auth_params,
            ClientId=client_id,
        )

        token = response["AuthenticationResult"]["IdToken"]

        st.session_state.token = token

        jwt_instance = JWT()

        decoded = jwt_instance.decode(
            token,
            do_verify=False,  # Skip verification for demonstration
        )
        return {"success": True, "data": decoded}
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        return {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
        }


def query_KB(prompt: str, model_id: str, temp: float, top_p: float):
    """
    Make POST request to Amazon Bedrock with configurable model parameters

    Args:
        prompt: The input text prompt
        model_id: The Bedrock model identifier
        temp: model temperature settings
        top_p: model top_p setting

    Returns:
        Text containing response from KB retreive_and_generate call
    """
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json",
    }

    data = {
        "prompt": prompt,
        "modelID": model_id,
        "temperature": temp,
        "top_p": top_p,
        "max_tokens": 2048,
    }

    # logger.debug(f"Request data: {data}")
    try:
        # logger.debug(f"{api_endpoint}bedrock")
        response = requests.post(f"{api_endpoint}bedrock", headers=headers, json=data)
        response_dict = json.loads(response.text)
        # logger.debug(response_dict)
        generated_response = response_dict.get('response')
        guardrail_action = response_dict.get("guardrail_action", 'NONE')
        response.raise_for_status()

        return generated_response, guardrail_action

    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return {
            "success": False,
            "error": "Request timed out",
            "status_code": HTTPStatus.REQUEST_TIMEOUT,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(
                e.response, "status_code", HTTPStatus.INTERNAL_SERVER_ERROR
            ),
        }


def get_inference_profiles(
    provider: str,
    type: Literal["SYSTEM_DEFINED", "APPLICATION"] = "SYSTEM_DEFINED",
) -> Dict[str, str]:
    bedrock_client = boto3.client("bedrock")
    try:
        response = bedrock_client.list_inference_profiles(typeEquals=type)
        profiles = response["inferenceProfileSummaries"]
        filtered_profiles = [
            profile
            for profile in profiles
            if provider.strip().lower() in profile["inferenceProfileId"]
        ]
        inf_profiles_map = {
            profile["inferenceProfileName"]: profile["inferenceProfileArn"]
            for profile in filtered_profiles
            if profile["status"] == "ACTIVE"
        }
        # logger.debug(inf_profiles_map)
        return inf_profiles_map
    except NoCredentialsError:
        logger.error("AWS credentials not properly configured.")
        return {}
    except Exception as e:
        logger.error(f"Error fetching inference profiles: {e}")
        return {}
