"""
Setup helpers for the security & access-control notebooks.

Self-contained — no imports from the repo's utils/ package. Provides the three
prerequisite steps a Managed Knowledge Base needs before it can be created and
ingested:

  1. create_bucket(...)        — ensure an S3 bucket exists (region-aware)
  2. upload_sample_files(...)  — push the repo's synthetic_dataset docs to a prefix
  3. create_kb_role(...)       — create the KB execution role + policies

Or run all three at once:

    from util import setup
    info = setup(bucket_name="my-bmkb-bucket")
    # info -> {"bucket", "prefix", "uploaded", "role_arn"}

    ROLE_ARN  = info["role_arn"]
    S3_BUCKET = info["bucket"]
    S3_PREFIX = info["prefix"]
"""

import os
import json
import time

import boto3
from botocore.exceptions import ClientError

# ── Sample documents shipped with the repo ──────────────────────────────────
# util.py lives in 04-security-and-access-controls/notebooks/, so the repo
# root (and synthetic_dataset/) is two levels up.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATASET_DIR = os.path.join(_REPO_ROOT, "synthetic_dataset")

# Defaults to the text-bearing PDFs (skips the 0-byte IF12695.pdf and the
# large audio/video media files, which need Advanced Indexing to be useful).
DEFAULT_SAMPLE_FILES = [
    "octank_financial_10K.pdf",
    "tornadoes_report.pdf",
]

# Access-control metadata for the sample docs, used by the metadata-filtering
# notebook. Each doc is tagged with a department and an access_level so
# retrieval-time filters (equals / in / andAll on these keys) have something to
# match. Passed as `metadata=` to setup()/upload_sample_files() so the sidecar
# .metadata.json files are created at upload time.
SAMPLE_FILE_METADATA = {
    "octank_financial_10K.pdf": {"department": "finance", "access_level": "confidential"},
    "tornadoes_report.pdf": {"department": "operations", "access_level": "internal"},
}

DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"


def _region(session, region_name):
    return region_name or session.region_name or "us-west-2"


def _embedding_model_arn(model_id, region):
    """Build a foundation-model ARN for an embedding model id (pass-through if
    already an ARN)."""
    if model_id.startswith("arn:aws:bedrock"):
        return model_id
    return f"arn:aws:bedrock:{region}::foundation-model/{model_id}"


# ── Step 1 — bucket ─────────────────────────────────────────────────────────
def create_bucket(bucket_name, region_name=None, session=None):
    """
    Ensure an S3 bucket exists. Idempotent — no error if it already exists.

    Returns the bucket name.
    """
    session = session or boto3.Session()
    region = _region(session, region_name)
    s3 = session.client("s3", region_name=region)

    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket already exists: {bucket_name}")
        return bucket_name
    except ClientError:
        pass

    print(f"Creating bucket: {bucket_name} ({region})")
    if region == "us-east-1":
        # us-east-1 rejects an explicit LocationConstraint
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    print("  Done.")
    return bucket_name


# ── Step 2 — upload sample files ────────────────────────────────────────────
def _metadata_sidecar(attributes):
    """
    Build the JSON body for a .metadata.json sidecar from a simple
    {attr: value} dict, using the typed metadataAttributes format Bedrock
    expects (STRING / NUMBER / BOOLEAN inferred from the Python type).
    """
    typed = {}
    for k, v in attributes.items():
        if isinstance(v, bool):
            value = {"type": "BOOLEAN", "booleanValue": v}
        elif isinstance(v, (int, float)):
            value = {"type": "NUMBER", "numberValue": v}
        else:
            value = {"type": "STRING", "stringValue": str(v)}
        typed[k] = {"value": value, "includeForEmbedding": True}
    return json.dumps({"metadataAttributes": typed}, indent=2)


def upload_sample_files(bucket_name, prefix="documents/", files=None,
                        metadata=None, region_name=None, session=None):
    """
    Upload sample documents from synthetic_dataset/ into the given S3 prefix.

    Args:
        bucket_name: Target bucket (must already exist — see create_bucket).
        prefix: S3 key prefix. A trailing slash is added if missing.
        files: List of filenames from synthetic_dataset/ to upload.
               Defaults to DEFAULT_SAMPLE_FILES.
        metadata: Optional dict mapping filename -> {attr: value}. When a file
               has an entry, a <key>.metadata.json sidecar is uploaded alongside
               it so the attributes are available for retrieval-time filtering.

    Returns the list of S3 keys uploaded (documents only, not sidecars).
    """
    session = session or boto3.Session()
    region = _region(session, region_name)
    s3 = session.client("s3", region_name=region)

    if prefix and not prefix.endswith("/"):
        prefix += "/"
    files = files or DEFAULT_SAMPLE_FILES
    metadata = metadata or {}

    uploaded = []
    print(f"Uploading {len(files)} file(s) to s3://{bucket_name}/{prefix}")
    for fname in files:
        local_path = os.path.join(_DATASET_DIR, fname)
        if not os.path.isfile(local_path):
            print(f"  SKIP (not found): {local_path}")
            continue
        if os.path.getsize(local_path) == 0:
            print(f"  SKIP (empty file): {fname}")
            continue
        key = f"{prefix}{fname}"
        s3.upload_file(local_path, bucket_name, key)
        uploaded.append(key)
        print(f"  Uploaded: {key}")

        # Optional metadata sidecar
        if fname in metadata:
            meta_key = f"{key}.metadata.json"
            s3.put_object(
                Bucket=bucket_name,
                Key=meta_key,
                Body=_metadata_sidecar(metadata[fname]).encode(),
            )
            print(f"    + {meta_key}")

    print(f"  Done ({len(uploaded)} uploaded).")
    return uploaded


# ── IAM policy documents (KB execution role) ────────────────────────────────
def _build_kb_policies(bucket_name, embedding_model, region, account_id, suffix):
    """
    Build the IAM policies the KB execution role needs:
      - Foundation-model invoke (embedding model) + list + marketplace
      - CloudWatch PutMetricData (scoped to the Bedrock KB namespace)
      - S3 read (ListBucket + GetObject) on the data bucket

    Returns a list of (policy_name, policy_document) tuples.

    When embedding_model is None (managed default embedding), the foundation-model
    invoke policy is skipped — Bedrock handles embedding server-side.
    """
    policies = []

    # Foundation-model policy — only needed for a custom embedding model.
    if embedding_model is not None:
        embedding_model_arn = _embedding_model_arn(embedding_model, region)
        fm_policy = {
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
                    "Action": ["bedrock:ListFoundationModels", "bedrock:ListCustomModels"],
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
                        "StringEquals": {"aws:CalledViaLast": "bedrock.amazonaws.com"}
                    },
                },
            ],
        }
        policies.append(
            (f"AmazonBedrockFoundationModelPolicyForKnowledgeBase_{suffix}", fm_policy)
        )

    cw_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "CloudWatchWritePermissionStatement",
            "Effect": "Allow",
            "Action": ["cloudwatch:PutMetricData"],
            "Resource": ["*"],
            "Condition": {
                "StringEquals": {"cloudwatch:namespace": "AWS/Bedrock/KnowledgeBases"}
            },
        }],
    }

    # NOTE: Resource is "*" (not the scoped bucket ARN) on purpose.
    # The MANAGED_KNOWLEDGE_BASE_CONNECTOR ingestion session (the
    # "FMKB-CONNECTOR_..." role session) does NOT authorize s3:ListBucket /
    # s3:GetObject against a scoped bucket ARN — ingestion fails with
    # "not authorized to perform: s3:ListBucket" even when the ARN is exactly
    # correct. Only Resource "*" works for this managed connector. The
    # aws:ResourceAccount condition keeps this account-scoped, so it grants
    # access to buckets IN THIS ACCOUNT only, not every bucket globally.
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ListBucketStatement",
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": ["*"],
                "Condition": {"StringEquals": {"aws:ResourceAccount": [account_id]}},
            },
            {
                "Sid": "S3GetObjectStatement",
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": ["*"],
                "Condition": {"StringEquals": {"aws:ResourceAccount": [account_id]}},
            },
        ],
    }

    policies.append((f"AmazonBedrockCloudWatchPolicyForKnowledgeBase_{suffix}", cw_policy))
    policies.append((f"AmazonBedrockS3PolicyForKnowledgeBase_{suffix}", s3_policy))
    return policies


# ── Step 3 — KB execution role ──────────────────────────────────────────────
def create_kb_role(bucket_name, embedding_model=DEFAULT_EMBEDDING_MODEL,
                   region_name=None, session=None, propagation_wait=10):
    """
    Create the Bedrock KB execution role and attach the required policies
    (foundation-model invoke, CloudWatch, and S3 read on ``bucket_name``).

    Idempotent — reuses the role/policies if they already exist.

    Returns the role ARN.
    """
    session = session or boto3.Session()
    region = _region(session, region_name)
    iam = session.client("iam")
    account_id = session.client("sts").get_caller_identity()["Account"]
    suffix = f"{region}-{account_id}"
    # IAM role names are capped at 64 chars, so keep the prefix short.
    role_name = f"AmazonBedrockExecutionRoleForKB_{suffix}"

    # Trust policy — Bedrock assumes this role, scoped to KBs in this account.
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": account_id},
                "ArnLike": {
                    "AWS:SourceArn": f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/*"
                },
            },
        }],
    }

    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for BMKB security notebooks",
            MaxSessionDuration=3600,
        )
        print(f"Created role: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        print(f"Role already exists: {role_name}")

    role_arn = role["Role"]["Arn"]

    for policy_name, policy_doc in _build_kb_policies(
        bucket_name, embedding_model, region, account_id, suffix
    ):
        try:
            policy_arn = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_doc),
            )["Policy"]["Arn"]
            print(f"  Created policy: {policy_name}")
        except iam.exceptions.EntityAlreadyExistsException:
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            print(f"  Policy already exists: {policy_name}")
        iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

    if propagation_wait:
        print(f"  Waiting {propagation_wait}s for IAM propagation...")
        time.sleep(propagation_wait)

    print(f"ROLE_ARN = {role_arn}")
    return role_arn


# ── AgentCore Gateway role ──────────────────────────────────────────────────
def create_gateway_role(region_name=None, session=None, propagation_wait=10):
    """
    Create the IAM role an AgentCore Gateway assumes to retrieve from KBs.

    Trust: bedrock-agentcore.amazonaws.com. Permissions: bedrock:Retrieve /
    GetKnowledgeBase / ListKnowledgeBases on all KBs in this account (the KB ID
    is created per-notebook, so the policy is scoped to knowledge-base/*).

    Idempotent — reuses the role/policy if they already exist.

    Returns the gateway role ARN.
    """
    session = session or boto3.Session()
    region = _region(session, region_name)
    iam = session.client("iam")
    account_id = session.client("sts").get_caller_identity()["Account"]
    suffix = f"{region}-{account_id}"
    role_name = f"AmazonBedrockGatewayRoleForKB_{suffix}"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }

    permission_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "KnowledgeBaseRetrieve",
                "Effect": "Allow",
                "Action": [
                    "bedrock:Retrieve",
                    "bedrock:GetKnowledgeBase",
                    "bedrock:ListKnowledgeBases",
                ],
                "Resource": [
                    f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/*",
                ],
            },
            {
                # Read the Policy Engine — checked at gateway-create time.
                "Sid": "PolicyEngineRead",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetPolicyEngine",
                    "bedrock-agentcore:GetPolicyEngineSummary",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:policy-engine/*",
                ],
            },
            {
                # Cedar evaluation — the engine calls a family of authorize
                # actions (AuthorizeAction, PartiallyAuthorizeActions, ...),
                # checked against BOTH the policy-engine and gateway resources.
                "Sid": "PolicyEngineAuthorize",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:Authorize*",
                    "bedrock-agentcore:PartiallyAuthorize*",
                ],
                "Resource": [
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:policy-engine/*",
                    f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/*",
                ],
            },
        ],
    }

    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Gateway role for BMKB security notebooks",
            MaxSessionDuration=3600,
        )
        print(f"Created gateway role: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        print(f"Gateway role already exists: {role_name}")

    role_arn = role["Role"]["Arn"]

    policy_name = f"AmazonBedrockGatewayRetrievePolicyForKB_{suffix}"
    try:
        policy_arn = iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permission_policy),
        )["Policy"]["Arn"]
        print(f"  Created policy: {policy_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        # Policy exists — set a new default version so permission changes to this
        # function take effect on re-run. IAM keeps max 5 versions; prune the
        # oldest non-default one if we're at the limit.
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        versions = iam.list_policy_versions(PolicyArn=policy_arn)["Versions"]
        if len(versions) >= 5:
            oldest = min(
                (v for v in versions if not v["IsDefaultVersion"]),
                key=lambda v: v["CreateDate"],
            )
            iam.delete_policy_version(PolicyArn=policy_arn, VersionId=oldest["VersionId"])
        iam.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(permission_policy),
            SetAsDefault=True,
        )
        print(f"  Updated policy (new default version): {policy_name}")
    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

    if propagation_wait:
        print(f"  Waiting {propagation_wait}s for IAM propagation...")
        time.sleep(propagation_wait)

    print(f"GW_ROLE_ARN = {role_arn}")
    return role_arn


# ── One-shot setup ──────────────────────────────────────────────────────────
def setup(bucket_name, prefix="documents/", files=None, metadata=None,
          embedding_model=DEFAULT_EMBEDDING_MODEL, region_name=None,
          session=None):
    """
    Run all three steps: create bucket, upload sample files, create KB role.

    Args:
        metadata: Optional dict mapping filename -> {attr: value} to upload
            .metadata.json sidecars alongside the documents (for filtering).
        embedding_model: Custom embedding model id, or None for the managed
            default (no custom-embedding FM policy is then created).

    Returns a dict: {"bucket", "prefix", "uploaded", "role_arn"}.
    """
    session = session or boto3.Session()
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    create_bucket(bucket_name, region_name=region_name, session=session)
    uploaded = upload_sample_files(
        bucket_name, prefix=prefix, files=files, metadata=metadata,
        region_name=region_name, session=session,
    )
    role_arn = create_kb_role(
        bucket_name, embedding_model=embedding_model,
        region_name=region_name, session=session,
    )

    return {
        "bucket": bucket_name,
        "prefix": prefix,
        "uploaded": uploaded,
        "role_arn": role_arn,
    }
