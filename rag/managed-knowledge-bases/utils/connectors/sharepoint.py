"""
SharePoint connector utilities for Bedrock Managed Knowledge Bases.

Provides validation, connector param building, and Secrets Manager helpers
for the SharePoint Online data source connector.

Supported auth types: OAUTH2_APP, ENTRA_ID_APP_ONLY

Usage:
    from utils.connectors.sharepoint import (
        validate_sharepoint_config,
        build_sharepoint_connector_params,
        create_sharepoint_secret_oauth2,
    )
"""

import json
import boto3

VALID_SHAREPOINT_AUTH_TYPES = {"OAUTH2_APP", "ENTRA_ID_APP_ONLY"}

SHAREPOINT_REQUIRED_FIELDS = ["secret_arn", "tenant_id", "auth_type", "site_urls"]


def validate_sharepoint_config(config: dict) -> None:
    """Validate a SharePoint data source config dict."""
    for field in SHAREPOINT_REQUIRED_FIELDS:
        if field not in config or config[field] is None:
            raise ValueError(
                f"'{field}' is required for SHAREPOINT data source. "
                f"Required fields: {', '.join(SHAREPOINT_REQUIRED_FIELDS)}"
            )

    if config["auth_type"] not in VALID_SHAREPOINT_AUTH_TYPES:
        raise ValueError(
            f"Invalid auth_type '{config['auth_type']}'. "
            f"Valid types: {', '.join(sorted(VALID_SHAREPOINT_AUTH_TYPES))}"
        )

    site_urls = config["site_urls"]
    if not site_urls or not isinstance(site_urls, list):
        raise ValueError("site_urls must be a non-empty list of SharePoint site URLs")
    for url in site_urls:
        if not url.startswith("https://") or "sharepoint.com" not in url:
            raise ValueError(f"Invalid SharePoint URL: {url}. Must start with https:// and contain sharepoint.com")

    if config["auth_type"] == "ENTRA_ID_APP_ONLY" and not config.get("certificate_s3_path"):
        raise ValueError("certificate_s3_path is required for ENTRA_ID_APP_ONLY auth")


def build_sharepoint_connector_params(config: dict) -> dict:
    """Build the connectorParameters dict for a SharePoint data source."""
    connection_config = {
        "secretArn": config["secret_arn"],
        "tenantId": config["tenant_id"],
        "authType": config["auth_type"],
    }

    if config["auth_type"] == "ENTRA_ID_APP_ONLY" and config.get("certificate_s3_path"):
        connection_config["certificateS3Path"] = config["certificate_s3_path"]

    connector_params = {
        "type": "SHAREPOINT",
        "version": "1",
        "connectionConfiguration": connection_config,
        "dataEntityConfiguration": {
            "siteUrls": config["site_urls"],
            "crawlFiles": config.get("crawl_files", True),
            "crawlPages": config.get("crawl_pages", True),
        },
        "deletionProtectionConfiguration": {"enableDeletionProtection": False},
    }

    # Optional filter configuration
    filter_config = {}
    if config.get("modified_date_after"):
        filter_config["modifiedDateAfter"] = config["modified_date_after"]
    if config.get("modified_date_before"):
        filter_config["modifiedDateBefore"] = config["modified_date_before"]
    if config.get("inclusion_item_paths"):
        filter_config["inclusionItemPaths"] = config["inclusion_item_paths"]
    if config.get("excluded_sensitivity_label_ids"):
        filter_config["excludedSensitivityLabelIds"] = config["excluded_sensitivity_label_ids"]
    if config.get("max_file_size_mb"):
        filter_config["maxFileSizeInMegaBytes"] = str(config["max_file_size_mb"])
    if filter_config:
        connector_params["filterConfiguration"] = filter_config

    return connector_params


def build_sharepoint_data_source_config(config: dict) -> tuple:
    """Build the full dataSourceConfiguration and vectorIngestionConfiguration."""
    connector_params = build_sharepoint_connector_params(config)
    ds_config = {
        "type": "MANAGED_KNOWLEDGE_BASE_CONNECTOR",
        "managedKnowledgeBaseConnectorConfiguration": {
            "connectorParameters": connector_params,
            "deletionProtectionConfiguration": {"deletionProtectionStatus": "DISABLED"},
        },
    }
    vector_ingestion_config = {"parsingConfiguration": {"parsingStrategy": "SMART_PARSING"}}
    return (ds_config, vector_ingestion_config)


# ── Secrets Manager Helpers ───────────────────────────────────────────

def create_sharepoint_secret_oauth2(
    secret_name: str,
    username: str,
    password: str,
    client_id: str,
    client_secret: str,
    region_name: str = None,
) -> str:
    """Create a Secrets Manager secret for SharePoint OAuth 2.0 App-Only auth."""
    sm = boto3.client("secretsmanager", region_name=region_name)
    secret_value = {
        "userName": username,
        "password": password,
        "clientId": client_id,
        "clientSecret": client_secret,
        "authType": "OAuth2",
    }
    try:
        resp = sm.create_secret(Name=secret_name, SecretString=json.dumps(secret_value))
        print(f"  Created secret: {secret_name}")
        return resp["ARN"]
    except sm.exceptions.ResourceExistsException:
        resp = sm.describe_secret(SecretId=secret_name)
        print(f"  Secret already exists: {secret_name}")
        return resp["ARN"]


def create_sharepoint_secret_entra_id(
    secret_name: str,
    client_id: str,
    client_secret: str,
    certificate_password: str,
    private_key: str,
    region_name: str = None,
) -> str:
    """Create a Secrets Manager secret for SharePoint Entra ID App-Only auth."""
    sm = boto3.client("secretsmanager", region_name=region_name)
    secret_value = {
        "clientId": client_id,
        "clientSecret": client_secret,
        "certificatePassword": certificate_password,
        "privateKey": private_key,
    }
    try:
        resp = sm.create_secret(Name=secret_name, SecretString=json.dumps(secret_value))
        print(f"  Created secret: {secret_name}")
        return resp["ARN"]
    except sm.exceptions.ResourceExistsException:
        resp = sm.describe_secret(SecretId=secret_name)
        print(f"  Secret already exists: {secret_name}")
        return resp["ARN"]


def delete_sharepoint_secret(secret_name: str, region_name: str = None):
    """Delete a SharePoint Secrets Manager secret."""
    sm = boto3.client("secretsmanager", region_name=region_name)
    try:
        sm.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
        print(f"  Deleted secret: {secret_name}")
    except Exception as e:
        print(f"  Error deleting secret {secret_name}: {e}")
