import json
import sys
from typing import Dict, List, Literal

import boto3
import requests
import streamlit as st
from botocore.exceptions import ClientError, NoCredentialsError
from jwt import JWT
from loguru import logger

client_id = sys.argv[1]
api_endpoint = sys.argv[2]


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


def authenticate_user(username, password):
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
            token, do_verify=False  # Skip verification for demonstration
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
    response_dict = json.loads(response.text)
    # logger.debug(response_dict)
    generated_response = response_dict.get('response')
    guardrail_action = response_dict.get("guardrail_action", 'NONE')
    response.raise_for_status()
    return generated_response, guardrail_action
