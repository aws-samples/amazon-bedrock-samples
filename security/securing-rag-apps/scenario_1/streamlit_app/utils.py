import os
import sys
from http import HTTPStatus
from typing import List

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
        logger.debug(response)

        response.raise_for_status()

        return response.text

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


def get_bedrock_model_ids(
    provider: str = "Anthropic", output_modality: str = "TEXT"
) -> List[str]:
    """
    Fetch model IDs from AWS Bedrock for specified provider and output modality.

    Args:
    provider (str): The provider of the model.
    output_modality (str): The output modality of the model.

    Returns:
    list: A list of model IDs that match the criteria.
    """
    try:
        bedrock_client = boto3.client("bedrock")
        if provider == "Anthropic":
            models = bedrock_client.list_inference_profiles(
                typeEquals="SYSTEM_DEFINED"
            )["inferenceProfileSummaries"]
            model_ids = [
                model["inferenceProfileId"]
                for model in models
                if provider in model["inferenceProfileName"]
                and "claude-3-5" in model["inferenceProfileId"]
            ]
    except NoCredentialsError:
        st.error("AWS credentials not available.")
        logger.error("AWS credentials not properly configured.")
        model_ids = []
    except Exception as e:
        st.error(f"{e}")
        logger.error(f"Error fetching model IDs: {e}")
        model_ids = []
    return model_ids
