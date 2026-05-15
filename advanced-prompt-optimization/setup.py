#!/usr/bin/env python3
"""Interactive bootstrap for the APO tutorial notebooks.

Run once after installing `requirements.txt`:

    python setup.py                  # fully interactive
    python setup.py -y               # accept all defaults (CI / scripted)
    python setup.py --region us-west-2 --bucket my-bucket --mode live
    python setup.py --reuse-env      # re-confirm existing .env without prompts

What it does (each step asks for confirmation unless -y):
  1. Verifies AWS credentials via `sts get-caller-identity`.
  2. Auto-detects your account ID.
  3. Prompts for a region (defaults to your profile's region or us-west-2).
  4. Lists existing S3 buckets; you pick one or create a new one.
  5. Creates the Lambda execution role `apo-tutorial-lambda-role` if missing.
  6. Asks whether you want notebooks to default to live or replay mode.
  7. Writes the choices to `./.env`.

No state is stored anywhere except `.env` next to this script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

import utils

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / ".env"

LAMBDA_ROLE_NAME = "apo-tutorial-lambda-role"
CALLER_POLICY_NAME = "apo-tutorial-permissions"
DEFAULT_REGION = "us-west-2"


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _say(msg: str) -> None:
    print(f"[setup] {msg}")


def _ask(prompt: str, default: str | None = None, *, assume_yes: bool = False) -> str:
    if assume_yes:
        if default is None:
            sys.exit(f"[setup] ERROR: {prompt} has no default and -y was passed.")
        _say(f"{prompt}: using default '{default}'")
        return default
    label = f"  {prompt}"
    if default is not None:
        label += f" [{default}]"
    label += ": "
    while True:
        ans = input(label).strip()
        if ans:
            return ans
        if default is not None:
            return default


def _confirm(prompt: str, default: bool = True, *, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        ans = input(f"  {prompt} {suffix}: ").strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False


def _read_existing_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    out: dict[str, str] = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


# ---------------------------------------------------------------------------
# AWS resource helpers
# ---------------------------------------------------------------------------

def verify_credentials(session: boto3.Session) -> tuple[str, str]:
    """Return (account_id, caller_arn). Exits on failure."""
    try:
        ident = session.client("sts").get_caller_identity()
    except (NoCredentialsError, ClientError) as e:
        sys.exit(f"[setup] ERROR: could not call sts:GetCallerIdentity — {e}")
    return ident["Account"], ident["Arn"]


def pick_bucket(session: boto3.Session, region: str, account_id: str,
                provided: str | None, *, assume_yes: bool) -> str:
    """Return a bucket name that exists (or was just created) in *region*."""
    s3 = session.client("s3")
    default_name = provided or f"apo-tutorial-{account_id}-{region}"

    if provided is None and not assume_yes:
        try:
            buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])][:25]
        except ClientError:
            buckets = []
        if buckets:
            _say("Existing buckets in your account (first 25):")
            for i, b in enumerate(buckets, 1):
                print(f"    [{i:2d}] {b}")
            print("    [ 0] Type a name (will be created if it doesn't exist)")
            raw = input(f"  Pick a bucket [0-{len(buckets)}], default 0: ").strip() or "0"
            if raw.isdigit() and 1 <= int(raw) <= len(buckets):
                return _ensure_bucket(s3, buckets[int(raw) - 1], region, assume_yes=assume_yes)

    name = _ask("Bucket name (will be created if missing)", default_name, assume_yes=assume_yes)
    return _ensure_bucket(s3, name, region, assume_yes=assume_yes)


def _ensure_bucket(s3, name: str, region: str, *, assume_yes: bool) -> str:
    try:
        s3.head_bucket(Bucket=name)
        # Check region
        loc = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
        if loc != region:
            _say(f"WARNING: bucket '{name}' is in {loc} but you chose region={region}.")
            if not _confirm("Continue using it anyway?", default=False, assume_yes=assume_yes):
                sys.exit("[setup] Aborted; pick a bucket in your chosen region.")
        else:
            _say(f"Bucket '{name}' exists in {region}.")
        return name
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code not in ("404", "NoSuchBucket", "NoSuchKey"):
            # 403 typically means it exists but we can't access it
            sys.exit(f"[setup] ERROR: cannot access bucket '{name}' — {e}")

    _say(f"Bucket '{name}' does not exist.")
    if not _confirm(f"Create it in {region}?", default=True, assume_yes=assume_yes):
        sys.exit("[setup] Aborted; pick or create a bucket and rerun.")
    kwargs: dict = {"Bucket": name}
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**kwargs)
    _say(f"Created bucket '{name}'.")
    return name


def build_caller_policy(account_id: str, region: str, bucket: str) -> dict:
    """Narrow inline policy granting only what the notebooks need.

    Scoped to:
      - APO API calls (bedrock:*AdvancedPromptOptimizationJob)
      - Read/write on the chosen bucket
      - Lambda CRUD + Invoke on `apo-tutorial-*` functions only
      - PassRole on the tutorial Lambda execution role
      - sts:GetCallerIdentity
    """
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowAPOAPIs",
                "Effect": "Allow",
                "Action": [
                    "bedrock:CreateAdvancedPromptOptimizationJob",
                    "bedrock:GetAdvancedPromptOptimizationJob",
                    "bedrock:ListAdvancedPromptOptimizationJobs",
                    "bedrock:StopAdvancedPromptOptimizationJob",
                ],
                "Resource": "*",
            },
            {
                "Sid": "AllowBucketObjectRW",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject", "s3:GetObject", "s3:DeleteObject",
                ],
                "Resource": f"arn:aws:s3:::{bucket}/*",
            },
            {
                "Sid": "AllowBucketLevel",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket", "s3:GetBucketLocation",
                ],
                "Resource": f"arn:aws:s3:::{bucket}",
            },
            {
                "Sid": "AllowLambdaCRUD",
                "Effect": "Allow",
                "Action": [
                    "lambda:CreateFunction", "lambda:UpdateFunctionCode",
                    "lambda:UpdateFunctionConfiguration", "lambda:GetFunction",
                    "lambda:InvokeFunction", "lambda:AddPermission",
                    "lambda:DeleteFunction",
                ],
                "Resource": f"arn:aws:lambda:{region}:{account_id}:function:apo-tutorial-*",
            },
            {
                "Sid": "AllowPassLambdaRole",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": f"arn:aws:iam::{account_id}:role/{LAMBDA_ROLE_NAME}",
            },
            {
                "Sid": "AllowSTSWhoAmI",
                "Effect": "Allow",
                "Action": "sts:GetCallerIdentity",
                "Resource": "*",
            },
        ],
    }


def _caller_kind(caller_arn: str) -> tuple[str, str | None]:
    """Return ("user", user_name) | ("role", role_name) | ("federated", None)."""
    # arn:aws:iam::ACCOUNT:user/NAME
    # arn:aws:sts::ACCOUNT:assumed-role/ROLE_NAME/SESSION_NAME
    parts = caller_arn.split(":")
    if len(parts) < 6:
        return ("federated", None)
    resource = parts[5]
    if resource.startswith("user/"):
        return ("user", resource[len("user/"):])
    if resource.startswith("assumed-role/"):
        role_and_session = resource[len("assumed-role/"):]
        return ("role", role_and_session.split("/", 1)[0])
    return ("federated", None)


def ensure_caller_permissions(session: boto3.Session, caller_arn: str,
                              account_id: str, region: str, bucket: str,
                              *, assume_yes: bool) -> None:
    """Attach the narrow inline policy to the principal running setup.py.

    Works for IAM users and assumed-role principals. For federated/SSO
    sessions where the underlying role can't be modified by the caller, we
    print the policy JSON and instruct the user to give it to their admin.
    """
    policy = build_caller_policy(account_id, region, bucket)
    policy_json = json.dumps(policy, indent=2)
    kind, name = _caller_kind(caller_arn)

    if kind == "federated" or name is None:
        _say("Cannot auto-attach IAM policy: caller is a federated/SSO session.")
        _say(f"Have an admin attach this inline policy named '{CALLER_POLICY_NAME}' "
             "to the principal you use:")
        print()
        print(policy_json)
        print()
        return

    _say(f"Caller is an IAM {kind} ('{name}').")
    if not _confirm(
        f"Attach inline policy '{CALLER_POLICY_NAME}' to this {kind}?",
        default=True, assume_yes=assume_yes,
    ):
        _say("Skipping caller-permission configuration.")
        _say("Policy JSON (apply manually if you want it later):")
        print()
        print(policy_json)
        print()
        return

    iam = session.client("iam")
    try:
        if kind == "user":
            iam.put_user_policy(
                UserName=name,
                PolicyName=CALLER_POLICY_NAME,
                PolicyDocument=policy_json,
            )
        else:
            iam.put_role_policy(
                RoleName=name,
                PolicyName=CALLER_POLICY_NAME,
                PolicyDocument=policy_json,
            )
        _say(f"Attached inline policy '{CALLER_POLICY_NAME}' to {kind} '{name}'.")
    except ClientError as e:
        _say(f"WARNING: could not attach policy automatically ({e.response['Error']['Code']}).")
        _say("Apply this JSON manually (or have an admin do it):")
        print()
        print(policy_json)
        print()


def ensure_lambda_role(session: boto3.Session, *, assume_yes: bool) -> str:
    iam = session.client("iam")
    try:
        info = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
        _say(f"Lambda role '{LAMBDA_ROLE_NAME}' already exists.")
        return info["Role"]["Arn"]
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchEntity":
            raise
    _say(f"Lambda role '{LAMBDA_ROLE_NAME}' does not exist.")
    if not _confirm("Create it (Lambda basic-execution policy)?", default=True, assume_yes=assume_yes):
        sys.exit("[setup] Aborted; create the role manually and rerun.")
    trust = (
        '{"Version":"2012-10-17","Statement":'
        '[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},'
        '"Action":"sts:AssumeRole"}]}'
    )
    created = iam.create_role(RoleName=LAMBDA_ROLE_NAME, AssumeRolePolicyDocument=trust)
    iam.attach_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    _say("Created role + attached basic execution policy. Waiting 10s for IAM propagation…")
    import time
    time.sleep(10)
    return created["Role"]["Arn"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Bootstrap the APO tutorial environment.")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default=None)
    p.add_argument("--bucket", default=None)
    p.add_argument("--mode", choices=["live", "replay"], default=None,
                   help="Default notebook mode (writes APO_USE_REFERENCE).")
    p.add_argument("-y", "--yes", action="store_true",
                   help="Accept all defaults; do not prompt.")
    p.add_argument("--reuse-env", action="store_true",
                   help="Read existing .env, no AWS calls; useful to flip --mode only.")
    p.add_argument("--skip-perms", action="store_true",
                   help="Skip attaching the inline IAM policy to the caller.")
    args = p.parse_args()

    existing = _read_existing_env()

    if args.reuse_env:
        if not existing:
            sys.exit(f"[setup] ERROR: --reuse-env passed but {ENV_FILE} does not exist.")
        env = dict(existing)
        if args.mode:
            env["APO_USE_REFERENCE"] = "1" if args.mode == "replay" else "0"
        _write_env(env)
        _say(f"Updated {ENV_FILE} (reuse mode).")
        _print_summary(env)
        return

    profile = args.profile or existing.get("PROFILE") or "default"
    _say(f"Using AWS profile: {profile}")
    try:
        session = boto3.Session(profile_name=profile)
    except ProfileNotFound:
        sys.exit(f"[setup] ERROR: AWS profile '{profile}' not found. "
                 "Check `aws configure list-profiles` or pass --profile.")

    account_id, caller = verify_credentials(session)
    _say(f"Account: {account_id}")
    _say(f"Caller:  {caller}")

    region_default = (
        args.region
        or existing.get("REGION")
        or DEFAULT_REGION
    )
    region = _ask("Region for S3 + Lambda", region_default, assume_yes=args.yes)
    # Re-bind session to the chosen region.
    session = boto3.Session(profile_name=profile, region_name=region)

    bucket = pick_bucket(session, region, account_id, args.bucket, assume_yes=args.yes)

    role_arn = ensure_lambda_role(session, assume_yes=args.yes)

    if args.skip_perms:
        _say("--skip-perms passed; not configuring caller IAM permissions.")
    else:
        ensure_caller_permissions(
            session, caller, account_id, region, bucket, assume_yes=args.yes,
        )

    if args.mode:
        mode = args.mode
    else:
        default_mode = "replay" if existing.get("APO_USE_REFERENCE") == "1" else "live"
        mode = _ask(
            "Default notebook mode (live | replay)",
            default_mode,
            assume_yes=args.yes,
        ).lower()
        if mode not in ("live", "replay"):
            sys.exit(f"[setup] ERROR: mode must be 'live' or 'replay', got {mode!r}.")

    env = {
        "BUCKET": bucket,
        "REGION": region,
        "ACCOUNT_ID": account_id,
        "PROFILE": profile,
        "LAMBDA_ROLE_ARN": role_arn,
        "APO_USE_REFERENCE": "1" if mode == "replay" else "0",
    }
    _write_env(env)
    _say(f"Wrote {ENV_FILE}")

    if mode == "live":
        _say("Deploying metric Lambdas and running smoke tests…")
        try:
            arns = utils.setup_lambdas(env, lambda_client=session.client("lambda"))
            for ex, arn in arns.items():
                _say(f"  {ex}: {arn}")
        except Exception as e:
            _say(f"WARNING: Lambda deploy/smoke-test failed: {e}")
            _say("You can re-run setup.py after fixing, or run live notebooks anyway.")

    _print_summary(env)


def _write_env(env: dict[str, str]) -> None:
    lines = ["# Generated by setup.py — re-run to update.", ""]
    for key in ("BUCKET", "REGION", "ACCOUNT_ID", "PROFILE",
                "LAMBDA_ROLE_ARN", "APO_USE_REFERENCE"):
        if key in env:
            lines.append(f'export {key}="{env[key]}"')
    ENV_FILE.write_text("\n".join(lines) + "\n")
    os.chmod(ENV_FILE, 0o600)


def _print_summary(env: dict[str, str]) -> None:
    print()
    print("  BUCKET             =", env.get("BUCKET"))
    print("  REGION             =", env.get("REGION"))
    print("  ACCOUNT_ID         =", env.get("ACCOUNT_ID"))
    print("  PROFILE            =", env.get("PROFILE"))
    print("  LAMBDA_ROLE_ARN    =", env.get("LAMBDA_ROLE_ARN"))
    print("  APO_USE_REFERENCE  =", env.get("APO_USE_REFERENCE"),
          "  (1 = replay, 0 = live)")
    print()
    print("Next: open a notebook —")
    print("  jupyter notebook 01_lambda_metric.ipynb")


if __name__ == "__main__":
    main()
