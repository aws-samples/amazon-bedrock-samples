"""
Bedrock Managed Knowledge Base (BMKB) utility for Amazon Bedrock.

Creates a managed KB with S3 data source, including all required IAM roles,
policies, and resources. No external vector store needed — Bedrock manages it.

Usage:
    from utils.managed_knowledge_base import ManagedKnowledgeBase

    kb = ManagedKnowledgeBase(
        kb_name="my-bmkb",
        bucket_name="my-docs-bucket",
        s3_prefix="documents/",
        embedding_model="amazon.titan-embed-text-v2:0",
    )
    kb.start_ingestion_job()
    # ... use kb.kb_id with retrieve / retrieve_and_generate APIs
    kb.delete_kb()
"""

import json
import time
import pprint
import warnings
import sys
import os

import boto3
from botocore.exceptions import ClientError
from retrying import retry

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

warnings.filterwarnings("ignore")
pp = pprint.PrettyPrinter(indent=2)

# ── Preview / GA toggle ──────────────────────────────────────────────────
# BMKB is now GA. Standard boto3 is used everywhere.
USE_PREVIEW_SDK = False

VALID_EMBEDDING_MODELS = [
    "amazon.titan-embed-text-v2:0",
    "amazon.titan-embed-g1-text-01",
    "cohere.embed-english-v3",
    "cohere.embed-multilingual-v3",
    "cohere.embed-english-v4:0",
    "amazon.nova-2-multimodal-embeddings-v1:0",
]

VALID_PARSING_STRATEGIES = ["SMART_PARSING"]

# ── Connector type registry and validation ────────────────────────────
VALID_CONNECTOR_TYPES = {"S3", "WEB", "CONFLUENCE", "SHAREPOINT", "ONEDRIVE", "GOOGLEDRIVE"}

AUTHENTICATED_CONNECTORS = {"CONFLUENCE", "SHAREPOINT", "ONEDRIVE", "GOOGLEDRIVE"}

CONNECTOR_REQUIRED_FIELDS = {
    "S3": ["bucket_name"],
    "WEB": ["seed_urls"],
    "CONFLUENCE": ["secret_arn"],
    "SHAREPOINT": ["secret_arn"],
    "ONEDRIVE": ["secret_arn"],
    "GOOGLEDRIVE": ["secret_arn"],
}

WEB_VALIDATION = {
    "seed_urls": (1, 10),
    "sitemap_urls": (0, 3),
    "crawl_depth": (0, 10),
    "max_links_per_url": (1, 1000),
    "max_crawled_urls_per_minute": (1, 1200),
}

VALID_AUTH_TYPES = {"NO_AUTH", "BASIC_AUTH", "FORM", "SAML"}

VALID_SYNC_SCOPES = {"SUB_DOMAINS", "ALL_DOMAINS"}


def _build_embedding_model_arn(model_id: str, region: str) -> str:
    """
    Build the foundation model ARN for embedding models.

    BMKB only supports direct foundation model ARNs — inference profiles
    and cross-region inference (CRIS) are NOT supported for embedding models.

    Format: arn:aws:bedrock:<region>::foundation-model/<model-id>
    """
    # If user passed a full ARN, validate it's a foundation-model ARN
    if model_id.startswith("arn:aws:bedrock"):
        if "foundation-model/" not in model_id:
            raise ValueError(
                f"BMKB only supports foundation model ARNs for embeddings.\n"
                f"Inference profiles and CRIS are not supported.\n"
                f"Got: {model_id}\n"
                f"Expected format: arn:aws:bedrock:<region>::foundation-model/<model-id>"
            )
        return model_id
    return f"arn:aws:bedrock:{region}::foundation-model/{model_id}"


def _interactive_sleep(seconds: int):
    for i in range(seconds):
        print("." * (i + 1), end="\r")
        time.sleep(1)
    print()


def _get_session(use_preview: bool):
    """Return a boto3 session — preview-aware or standard."""
    if use_preview:
        try:
            from preview_session import session as preview_sess
            return preview_sess
        except ImportError:
            print("⚠️  preview_session not found, falling back to standard boto3.")
            print("   BMKB is GA, this code path should not execute")
            return boto3.Session()
    return boto3.Session()


def _validate_data_source_config(config: dict) -> None:
    """
    Validate a single data source config dict.

    Raises ValueError with descriptive messages for:
    - Missing or unrecognized ``type`` field
    - Missing required fields per connector type
    - Out-of-range values for WEB connector fields
    - Auth/secret mismatch on WEB connectors
    - Missing secret_arn on authenticated connectors
    """
    # ── type field ────────────────────────────────────────────────────
    connector_type = config.get("type")
    if connector_type is None:
        raise ValueError(
            f"Data source config must include a 'type' field. "
            f"Valid types: {', '.join(sorted(VALID_CONNECTOR_TYPES))}"
        )
    if connector_type not in VALID_CONNECTOR_TYPES:
        raise ValueError(
            f"Invalid connector type '{connector_type}'. "
            f"Valid types: {', '.join(sorted(VALID_CONNECTOR_TYPES))}"
        )

    # ── required fields ───────────────────────────────────────────────
    required = CONNECTOR_REQUIRED_FIELDS.get(connector_type, [])
    for field in required:
        if field not in config or config[field] is None:
            raise ValueError(
                f"{field} is required for {connector_type} data source."
            )

    # ── WEB-specific validation ───────────────────────────────────────
    if connector_type == "WEB":
        # seed_urls count
        seed_urls = config.get("seed_urls", [])
        min_seeds, max_seeds = WEB_VALIDATION["seed_urls"]
        if not (min_seeds <= len(seed_urls) <= max_seeds):
            raise ValueError(
                f"seed_urls must have {min_seeds}-{max_seeds} URLs, got {len(seed_urls)}."
            )

        # sitemap_urls count (optional field, default empty)
        sitemap_urls = config.get("sitemap_urls") or []
        min_sitemaps, max_sitemaps = WEB_VALIDATION["sitemap_urls"]
        if len(sitemap_urls) > max_sitemaps:
            raise ValueError(
                f"sitemap_urls must have {min_sitemaps}-{max_sitemaps} URLs, got {len(sitemap_urls)}."
            )

        # Numeric range checks (only validate if the field is explicitly provided)
        for field in ("crawl_depth", "max_links_per_url", "max_crawled_urls_per_minute"):
            if field in config:
                value = config[field]
                min_val, max_val = WEB_VALIDATION[field]
                if not (min_val <= value <= max_val):
                    raise ValueError(
                        f"{field} must be between {min_val} and {max_val}, got {value}."
                    )

        # Auth / secret consistency
        auth_type = config.get("auth_type", "NO_AUTH")
        if auth_type != "NO_AUTH" and not config.get("secret_arn"):
            raise ValueError(
                f"secret_arn is required when auth_type is {auth_type}."
            )

    # ── Authenticated connectors ──────────────────────────────────────
    if connector_type in AUTHENTICATED_CONNECTORS:
        if not config.get("secret_arn"):
            raise ValueError(
                f"secret_arn is required for {connector_type} data source."
            )


def _build_iam_policies(
    data_sources: list,
    embedding_model: str,
    region: str,
    account_id: str,
    suffix: str,
) -> list:
    """
    Build the minimal set of IAM policies required for the given data sources.

    Always produces:
      - Foundation Model policy (InvokeModel + ListModels + Marketplace)
      - CloudWatch policy (PutMetricData)

    Conditionally produces:
      - S3 policy (consolidated bucket ARNs) if any S3 sources present
      - Secrets Manager policy (consolidated secret ARNs) if any config has secret_arn

    Returns:
        List of (policy_name, policy_document) tuples.
    """
    policies = []

    # ── Foundation Model policy (only when custom embedding model specified) ──
    if embedding_model is not None:
        embedding_model_arn = _build_embedding_model_arn(embedding_model, region)
        fm_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "BedrockInvokeModelStatement",
                    "Effect": "Allow",
                    "Action": ["bedrock:InvokeModel"],
                    "Resource": [embedding_model_arn],
                },
                {
                    "Sid": "BedrockListModelsStatement",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:ListFoundationModels",
                        "bedrock:ListCustomModels",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "MarketplaceOperationsFromBedrockFor3pModels",
                    "Effect": "Allow",
                    "Action": [
                        "aws-marketplace:Subscribe",
                        "aws-marketplace:ViewSubscriptions",
                        "aws-marketplace:Unsubscribe",
                    ],
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {
                            "aws:CalledViaLast": "bedrock.amazonaws.com"
                        }
                    },
                },
            ],
        }
        policies.append((
            f"AmazonBedrockFoundationModelPolicyForKnowledgeBase_{suffix}",
            fm_policy_doc,
        ))

    # ── CloudWatch policy (always) ────────────────────────────────────
    cw_policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "CloudWatchWritePermissionStatement",
                "Effect": "Allow",
                "Action": ["cloudwatch:PutMetricData"],
                "Resource": ["*"],
                "Condition": {
                    "StringEquals": {
                        "cloudwatch:namespace": "AWS/Bedrock/KnowledgeBases"
                    }
                },
            }
        ],
    }
    policies.append((
        f"AmazonBedrockCloudWatchPolicyForKnowledgeBase_{suffix}",
        cw_policy_doc,
    ))

    # ── S3 policy (conditional — only if S3 sources exist) ────────────
    bucket_names = list(dict.fromkeys(
        cfg["bucket_name"]
        for cfg in data_sources
        if cfg.get("type") == "S3" and cfg.get("bucket_name")
    ))
    if bucket_names:
        bucket_arns = [f"arn:aws:s3:::{b}" for b in bucket_names]
        bucket_object_arns = [f"arn:aws:s3:::{b}/*" for b in bucket_names]
        s3_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "S3ListBucketStatement",
                    "Effect": "Allow",
                    "Action": ["s3:ListBucket"],
                    "Resource": bucket_arns,
                    "Condition": {
                        "StringEquals": {"aws:ResourceAccount": [account_id]}
                    },
                },
                {
                    "Sid": "S3GetObjectStatement",
                    "Effect": "Allow",
                    "Action": ["s3:GetObject"],
                    "Resource": bucket_object_arns,
                    "Condition": {
                        "StringEquals": {"aws:ResourceAccount": [account_id]}
                    },
                },
            ],
        }
        policies.append((
            f"AmazonBedrockS3PolicyForKnowledgeBase_{suffix}",
            s3_policy_doc,
        ))

    # ── Secrets Manager policy (conditional — only if any secret_arn) ─
    secret_arns = list(dict.fromkeys(
        cfg["secret_arn"]
        for cfg in data_sources
        if cfg.get("secret_arn")
    ))
    if secret_arns:
        sm_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "SecretsManagerAccess",
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": secret_arns,
                }
            ],
        }
        policies.append((
            f"AmazonBedrockSecretPolicyForKnowledgeBase_{suffix}",
            sm_policy_doc,
        ))

    return policies


def _build_connector_params(config: dict, account_id: str) -> tuple:
    """
    Build the connector parameters and vector ingestion config for a data source.

    Dispatches on ``config["type"]`` to build the correct ``connectorParameters``
    dict for the Bedrock API.

    Args:
        config: A validated data source config dict with a ``type`` field.
        account_id: The AWS account ID (used for S3 bucket owner).

    Returns:
        Tuple of (ds_config, vector_ingestion_config) where:
        - ds_config is the full dataSourceConfiguration dict with
          MANAGED_KNOWLEDGE_BASE_CONNECTOR wrapper
        - vector_ingestion_config is the vectorIngestionConfiguration dict
          with SMART_PARSING
    """
    connector_type = config["type"]

    if connector_type == "S3":
        connector_params = {
            "type": "S3",
            "version": "1",
            "connectionConfiguration": {
                "bucketName": config["bucket_name"],
                "bucketOwnerAccountId": account_id,
            },
            "deletionProtectionConfiguration": {"enableDeletionProtection": False},
        }
        # Add filterConfiguration with inclusionPrefixes if s3_prefix is non-empty
        s3_prefix = config.get("s3_prefix", "")
        if s3_prefix:
            connector_params["filterConfiguration"] = {
                "inclusionPrefixes": [s3_prefix]
            }

    elif connector_type == "WEB":
        connection_cfg = {
            "seedUrls": config["seed_urls"],
            "authType": config.get("auth_type", "NO_AUTH"),
        }
        # Add siteMapUrls if provided
        if config.get("sitemap_urls"):
            connection_cfg["siteMapUrls"] = config["sitemap_urls"]
        # Add secretArn if auth_type != NO_AUTH
        auth_type = config.get("auth_type", "NO_AUTH")
        if auth_type != "NO_AUTH" and config.get("secret_arn"):
            connection_cfg["secretArn"] = config["secret_arn"]

        connector_params = {
            "type": "WEB",
            "version": "1",
            "connectionConfiguration": connection_cfg,
            "crawlConfiguration": {
                "crawlDepth": config.get("crawl_depth", 2),
                "maxLinksPerUrl": config.get("max_links_per_url", 100),
                "maxCrawledUrlsPerMinute": config.get("max_crawled_urls_per_minute", 300),
                "syncScope": config.get("sync_scope", "ALL_DOMAINS"),
                "crawlAttachments": config.get("crawl_attachments", True),
            },
            "deletionProtectionConfiguration": {"enableDeletionProtection": False},
        }

    elif connector_type == "SHAREPOINT":
        connector_params = {
            "type": "SHAREPOINT",
            "version": "1",
            "connectionConfiguration": {
                "secretArn": config["secret_arn"],
                "tenantId": config.get("tenant_id") or config.get("connection_configuration", {}).get("tenantId", ""),
                "authType": config.get("auth_type") or config.get("connection_configuration", {}).get("authType", "OAUTH2_APP"),
            },
            "dataEntityConfiguration": {
                "siteUrls": config.get("site_urls") or config.get("connection_configuration", {}).get("siteUrls", []),
                "crawlFiles": config.get("crawl_files", True),
                "crawlPages": config.get("crawl_pages", True),
            },
            "deletionProtectionConfiguration": {"enableDeletionProtection": False},
        }
        # Certificate path for Entra ID auth
        cert_path = config.get("certificate_s3_path") or config.get("connection_configuration", {}).get("certificateS3Path")
        if cert_path:
            connector_params["connectionConfiguration"]["certificateS3Path"] = cert_path
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
        if filter_config:
            connector_params["filterConfiguration"] = filter_config

    elif connector_type == "CONFLUENCE":
        connector_params = {
            "type": "CONFLUENCE",
            "version": "1",
            "connectionConfiguration": {
                "secretArn": config["secret_arn"],
                **config.get("connection_configuration", {}),
            },
            "deletionProtectionConfiguration": {"enableDeletionProtection": False},
        }
        # Data entity configuration
        if config.get("data_entity_config"):
            connector_params["dataEntityConfiguration"] = config["data_entity_config"]
        # Filter configuration
        if config.get("filter_config"):
            connector_params["filterConfiguration"] = config["filter_config"]

    else:
        # Generic authenticated connectors: ONEDRIVE, GOOGLEDRIVE
        connector_params = {
            "type": config["type"],
            "version": "1",
            "connectionConfiguration": {
                "secretArn": config["secret_arn"],
                **config.get("connection_configuration", {}),
            },
            "deletionProtectionConfiguration": {"enableDeletionProtection": False},
        }
        if config.get("data_entity_config"):
            connector_params["dataEntityConfiguration"] = config["data_entity_config"]
        if config.get("filter_config"):
            connector_params["filterConfiguration"] = config["filter_config"]

    # Wrap in MANAGED_KNOWLEDGE_BASE_CONNECTOR outer structure
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


class ManagedKnowledgeBase:
    """
    End-to-end utility for creating a Bedrock Managed Knowledge Base (BMKB)
    with one or more data sources. Supports S3, WEB, CONFLUENCE, SHAREPOINT,
    ONEDRIVE, and GOOGLEDRIVE connector types. Handles IAM role/policy creation,
    KB creation, data source setup, and ingestion.
    """

    def __init__(
        self,
        kb_name: str,
        data_sources: list = None,
        bucket_name: str = None,
        s3_prefix: str = "",
        embedding_model: str = None,
        enable_logging: bool = False,
        suffix: str = None,
        region_name: str = None,
        use_preview_session: bool = None,
    ):
        """
        Args:
            kb_name: Name for the knowledge base.
            data_sources: List of data source config dicts, each with a ``type``
                field (S3, WEB, CONFLUENCE, SHAREPOINT, ONEDRIVE, GOOGLEDRIVE)
                and connector-specific fields.
            bucket_name: S3 bucket name (backward-compatible shorthand).
                Mutually exclusive with ``data_sources``.
            s3_prefix: S3 prefix to scope ingestion (used with ``bucket_name``).
            embedding_model: Embedding model ID.
            enable_logging: If True, enable CloudWatch log delivery for
                ingestion APPLICATION_LOGS.
            suffix: Suffix for resource naming. Defaults to region-account.
            region_name: AWS region. Defaults to session default.
            use_preview_session: Use preview SDK session. Defaults to module-level
                                 USE_PREVIEW_SDK flag. Set to False for GA.
        """
        if embedding_model is not None and embedding_model not in VALID_EMBEDDING_MODELS:
            raise ValueError(f"embedding_model must be None (managed default) or one of {VALID_EMBEDDING_MODELS}")

        # ── Resolve data_sources from constructor args ────────────────
        if bucket_name and data_sources:
            raise ValueError("Specify either 'bucket_name' or 'data_sources', not both.")
        if bucket_name:
            data_sources = [{"type": "S3", "bucket_name": bucket_name, "s3_prefix": s3_prefix}]
        if not data_sources:
            raise ValueError(
                "At least one data source is required. "
                "Provide 'data_sources' list or 'bucket_name'."
            )

        # Validate all configs upfront before any AWS calls
        for cfg in data_sources:
            _validate_data_source_config(cfg)

        # Session setup — controlled by module-level USE_PREVIEW_SDK or per-instance override
        use_preview = use_preview_session if use_preview_session is not None else USE_PREVIEW_SDK
        self._session = _get_session(use_preview)

        boto3_session = boto3.Session()
        self.region_name = region_name or boto3_session.region_name
        self.account_id = boto3.client("sts").get_caller_identity()["Account"]
        self.identity_arn = boto3.client("sts").get_caller_identity()["Arn"]
        self.suffix = suffix or f"{self.region_name}-{self.account_id}"

        # Clients
        self.iam_client = boto3.client("iam")
        self.s3_client = boto3.client("s3", region_name=self.region_name)
        self.bedrock_agent_client = self._session.client("bedrock-agent", region_name=self.region_name)

        # Config
        self.kb_name = kb_name
        self.embedding_model = embedding_model
        self.enable_logging = enable_logging
        self._data_source_configs = list(data_sources)

        # Resource names
        self.kb_role_name = f"AmazonBedrockExecutionRoleForKnowledgeBase_{self.suffix}"

        # State
        self.kb_id = None
        self.kb_role_arn = None
        self._data_sources = []          # [{type, ds_id, name, config}, ...]
        self._created_policies = []      # policy names created during setup

        # Run setup
        self._setup()

    @property
    def ds_id(self):
        """Return single DS ID for backward compat. Returns first DS ID."""
        if self._data_sources:
            return self._data_sources[0]["ds_id"]
        return None

    @property
    def data_sources(self):
        """Return simplified view of data sources: [{type, ds_id, name}, ...]."""
        return [
            {"type": ds["type"], "ds_id": ds["ds_id"], "name": ds["name"]}
            for ds in self._data_sources
        ]

    def _setup(self):
        # Step 1 — Ensure S3 buckets exist (only for S3 sources)
        s3_configs = [cfg for cfg in self._data_source_configs if cfg.get("type") == "S3"]
        if s3_configs:
            print("=" * 80)
            print("Step 1 — Ensuring S3 buckets exist")
            for cfg in s3_configs:
                bucket = cfg["bucket_name"]
                try:
                    self.s3_client.head_bucket(Bucket=bucket)
                    print(f"  Bucket '{bucket}' already exists")
                except ClientError:
                    print(f"  Creating bucket '{bucket}'")
                    if self.region_name == "us-east-1":
                        self.s3_client.create_bucket(Bucket=bucket)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=bucket,
                            CreateBucketConfiguration={"LocationConstraint": self.region_name},
                        )

        # Step 2 — Build and create IAM role + dynamic policies
        print("=" * 80)
        print("Step 2 — Creating IAM role and policies")

        assume_role_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceAccount": self.account_id
                        },
                        "ArnLike": {
                            "AWS:SourceArn": f"arn:aws:bedrock:{self.region_name}:{self.account_id}:knowledge-base/*"
                        },
                    },
                }
            ],
        }

        # Create role
        try:
            role_resp = self.iam_client.create_role(
                RoleName=self.kb_role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_doc),
                Description=f"Execution role for BMKB: {self.kb_name}",
                MaxSessionDuration=3600,
            )
            print(f"  Created role: {self.kb_role_name}")
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            role_resp = self.iam_client.get_role(RoleName=self.kb_role_name)
            print(f"  Role already exists: {self.kb_role_name}")

        self.kb_role_arn = role_resp["Role"]["Arn"]

        # Build dynamic policies based on data source configs
        policies = _build_iam_policies(
            self._data_source_configs,
            self.embedding_model,
            self.region_name,
            self.account_id,
            self.suffix,
        )

        # Create and attach each policy, track names for cleanup
        for policy_name, policy_doc in policies:
            try:
                policy_resp = self.iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_doc),
                )
                policy_arn = policy_resp["Policy"]["Arn"]
                print(f"  Created policy: {policy_name}")
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                policy_arn = f"arn:aws:iam::{self.account_id}:policy/{policy_name}"
                print(f"  Policy already exists: {policy_name}")

            self.iam_client.attach_role_policy(
                RoleName=self.kb_role_name, PolicyArn=policy_arn
            )
            self._created_policies.append(policy_name)

        # Wait for IAM propagation
        print("  Waiting for IAM propagation...")
        _interactive_sleep(10)

        # Step 3 — Create Knowledge Base
        print("=" * 80)
        print("Step 3 — Creating Bedrock Managed Knowledge Base")
        self._create_knowledge_base()

        # Step 4 — Create data sources from configs
        print("=" * 80)
        print(f"Step 4 — Creating {len(self._data_source_configs)} data source(s)")

        # Track type counts for naming duplicates
        type_counts = {}
        for cfg in self._data_source_configs:
            ctype = cfg["type"].lower()
            type_counts[ctype] = type_counts.get(ctype, 0) + 1

        type_seen = {}
        for cfg in self._data_source_configs:
            ctype = cfg["type"].lower()
            type_seen[ctype] = type_seen.get(ctype, 0) + 1

            # Build data source name with numeric suffix for duplicates
            ds_name = f"{self.kb_name}-{ctype}-source"
            if type_counts[ctype] > 1:
                if type_seen[ctype] == 1:
                    pass  # first one keeps base name
                else:
                    ds_name = f"{ds_name}-{type_seen[ctype]}"

            ds_config, vector_ingestion_config = _build_connector_params(cfg, self.account_id)

            try:
                resp = self.bedrock_agent_client.create_data_source(
                    knowledgeBaseId=self.kb_id,
                    name=ds_name,
                    dataSourceConfiguration=ds_config,
                    vectorIngestionConfiguration=vector_ingestion_config,
                )
                ds_id = resp["dataSource"]["dataSourceId"]
                print(f"  Created data source '{ds_name}': {ds_id}")
            except self.bedrock_agent_client.exceptions.ConflictException:
                ds_list = self.bedrock_agent_client.list_data_sources(
                    knowledgeBaseId=self.kb_id, maxResults=100
                )
                ds_id = next(
                    (
                        ds["dataSourceId"]
                        for ds in ds_list["dataSourceSummaries"]
                        if ds["name"] == ds_name
                    ),
                    ds_list["dataSourceSummaries"][0]["dataSourceId"] if ds_list["dataSourceSummaries"] else None,
                )
                print(f"  Data source '{ds_name}' already exists: {ds_id}")

            self._data_sources.append({
                "type": cfg["type"],
                "ds_id": ds_id,
                "name": ds_name,
                "config": cfg,
            })

            # Wait for AVAILABLE
            self._wait_for_ds_status(ds_id, "AVAILABLE")

        print("=" * 80)
        print(f"Setup complete — KB ID: {self.kb_id}, {len(self._data_sources)} data source(s)")

        # Step 5 — Enable log delivery (optional)
        if self.enable_logging:
            print("=" * 80)
            print("Step 5 — Enabling CloudWatch log delivery")
            self._enable_log_delivery()

    # ── Log delivery ──────────────────────────────────────────────────────

    def _enable_log_delivery(self):
        """Enable CloudWatch log delivery for KB ingestion APPLICATION_LOGS."""
        logs_client = boto3.client("logs", region_name=self.region_name)
        kb_arn = f"arn:aws:bedrock:{self.region_name}:{self.account_id}:knowledge-base/{self.kb_id}"
        log_group = f"/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/{self.kb_id}"
        source_name = f"bedrock-kb-{self.kb_id}"
        dest_name = f"bedrock-kb-dest-{self.kb_id}"

        # Create log group
        try:
            logs_client.create_log_group(logGroupName=log_group)
            print(f"  Created log group: {log_group}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            print(f"  Log group exists: {log_group}")

        # Create delivery source
        try:
            logs_client.put_delivery_source(
                name=source_name, resourceArn=kb_arn, logType="APPLICATION_LOGS",
            )
            print(f"  Created delivery source: {source_name}")
        except Exception as e:
            print(f"  Delivery source: {e}")

        # Create delivery destination
        dest_arn = f"arn:aws:logs:{self.region_name}:{self.account_id}:log-group:{log_group}"
        try:
            logs_client.put_delivery_destination(
                name=dest_name,
                deliveryDestinationConfiguration={"destinationResourceArn": dest_arn},
            )
            print(f"  Created delivery destination: {dest_name}")
        except Exception as e:
            print(f"  Delivery destination: {e}")

        # Create delivery
        try:
            full_dest_arn = f"arn:aws:logs:{self.region_name}:{self.account_id}:delivery-destination:{dest_name}"
            resp = logs_client.create_delivery(
                deliverySourceName=source_name, deliveryDestinationArn=full_dest_arn,
            )
            self._delivery_id = resp["delivery"]["id"]
            print(f"  Log delivery enabled (ID: {self._delivery_id})")
        except Exception as e:
            self._delivery_id = None
            print(f"  Create delivery: {e}")

        self._log_group_name = log_group

    def _disable_log_delivery(self):
        """Disable log delivery and clean up log resources."""
        if not self.enable_logging:
            return
        logs_client = boto3.client("logs", region_name=self.region_name)
        source_name = f"bedrock-kb-{self.kb_id}"
        dest_name = f"bedrock-kb-dest-{self.kb_id}"

        # Delete delivery
        if getattr(self, "_delivery_id", None):
            try:
                logs_client.delete_delivery(id=self._delivery_id)
                print(f"  Deleted delivery: {self._delivery_id}")
            except Exception as e:
                print(f"  Error deleting delivery: {e}")

        # Delete delivery source
        try:
            logs_client.delete_delivery_source(name=source_name)
            print(f"  Deleted delivery source: {source_name}")
        except Exception as e:
            print(f"  Error deleting delivery source: {e}")

        # Delete delivery destination
        try:
            logs_client.delete_delivery_destination(name=dest_name)
            print(f"  Deleted delivery destination: {dest_name}")
        except Exception as e:
            print(f"  Error deleting delivery destination: {e}")

        # Delete log group
        log_group = getattr(self, "_log_group_name", None)
        if log_group:
            try:
                logs_client.delete_log_group(logGroupName=log_group)
                print(f"  Deleted log group: {log_group}")
            except Exception as e:
                print(f"  Error deleting log group: {e}")

    # ── Data source management ────────────────────────────────────────────

    def add_data_source(self, config: dict) -> str:
        """
        Add a new data source to an existing Knowledge Base.

        Validates the config, creates/updates IAM policies if the new source
        requires permissions not yet granted, creates the data source via the
        Bedrock API, and appends it to the internal tracking list.

        Args:
            config: A data source config dict with a ``type`` field and
                connector-specific fields (same schema as entries in the
                ``data_sources`` constructor parameter).

        Returns:
            The new data source ID.

        Raises:
            ValueError: If the config is invalid.
        """
        # 1. Validate the config
        _validate_data_source_config(config)

        # 2. Check if new IAM policies are needed
        existing_has_s3 = any(
            ds["type"] == "S3" for ds in self._data_sources
        )
        existing_secret_arns = {
            ds["config"].get("secret_arn")
            for ds in self._data_sources
            if ds["config"].get("secret_arn")
        }

        new_needs_s3 = config.get("type") == "S3" and not existing_has_s3
        new_secret_arn = config.get("secret_arn")
        new_needs_secret_update = (
            new_secret_arn and new_secret_arn not in existing_secret_arns
        )

        # 3. Create/update IAM policies as needed
        if new_needs_s3:
            # Build and attach an S3 policy for this bucket
            bucket_name = config["bucket_name"]
            s3_policy_name = f"AmazonBedrockS3PolicyForKnowledgeBase_{self.suffix}"
            s3_policy_doc = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3ListBucketStatement",
                        "Effect": "Allow",
                        "Action": ["s3:ListBucket"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}"],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": [self.account_id]
                            }
                        },
                    },
                    {
                        "Sid": "S3GetObjectStatement",
                        "Effect": "Allow",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": [self.account_id]
                            }
                        },
                    },
                ],
            }
            try:
                resp = self.iam_client.create_policy(
                    PolicyName=s3_policy_name,
                    PolicyDocument=json.dumps(s3_policy_doc),
                )
                policy_arn = resp["Policy"]["Arn"]
                print(f"  Created S3 policy: {s3_policy_name}")
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                policy_arn = f"arn:aws:iam::{self.account_id}:policy/{s3_policy_name}"
                print(f"  S3 policy already exists: {s3_policy_name}")

            self.iam_client.attach_role_policy(
                RoleName=self.kb_role_name, PolicyArn=policy_arn
            )
            if s3_policy_name not in self._created_policies:
                self._created_policies.append(s3_policy_name)

            # Ensure the S3 bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                print(f"  Bucket '{bucket_name}' already exists")
            except ClientError:
                print(f"  Creating bucket '{bucket_name}'")
                if self.region_name == "us-east-1":
                    self.s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={
                            "LocationConstraint": self.region_name
                        },
                    )

        if new_needs_secret_update:
            sm_policy_name = f"AmazonBedrockSecretPolicyForKnowledgeBase_{self.suffix}"
            # Collect all secret ARNs (existing + new)
            all_secret_arns = list(existing_secret_arns | {new_secret_arn})
            sm_policy_doc = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "SecretsManagerAccess",
                        "Effect": "Allow",
                        "Action": ["secretsmanager:GetSecretValue"],
                        "Resource": all_secret_arns,
                    }
                ],
            }
            sm_policy_arn = (
                f"arn:aws:iam::{self.account_id}:policy/{sm_policy_name}"
            )

            if sm_policy_name in self._created_policies:
                # Policy exists — delete and recreate with updated ARNs
                try:
                    self.iam_client.detach_role_policy(
                        RoleName=self.kb_role_name, PolicyArn=sm_policy_arn
                    )
                    self.iam_client.delete_policy(PolicyArn=sm_policy_arn)
                except Exception:
                    pass
                try:
                    resp = self.iam_client.create_policy(
                        PolicyName=sm_policy_name,
                        PolicyDocument=json.dumps(sm_policy_doc),
                    )
                    sm_policy_arn = resp["Policy"]["Arn"]
                except self.iam_client.exceptions.EntityAlreadyExistsException:
                    pass
                self.iam_client.attach_role_policy(
                    RoleName=self.kb_role_name, PolicyArn=sm_policy_arn
                )
                print(f"  Updated Secrets Manager policy: {sm_policy_name}")
            else:
                # Create new SM policy
                try:
                    resp = self.iam_client.create_policy(
                        PolicyName=sm_policy_name,
                        PolicyDocument=json.dumps(sm_policy_doc),
                    )
                    sm_policy_arn = resp["Policy"]["Arn"]
                    print(f"  Created Secrets Manager policy: {sm_policy_name}")
                except self.iam_client.exceptions.EntityAlreadyExistsException:
                    print(f"  SM policy already exists: {sm_policy_name}")

                self.iam_client.attach_role_policy(
                    RoleName=self.kb_role_name, PolicyArn=sm_policy_arn
                )
                self._created_policies.append(sm_policy_name)

        # 4. Build connector params and create data source
        ctype = config["type"].lower()

        # Determine name with duplicate suffix
        existing_same_type = sum(
            1 for ds in self._data_sources if ds["type"] == config["type"]
        )
        ds_name = f"{self.kb_name}-{ctype}-source"
        if existing_same_type > 0:
            ds_name = f"{ds_name}-{existing_same_type + 1}"

        ds_config, vector_ingestion_config = _build_connector_params(
            config, self.account_id
        )

        try:
            resp = self.bedrock_agent_client.create_data_source(
                knowledgeBaseId=self.kb_id,
                name=ds_name,
                dataSourceConfiguration=ds_config,
                vectorIngestionConfiguration=vector_ingestion_config,
            )
            ds_id = resp["dataSource"]["dataSourceId"]
            print(f"  Created data source '{ds_name}': {ds_id}")
        except self.bedrock_agent_client.exceptions.ConflictException:
            ds_list = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id, maxResults=100
            )
            ds_id = next(
                (
                    ds["dataSourceId"]
                    for ds in ds_list["dataSourceSummaries"]
                    if ds["name"] == ds_name
                ),
                ds_list["dataSourceSummaries"][0]["dataSourceId"]
                if ds_list["dataSourceSummaries"]
                else None,
            )
            print(f"  Data source '{ds_name}' already exists: {ds_id}")

        # 5. Append to internal tracking and return
        self._data_sources.append({
            "type": config["type"],
            "ds_id": ds_id,
            "name": ds_name,
            "config": config,
        })

        # Wait for AVAILABLE
        self._wait_for_ds_status(ds_id, "AVAILABLE")

        return ds_id

    # ── Knowledge Base ────────────────────────────────────────────────────

    @retry(wait_random_min=1000, wait_random_max=2000, stop_max_attempt_number=5)
    def _create_knowledge_base(self):
        # Build KB configuration — managed default or custom embedding model
        if self.embedding_model is None:
            # Use the managed default embedding model (no extra cost)
            managed_config = {}
        else:
            # Use a custom Bedrock embedding model (additional cost applies)
            embedding_model_arn = _build_embedding_model_arn(self.embedding_model, self.region_name)
            managed_config = {
                "embeddingModelArn": embedding_model_arn,
                "embeddingModelConfiguration": {
                    "bedrockEmbeddingModelConfiguration": {
                        "embeddingDataType": "FLOAT32"
                    }
                },
            }

        try:
            resp = self.bedrock_agent_client.create_knowledge_base(
                name=self.kb_name,
                roleArn=self.kb_role_arn,
                knowledgeBaseConfiguration={
                    "type": "MANAGED",
                    "managedKnowledgeBaseConfiguration": managed_config,
                },
            )
            self.kb_id = resp["knowledgeBase"]["knowledgeBaseId"]
            print(f"  Created KB: {self.kb_id}")
        except self.bedrock_agent_client.exceptions.ConflictException:
            # KB with same name exists — find it
            kbs = self.bedrock_agent_client.list_knowledge_bases(maxResults=100)
            self.kb_id = next(
                (
                    kb["knowledgeBaseId"]
                    for kb in kbs["knowledgeBaseSummaries"]
                    if kb["name"] == self.kb_name
                ),
                None,
            )
            print(f"  KB already exists: {self.kb_id}")

        # Wait for ACTIVE
        self._wait_for_kb_status("ACTIVE")

    def _wait_for_kb_status(self, target, timeout=300, interval=5):
        for _ in range(timeout // interval):
            resp = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=self.kb_id)
            status = resp["knowledgeBase"]["status"]
            if status == target:
                print(f"  KB status: {status}")
                return
            if "FAIL" in status:
                raise RuntimeError(f"KB entered failed state: {status}")
            time.sleep(interval)
        raise TimeoutError(f"KB did not reach {target} within {timeout}s")

    def _wait_for_ds_status(self, ds_id, target, timeout=120, interval=5):
        for _ in range(timeout // interval):
            resp = self.bedrock_agent_client.get_data_source(
                knowledgeBaseId=self.kb_id, dataSourceId=ds_id
            )
            status = resp["dataSource"]["status"]
            if status == target:
                print(f"  Data source status: {status}")
                return
            if "FAIL" in status:
                raise RuntimeError(f"Data source entered failed state: {status}")
            time.sleep(interval)
        raise TimeoutError(f"Data source did not reach {target} within {timeout}s")

    # ── Ingestion ─────────────────────────────────────────────────────────

    def start_ingestion_job(self, ds_id: str = None):
        """
        Start ingestion job(s) and poll until complete.

        Args:
            ds_id: Optional data source ID. When provided, ingests only that
                source and returns a single job result dict. When ``None``,
                ingests all data sources sequentially and returns a list of
                job result dicts.

        Returns:
            A single job dict when ``ds_id`` is provided, or a list of job
            dicts when ingesting all sources.

        Raises:
            ValueError: If ``ds_id`` is provided but does not belong to this KB.
        """
        if ds_id is not None:
            # Validate ds_id belongs to this KB
            if not any(ds["ds_id"] == ds_id for ds in self._data_sources):
                raise ValueError(f"Data source {ds_id} not found in this KB.")
            return self._run_ingestion(ds_id)
        else:
            # Ingest all data sources sequentially
            return [self._run_ingestion(ds["ds_id"]) for ds in self._data_sources]

    def _run_ingestion(self, ds_id: str):
        """Run a single ingestion job for the given data source and poll to completion."""
        resp = self.bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=self.kb_id, dataSourceId=ds_id
        )
        job_id = resp["ingestionJob"]["ingestionJobId"]
        print(f"Ingestion job started for {ds_id}: {job_id}")

        # Poll until terminal state (up to ~30 min for large data sources)
        max_polls = 120  # 120 × 15s = 30 min
        for poll in range(max_polls):
            job = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=ds_id,
                ingestionJobId=job_id,
            )["ingestionJob"]

            status = job["status"]
            stats = job.get("statistics", {})

            # Show progress every 4th poll (~60s)
            if poll > 0 and poll % 4 == 0:
                scanned = stats.get("numberOfDocumentsScanned", 0)
                indexed = stats.get("numberOfNewDocumentsIndexed", 0)
                failed = stats.get("numberOfDocumentsFailed", 0)
                print(f"  ... {status} — scanned={scanned}, indexed={indexed}, failed={failed}")

            if status in ("COMPLETE", "FAILED", "STOPPED"):
                break
            time.sleep(15)

        # Final statistics — matches Bedrock console columns
        stats = job.get("statistics", {})
        scanned = stats.get("numberOfDocumentsScanned", 0)
        indexed = stats.get("numberOfNewDocumentsIndexed", 0)
        modified = stats.get("numberOfModifiedDocumentsIndexed", 0)
        deleted = stats.get("numberOfDocumentsDeleted", 0)
        failed = stats.get("numberOfDocumentsFailed", 0)
        metadata = stats.get("numberOfMetadataDocumentsScanned", 0)

        print(f"\nIngestion {status} ({ds_id})")
        print(f"  Source files: {scanned}")
        print(f"  Added:        {indexed}")
        print(f"  Modified:     {modified}")
        print(f"  Deleted:      {deleted}")
        print(f"  Failed:       {failed}")
        if metadata:
            print(f"  Metadata:     {metadata}")

        if failed > 0:
            print(f"\n  ⚠️  {failed} file(s) failed. Check ingestion logs for details:")
            print(f"     /aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/{self.kb_id}")

        if status == "FAILED":
            reasons = job.get("failureReasons", [])
            if reasons:
                print(f"\n  Failure reasons:")
                for r in reasons:
                    print(f"    - {r}")

        return job

    # ── Retrieval helpers ─────────────────────────────────────────────────

    def get_runtime_client(self):
        """Return a bedrock-agent-runtime client using the same session."""
        return self._session.client("bedrock-agent-runtime", region_name=self.region_name)

    def retrieve(self, query: str, num_results: int = 5):
        """Run a Retrieve API call against this KB."""
        dp = self.get_runtime_client()
        return dp.retrieve(
            knowledgeBaseId=self.kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "managedSearchConfiguration": {"numberOfResults": num_results}
            },
        )

    def retrieve_and_generate(self, query: str, model_arn: str, num_results: int = 5):
        """
        NOT SUPPORTED for Managed Knowledge Bases.

        Use agentic_retrieve_stream(query, model_arn, generate_response=True) instead.
        This method is kept for backward compatibility with DIY (BYOVS) KBs only.
        """
        raise NotImplementedError(
            "RetrieveAndGenerate is not supported for Managed Knowledge Bases. "
            "Use agentic_retrieve_stream(query, model_arn, generate_response=True) instead."
        )

    def agentic_retrieve_stream(self, query: str, model_arn: str, max_results: int = 10, max_iterations: int = 3, generate_response: bool = True, reranking_model_type: str = "MANAGED", reranking_model_arn: str = None):
        """
        Run an AgenticRetrieveStream API call against this KB.

        Uses a foundation model to decompose complex queries into sub-queries
        and iteratively retrieves relevant information. Optionally generates
        a synthesized response from retrieved chunks.

        Args:
            query: The user query.
            model_arn: Foundation model ARN for orchestration.
            max_results: Max retrieval results per sub-query.
            max_iterations: Max agentic iteration rounds.
            generate_response: Whether to generate a synthesized answer (default True).
            reranking_model_type: 'MANAGED' (free default), 'CUSTOM' (specify model), or 'NONE'.
            reranking_model_arn: Required when reranking_model_type='CUSTOM'.

        Returns:
            Dict with:
            - 'traces': list of trace events showing the retrieval process
            - 'results': final deduplicated chunks
            - 'generated_response': synthesized answer with citations (if generate_response=True)
        """
        dp = self.get_runtime_client()
        response = dp.agentic_retrieve_stream(
            messages=[
                {
                    "role": "user",
                    "content": {"text": query},
                }
            ],
            retrievers=[
                {
                    "configuration": {
                        "knowledgeBase": {
                            "knowledgeBaseId": self.kb_id,
                            "retrievalOverrides": {
                                "maxNumberOfResults": max_results,
                            },
                        }
                    }
                }
            ],
            agenticRetrieveConfiguration={
                "foundationModelConfiguration": {
                    "bedrockFoundationModelConfiguration": {
                        "modelConfiguration": {"modelArn": model_arn}
                    },
                    "type": "BEDROCK_FOUNDATION_MODEL",
                },
                "foundationModelType": "CUSTOM",
                "maxAgentIteration": max_iterations,
                "rerankingModelType": reranking_model_type,
                **({"rerankingConfiguration": {
                    "bedrockRerankingConfiguration": {
                        "modelConfiguration": {"modelArn": reranking_model_arn}
                    },
                    "type": "BEDROCK_RERANKING_MODEL",
                }} if reranking_model_type == "CUSTOM" and reranking_model_arn else {}),
            },
            generateResponse=generate_response,
        )

        traces = []
        results = []
        generated_response = None
        response_text_chunks = []

        for event in response["stream"]:
            if "traceEvent" in event:
                traces.append(event["traceEvent"])
            elif "responseEvent" in event:
                # Streaming text chunks of the generated response
                response_text_chunks.append(event["responseEvent"].get("text", ""))
            elif "result" in event:
                results = event["result"].get("results", [])
                generated_response = event["result"].get("generatedResponse")

        output = {"traces": traces, "results": results}
        if generated_response:
            output["generated_response"] = generated_response
        elif response_text_chunks:
            output["generated_response"] = {"answer": "".join(response_text_chunks)}

        return output

    # ── Cleanup ───────────────────────────────────────────────────────────

    def delete_kb(self, delete_s3_bucket: bool = False, delete_iam: bool = True):
        """
        Gracefully delete the KB, data sources, and optionally IAM roles/policies and S3 bucket.
        Handles ordering: data sources first, then KB, then IAM, then S3.
        Each step is wrapped so a failure in one doesn't block the rest.
        """
        print("=" * 80)
        print("Cleaning up resources...")

        # 1. Delete all data sources for this KB
        try:
            ds_list = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id, maxResults=100
            ).get("dataSourceSummaries", [])
            for ds in ds_list:
                ds_id = ds["dataSourceId"]
                try:
                    self.bedrock_agent_client.delete_data_source(
                        knowledgeBaseId=self.kb_id, dataSourceId=ds_id
                    )
                    print(f"  Deleted data source: {ds_id}")
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ResourceNotFoundException":
                        print(f"  Data source {ds_id} already deleted")
                    else:
                        print(f"  Error deleting data source {ds_id}: {e}")
            # Wait for data sources to finish deleting
            if ds_list:
                print("  Waiting for data source deletion to propagate...")
                _interactive_sleep(10)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                print("  KB not found — skipping data source cleanup")
            else:
                print(f"  Error listing data sources: {e}")

        # 2. Delete knowledge base
        try:
            self.bedrock_agent_client.delete_knowledge_base(knowledgeBaseId=self.kb_id)
            print(f"  Deleted KB: {self.kb_id}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                print(f"  KB {self.kb_id} already deleted")
            else:
                print(f"  Error deleting KB: {e}")

        # 3. Delete IAM roles and policies
        if delete_iam:
            self._delete_iam_resources()

        # 4. Delete log delivery (if enabled)
        self._disable_log_delivery()

        # 5. Delete S3 bucket
        if delete_s3_bucket:
            self._delete_s3_bucket()

        print("=" * 80)
        print("Cleanup complete.")

    def _delete_iam_resources(self):
        for policy_name in self._created_policies:
            policy_arn = f"arn:aws:iam::{self.account_id}:policy/{policy_name}"
            try:
                self.iam_client.detach_role_policy(
                    RoleName=self.kb_role_name, PolicyArn=policy_arn
                )
                self.iam_client.delete_policy(PolicyArn=policy_arn)
                print(f"  Deleted policy: {policy_name}")
            except Exception as e:
                print(f"  Skipping policy {policy_name}: {e}")

        try:
            self.iam_client.delete_role(RoleName=self.kb_role_name)
            print(f"  Deleted role: {self.kb_role_name}")
        except Exception as e:
            print(f"  Error deleting role: {e}")

    def _delete_s3_bucket(self):
        # Collect unique bucket names from S3 data sources
        bucket_names = list(dict.fromkeys(
            ds["config"]["bucket_name"]
            for ds in self._data_sources
            if ds.get("type") == "S3" and ds.get("config", {}).get("bucket_name")
        ))
        for bucket_name in bucket_names:
            try:
                s3 = boto3.resource("s3")
                bucket = s3.Bucket(bucket_name)
                bucket.object_versions.delete()
                bucket.objects.all().delete()
                bucket.delete()
                print(f"  Deleted S3 bucket: {bucket_name}")
            except Exception as e:
                print(f"  Error deleting bucket {bucket_name}: {e}")

    # ── Static cleanup (from KB ID only) ─────────────────────────────────

    @staticmethod
    def delete_kb_by_id(kb_id: str, region_name: str = None):
        """
        Delete a KB and its data sources given only the KB ID.
        Useful when you don't have the full ManagedKnowledgeBase object.
        Does NOT delete IAM roles or S3 buckets.
        """
        region = region_name or boto3.Session().region_name
        client = boto3.client("bedrock-agent", region_name=region)

        # Delete all data sources
        try:
            ds_list = client.list_data_sources(
                knowledgeBaseId=kb_id, maxResults=100
            ).get("dataSourceSummaries", [])
            for ds in ds_list:
                try:
                    client.delete_data_source(
                        knowledgeBaseId=kb_id, dataSourceId=ds["dataSourceId"]
                    )
                    print(f"  Deleted data source: {ds['dataSourceId']}")
                except Exception as e:
                    print(f"  Error: {e}")
            if ds_list:
                _interactive_sleep(10)
        except Exception as e:
            print(f"  Error listing data sources: {e}")

        # Delete KB
        try:
            client.delete_knowledge_base(knowledgeBaseId=kb_id)
            print(f"  Deleted KB: {kb_id}")
        except Exception as e:
            print(f"  Error: {e}")

    # ── Info ───────────────────────────────────────────────────────────────

    def get_kb_id(self):
        return self.kb_id

    def get_ds_id(self):
        return self.ds_id  # uses the @property

    def __repr__(self):
        return (
            f"ManagedKnowledgeBase(kb_id={self.kb_id!r}, "
            f"data_sources={len(self._data_sources)}, "
            f"region={self.region_name!r})"
        )

    # ── AgentCore Gateway helpers ─────────────────────────────────────────

    def get_agentcore_client(self):
        """Return a bedrock-agentcore-control client using the same session."""
        return self._session.client("bedrock-agentcore-control", region_name=self.region_name)

    def create_gateway(self, gateway_name: str, gateway_role_arn: str, auth_type: str = "AWS_IAM"):
        """
        Create an AgentCore Gateway with MCP protocol.

        Args:
            gateway_name: Name for the gateway.
            gateway_role_arn: IAM role ARN for the gateway (needs bedrock:Retrieve on the KB).
            auth_type: AWS_IAM, CUSTOM_JWT, or NONE.

        Returns:
            Dict with gateway_id, gateway_url, and status.
        """
        ac = self.get_agentcore_client()

        resp = ac.create_gateway(
            name=gateway_name,
            roleArn=gateway_role_arn,
            protocolType="MCP",
            authorizerType=auth_type,
        )
        gw_id = resp["gatewayId"]
        print(f"  Gateway created: {gw_id}")

        # Wait for READY
        gw_url = None
        for _ in range(24):
            gw = ac.get_gateway(gatewayIdentifier=gw_id)
            if gw["status"] == "READY":
                gw_url = gw.get("gatewayUrl", "N/A")
                break
            time.sleep(5)

        print(f"  Gateway status: {gw['status']}")
        print(f"  Gateway URL: {gw_url}")
        return {"gateway_id": gw_id, "gateway_url": gw_url, "status": gw["status"]}

    def create_gateway_kb_target(
        self,
        gateway_id: str,
        target_name: str = "kb-retrieve",
        num_results: int = 5,
        description: str = "Retrieve from managed KB via Gateway",
    ):
        """
        Create a Gateway Target that connects the Gateway to this KB.

        Uses the bedrock-knowledge-bases connector with managedSearchConfiguration.

        Args:
            gateway_id: The gateway ID to attach the target to.
            target_name: Name for the target.
            num_results: Number of retrieval results.
            description: Description visible to agents.

        Returns:
            Dict with target_id and status.
        """
        ac = self.get_agentcore_client()

        resp = ac.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target_name,
            description=description,
            targetConfiguration={
                "mcp": {
                    "connector": {
                        "source": {"connectorId": "bedrock-knowledge-bases"},
                        "configurations": [{
                            "name": "Retrieve",
                            "parameterValues": {
                                "knowledgeBaseId": self.kb_id,
                                "retrievalConfiguration": {
                                    "managedSearchConfiguration": {
                                        "numberOfResults": num_results
                                    }
                                }
                            },
                        }],
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )

        target_id = resp["targetId"]
        print(f"  Target created: {target_id}")

        # Wait for READY
        for _ in range(12):
            t = ac.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
            if t["status"] == "READY":
                break
            time.sleep(5)

        print(f"  Target status: {t['status']}")
        return {"target_id": target_id, "status": t["status"]}

    def delete_gateway(self, gateway_id: str, target_id: str = None):
        """
        Delete a Gateway and optionally its target. Order: target → gateway.

        Args:
            gateway_id: Gateway ID to delete.
            target_id: Optional target ID to delete first.
        """
        ac = self.get_agentcore_client()

        if target_id:
            try:
                ac.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
                print(f"  Deleted target: {target_id}")
                time.sleep(3)
            except Exception as e:
                print(f"  Error deleting target: {e}")

        try:
            ac.delete_gateway(gatewayIdentifier=gateway_id)
            print(f"  Deleted gateway: {gateway_id}")
        except Exception as e:
            print(f"  Error deleting gateway: {e}")
