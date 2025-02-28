import sys
from typing import List

import boto3
import requests
import streamlit as st
from botocore.exceptions import ClientError, NoCredentialsError
from jwt import JWT
from loguru import logger

client_id = sys.argv[1]
api_endpoint = sys.argv[2]


def authenticate_user(username, password):
    try:
        client = boto3.client("cognito-idp", region_name="us-west-2")

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


def query_KB(prompt, modelID, temp, topP):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json",
    }

    data = {"prompt": prompt, "modelID": modelID, "temperature": temp, "topP": topP}

    response = requests.post(f"{api_endpoint}bedrock", headers=headers, json=data)
    return response.text


def get_bedrock_model_ids(
    provider: str = "Anthropic",
    output_modality: str = "TEXT",
    region: str = "us-west-2",
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
        bedrock_client = boto3.client("bedrock", region_name=region)
        models = bedrock_client.list_foundation_models()["modelSummaries"]
        model_ids = [
            model["modelId"]
            for model in models
            if model["providerName"] == provider
            and model["outputModalities"] == [output_modality]
        ]
        if provider == "Anthropic":
            model_ids = [
                model
                for model in model_ids
                if "claude-3-5" in model and ":0:" not in model
            ]
        elif provider == "Amazon":
            model_ids = [model for model in model_ids if "nova" in model]
    except NoCredentialsError:
        st.error("AWS credentials not available.")
        logger.error("AWS credentials not properly configured.")
        model_ids = []
    except Exception as e:
        logger.error(f"Error fetching model IDs: {e}")
        model_ids = []
    return model_ids
