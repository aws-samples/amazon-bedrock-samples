"""
Confluence connector utilities for Bedrock Managed Knowledge Bases.

Provides validation, connector param building, and Secrets Manager helpers
for the Confluence data source connector.

Supported auth types: BASIC, OAUTH2, PERSONAL_TOKEN
Deployment type: SAAS only

Usage:
    from utils.connectors.confluence import (
        validate_confluence_config,
        build_confluence_connector_params,
        create_confluence_secret,
    )
"""

import json
import boto3

# ── Constants ─────────────────────────────────────────────────────────

VALID_CONFLUENCE_AUTH_TYPES = {"BASIC", "OAUTH2", "PERSONAL_TOKEN"}

CONFLUENCE_REQUIRED_FIELDS = ["secret_arn", "host_url", "auth_type"]

CONFLUENCE_DATA_ENTITY_DEFAULTS = {
    "crawlBlog": True,
    "crawlPage": True,
    "crawlBlogAttachment": True,
    "crawlPageAttachment": True,
    "crawlArchivedSpace": False,
    "crawlArchivedPage": False,
    "crawlPersonalSpace": False,
}


# ── Validation ────────────────────────────────────────────────────────

def validate_confluence_config(config: dict) -> None:
    """
    Validate a Confluence data source config dict.

    Required fields:
        - secret_arn: Secrets Manager ARN with Confluence credentials
        - host_url: Confluence instance URL (e.g. https://mycompany.atlassian.net)
        - auth_type: BASIC, OAUTH2, or PERSONAL_TOKEN

    Optional fields:
        - data_entity_config: dict controlling which entities to crawl
        - filter_config: dict with inclusion/exclusion filters
        - rotate_secret: bool (default False)

    Raises:
        ValueError with descriptive message if config is invalid.
    """
    for field in CONFLUENCE_REQUIRED_FIELDS:
        if field not in config or config[field] is None:
            raise ValueError(
                f"'{field}' is required for CONFLUENCE data source. "
                f"Required fields: {', '.join(CONFLUENCE_REQUIRED_FIELDS)}"
            )

    auth_type = config["auth_type"]
    if auth_type not in VALID_CONFLUENCE_AUTH_TYPES:
        raise ValueError(
            f"Invalid auth_type '{auth_type}' for CONFLUENCE. "
            f"Valid types: {', '.join(sorted(VALID_CONFLUENCE_AUTH_TYPES))}"
        )

    host_url = config["host_url"]
    if not host_url.startswith("https://"):
        raise ValueError(
            f"host_url must start with 'https://'. Got: {host_url}"
        )


# ── Connector Params Builder ─────────────────────────────────────────

def build_confluence_connector_params(config: dict) -> dict:
    """
    Build the connectorParameters dict for a Confluence data source.

    Args:
        config: Validated Confluence config dict.

    Returns:
        The connectorParameters dict ready for the Bedrock API.
    """
    connection_config = {
        "secretArn": config["secret_arn"],
        "type": "SAAS",
        "authType": config["auth_type"],
        "hostUrl": config["host_url"],
    }

    if config.get("rotate_secret"):
        connection_config["rotateSecret"] = True

    connector_params = {
        "type": "CONFLUENCE",
        "version": "1",
        "connectionConfiguration": connection_config,
        "deletionProtectionConfiguration": {
            "enableDeletionProtection": False,
        },
    }

    # Data entity configuration (what to crawl)
    data_entity = {}
    entity_config = config.get("data_entity_config", {})
    for key, default in CONFLUENCE_DATA_ENTITY_DEFAULTS.items():
        data_entity[key] = entity_config.get(key, default)
    connector_params["dataEntityConfiguration"] = data_entity

    # Filter configuration (optional)
    filter_config = config.get("filter_config")
    if filter_config:
        connector_params["filterConfiguration"] = filter_config

    return connector_params


def build_confluence_data_source_config(config: dict) -> tuple:
    """
    Build the full dataSourceConfiguration and vectorIngestionConfiguration
    for a Confluence data source.

    Args:
        config: Validated Confluence config dict.

    Returns:
        Tuple of (ds_config, vector_ingestion_config).
    """
    connector_params = build_confluence_connector_params(config)

    ds_config = {
        "type": "MANAGED_KNOWLEDGE_BASE_CONNECTOR",
        "managedKnowledgeBaseConnectorConfiguration": {
            "connectorParameters": connector_params,
            "deletionProtectionConfiguration": {
                "deletionProtectionStatus": "DISABLED"
            },
        },
    }

    vector_ingestion_config = {
        "parsingConfiguration": {"parsingStrategy": "SMART_PARSING"}
    }

    return (ds_config, vector_ingestion_config)


# ── Secrets Manager Helpers ───────────────────────────────────────────

def create_confluence_secret_basic(
    secret_name: str,
    username: str,
    api_token: str,
    host_url: str,
    region_name: str = None,
) -> str:
    """
    Create a Secrets Manager secret for Confluence Basic authentication.

    Args:
        secret_name: Name for the secret.
        username: Confluence email/username.
        api_token: Confluence API token.
        host_url: Confluence instance URL.
        region_name: AWS region.

    Returns:
        The secret ARN.
    """
    sm = boto3.client("secretsmanager", region_name=region_name)

    secret_value = {
        "username": username,
        "password": api_token,
        "hostUrl": host_url,
        "apiToken": api_token,
    }

    try:
        resp = sm.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value),
        )
        print(f"  Created secret: {secret_name}")
        return resp["ARN"]
    except sm.exceptions.ResourceExistsException:
        resp = sm.describe_secret(SecretId=secret_name)
        print(f"  Secret already exists: {secret_name}")
        return resp["ARN"]


def create_confluence_secret_oauth2(
    secret_name: str,
    app_key: str,
    app_secret: str,
    access_token: str,
    refresh_token: str,
    host_url: str,
    region_name: str = None,
) -> str:
    """
    Create a Secrets Manager secret for Confluence OAuth 2.0 authentication.

    Args:
        secret_name: Name for the secret.
        app_key: Confluence OAuth app key.
        app_secret: Confluence OAuth app secret.
        access_token: OAuth access token.
        refresh_token: OAuth refresh token.
        host_url: Confluence instance URL.
        region_name: AWS region.

    Returns:
        The secret ARN.
    """
    sm = boto3.client("secretsmanager", region_name=region_name)

    secret_value = {
        "confluenceAppKey": app_key,
        "confluenceAppSecret": app_secret,
        "confluenceAccessToken": access_token,
        "confluenceRefreshToken": refresh_token,
        "hostUrl": host_url,
    }

    try:
        resp = sm.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value),
        )
        print(f"  Created secret: {secret_name}")
        return resp["ARN"]
    except sm.exceptions.ResourceExistsException:
        resp = sm.describe_secret(SecretId=secret_name)
        print(f"  Secret already exists: {secret_name}")
        return resp["ARN"]


def delete_confluence_secret(secret_name: str, region_name: str = None):
    """Delete a Confluence Secrets Manager secret."""
    sm = boto3.client("secretsmanager", region_name=region_name)
    try:
        sm.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
        print(f"  Deleted secret: {secret_name}")
    except Exception as e:
        print(f"  Error deleting secret {secret_name}: {e}")
