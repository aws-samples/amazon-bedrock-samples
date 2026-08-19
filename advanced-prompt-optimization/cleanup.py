#!/usr/bin/env python3
"""Teardown for the APO tutorial — deletes everything `setup.py` and the
notebooks created in your AWS account.

Usage:
    python cleanup.py                # interactive, confirm each destructive op
    python cleanup.py -y             # accept all confirmations
    python cleanup.py --dry-run      # print what would be deleted, do nothing
    python cleanup.py --delete-bucket   # also remove the S3 bucket itself
    python cleanup.py --keep-env     # leave the local .env file in place
    python cleanup.py --keep-perms   # leave the caller IAM policy in place

What gets removed (in order):
  1. APO jobs whose name starts with `apo-tutorial-` (stops + batch-deletes).
  2. Lambda functions matching `apo-tutorial-*-metric`.
  3. S3 objects under the `apo-tutorial/` prefix of the bucket from `.env`.
  4. (Optional, --delete-bucket only) The S3 bucket itself.
  5. Inline IAM policy `apo-tutorial-permissions` from the caller.
  6. IAM role `apo-tutorial-lambda-role` (detaches managed policies first).
  7. Local `.env` file (unless --keep-env).

Idempotent. Safe to re-run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / ".env"

LAMBDA_ROLE_NAME = "apo-tutorial-lambda-role"
CALLER_POLICY_NAME = "apo-tutorial-permissions"
LAMBDA_FUNCTION_PREFIX = "apo-tutorial-"
JOB_NAME_PREFIX = "apo-tutorial-"
S3_PREFIX = "apo-tutorial/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _say(msg: str) -> None:
    print(f"[cleanup] {msg}")


def _confirm(prompt: str, *, assume_yes: bool, dry_run: bool, default: bool = True) -> bool:
    if dry_run:
        return False  # never actually do anything in dry-run
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


def _read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        sys.exit(
            f"[cleanup] ERROR: {ENV_FILE} not found.\n"
            "        Nothing to clean up — or run `python setup.py` first if you want\n"
            "        cleanup to know which bucket/region to look in."
        )
    env: dict[str, str] = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _caller_kind(arn: str) -> tuple[str, str | None]:
    parts = arn.split(":")
    if len(parts) < 6:
        return ("federated", None)
    res = parts[5]
    if res.startswith("user/"):
        return ("user", res[len("user/"):])
    if res.startswith("assumed-role/"):
        return ("role", res[len("assumed-role/"):].split("/", 1)[0])
    return ("federated", None)


# ---------------------------------------------------------------------------
# 1. APO jobs
# ---------------------------------------------------------------------------

def cleanup_apo_jobs(env: dict, *, assume_yes: bool, dry_run: bool) -> None:
    session = boto3.Session(profile_name=env["PROFILE"], region_name=env["REGION"])
    cfg = Config(retries={"max_attempts": 3, "mode": "standard"},
                 read_timeout=60, connect_timeout=10)
    bedrock = session.client("bedrock", config=cfg)

    matching: list[dict] = []
    next_token = None
    try:
        while True:
            kwargs = {"maxResults": 100}
            if next_token:
                kwargs["nextToken"] = next_token
            resp = bedrock.list_advanced_prompt_optimization_jobs(**kwargs)
            for j in resp.get("jobSummaries", []):
                if j.get("jobName", "").startswith(JOB_NAME_PREFIX):
                    matching.append(j)
            next_token = resp.get("nextToken")
            if not next_token:
                break
    except ClientError as e:
        _say(f"WARNING: could not list APO jobs ({e.response['Error']['Code']}); skipping.")
        return

    if not matching:
        _say("No tutorial APO jobs found.")
        return

    _say(f"Found {len(matching)} APO job(s) with prefix '{JOB_NAME_PREFIX}':")
    for j in matching[:10]:
        _say(f"  - {j['jobName']} ({j.get('jobStatus')})")
    if len(matching) > 10:
        _say(f"  … and {len(matching) - 10} more.")

    if dry_run:
        return
    if not _confirm(f"Stop in-flight jobs and batch-delete all {len(matching)}?",
                    assume_yes=assume_yes, dry_run=dry_run):
        _say("Skipping APO job cleanup.")
        return

    in_flight = [j for j in matching if j.get("jobStatus") == "InProgress"]
    for j in in_flight:
        try:
            bedrock.stop_advanced_prompt_optimization_job(jobIdentifier=j["jobArn"])
            _say(f"Stopped {j['jobName']}.")
        except ClientError as e:
            _say(f"WARNING: stop {j['jobName']} failed: {e.response['Error']['Code']}")

    arns = [j["jobArn"] for j in matching]
    for i in range(0, len(arns), 25):
        batch = arns[i:i + 25]
        try:
            resp = bedrock.batch_delete_advanced_prompt_optimization_job(jobIdentifiers=batch)
            errors = resp.get("errors", []) if isinstance(resp, dict) else []
            for err in errors:
                _say(f"  delete error: {err}")
            _say(f"Deleted batch of {len(batch) - len(errors)} jobs.")
        except ClientError as e:
            _say(f"WARNING: batch delete failed: {e.response['Error']['Code']}")


# ---------------------------------------------------------------------------
# 2. Lambda functions
# ---------------------------------------------------------------------------

def cleanup_lambdas(env: dict, *, assume_yes: bool, dry_run: bool) -> None:
    session = boto3.Session(profile_name=env["PROFILE"], region_name=env["REGION"])
    lam = session.client("lambda")
    found: list[str] = []
    try:
        paginator = lam.get_paginator("list_functions")
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                if fn["FunctionName"].startswith(LAMBDA_FUNCTION_PREFIX):
                    found.append(fn["FunctionName"])
    except ClientError as e:
        _say(f"WARNING: could not list Lambda functions ({e.response['Error']['Code']}).")
        return

    if not found:
        _say("No tutorial Lambdas found.")
        return

    _say(f"Found {len(found)} tutorial Lambda(s):")
    for n in found:
        _say(f"  - {n}")
    if dry_run:
        return
    if not _confirm(f"Delete all {len(found)} Lambdas?", assume_yes=assume_yes, dry_run=dry_run):
        _say("Skipping Lambda cleanup.")
        return

    for n in found:
        try:
            lam.delete_function(FunctionName=n)
            _say(f"Deleted {n}.")
        except ClientError as e:
            _say(f"WARNING: delete {n} failed: {e.response['Error']['Code']}")


# ---------------------------------------------------------------------------
# 3. S3 objects (and optionally the bucket)
# ---------------------------------------------------------------------------

def cleanup_s3(env: dict, *, assume_yes: bool, dry_run: bool, delete_bucket: bool) -> None:
    session = boto3.Session(profile_name=env["PROFILE"], region_name=env["REGION"])
    s3 = session.client("s3")
    bucket = env.get("BUCKET")
    if not bucket:
        _say("No BUCKET in .env; skipping S3 cleanup.")
        return

    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        _say(f"Bucket '{bucket}' not accessible ({e.response['Error']['Code']}); skipping.")
        return

    keys: list[dict] = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=S3_PREFIX):
            for obj in page.get("Contents", []):
                keys.append({"Key": obj["Key"]})
    except ClientError as e:
        _say(f"WARNING: could not list s3://{bucket}/{S3_PREFIX} ({e.response['Error']['Code']}).")
        return

    if keys:
        _say(f"Found {len(keys)} object(s) under s3://{bucket}/{S3_PREFIX}.")
        if not dry_run and _confirm(
            f"Delete all {len(keys)} object(s) under '{S3_PREFIX}'?",
            assume_yes=assume_yes, dry_run=dry_run,
        ):
            for i in range(0, len(keys), 1000):
                batch = keys[i:i + 1000]
                try:
                    s3.delete_objects(Bucket=bucket, Delete={"Objects": batch})
                    _say(f"Deleted {len(batch)} object(s).")
                except ClientError as e:
                    _say(f"WARNING: delete batch failed: {e.response['Error']['Code']}")
    else:
        _say(f"No objects under s3://{bucket}/{S3_PREFIX}.")

    if not delete_bucket:
        return

    # Confirm bucket deletion separately — it's the most surprising op.
    if not _confirm(
        f"Also DELETE the bucket '{bucket}' itself? (must be fully empty)",
        assume_yes=assume_yes, dry_run=dry_run, default=False,
    ):
        _say("Keeping the bucket.")
        return

    # Quick non-prefix object check
    try:
        head = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        if head.get("KeyCount", 0) > 0:
            _say(f"WARNING: bucket '{bucket}' still has objects outside the tutorial prefix.")
            _say("Refusing to delete bucket — empty it manually first.")
            return
    except ClientError as e:
        _say(f"WARNING: could not verify bucket emptiness: {e.response['Error']['Code']}")
        return

    try:
        s3.delete_bucket(Bucket=bucket)
        _say(f"Deleted bucket '{bucket}'.")
    except ClientError as e:
        _say(f"WARNING: delete bucket failed: {e.response['Error']['Code']}")


# ---------------------------------------------------------------------------
# 4. IAM (caller inline policy + Lambda execution role)
# ---------------------------------------------------------------------------

def cleanup_caller_policy(env: dict, *, assume_yes: bool, dry_run: bool) -> None:
    session = boto3.Session(profile_name=env["PROFILE"], region_name=env["REGION"])
    try:
        ident = session.client("sts").get_caller_identity()
    except (NoCredentialsError, ClientError) as e:
        _say(f"WARNING: sts:GetCallerIdentity failed: {e}; skipping caller policy.")
        return
    kind, name = _caller_kind(ident["Arn"])
    if kind == "federated" or name is None:
        _say("Caller is federated/SSO; cannot detach inline policy automatically.")
        return

    _say(f"Caller is IAM {kind} '{name}'. Checking for inline policy '{CALLER_POLICY_NAME}'…")
    iam = session.client("iam")
    try:
        if kind == "user":
            iam.get_user_policy(UserName=name, PolicyName=CALLER_POLICY_NAME)
        else:
            iam.get_role_policy(RoleName=name, PolicyName=CALLER_POLICY_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            _say(f"No inline policy '{CALLER_POLICY_NAME}' on this {kind}.")
            return
        _say(f"WARNING: get policy failed: {e.response['Error']['Code']}; skipping.")
        return

    if dry_run:
        _say(f"Would delete inline policy '{CALLER_POLICY_NAME}' from {kind} '{name}'.")
        return
    if not _confirm(f"Delete inline policy '{CALLER_POLICY_NAME}' from {kind} '{name}'?",
                    assume_yes=assume_yes, dry_run=dry_run):
        _say("Skipping caller policy removal.")
        return
    try:
        if kind == "user":
            iam.delete_user_policy(UserName=name, PolicyName=CALLER_POLICY_NAME)
        else:
            iam.delete_role_policy(RoleName=name, PolicyName=CALLER_POLICY_NAME)
        _say(f"Removed inline policy from {kind} '{name}'.")
    except ClientError as e:
        _say(f"WARNING: delete policy failed: {e.response['Error']['Code']}")


def cleanup_lambda_role(env: dict, *, assume_yes: bool, dry_run: bool) -> None:
    session = boto3.Session(profile_name=env["PROFILE"], region_name=env["REGION"])
    iam = session.client("iam")
    try:
        iam.get_role(RoleName=LAMBDA_ROLE_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            _say(f"Lambda role '{LAMBDA_ROLE_NAME}' does not exist.")
            return
        _say(f"WARNING: get_role failed: {e.response['Error']['Code']}.")
        return

    if dry_run:
        _say(f"Would delete role '{LAMBDA_ROLE_NAME}' (after detaching policies).")
        return
    if not _confirm(f"Delete IAM role '{LAMBDA_ROLE_NAME}'?", assume_yes=assume_yes, dry_run=dry_run):
        _say("Skipping role deletion.")
        return

    try:
        for ap in iam.list_attached_role_policies(RoleName=LAMBDA_ROLE_NAME).get("AttachedPolicies", []):
            iam.detach_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyArn=ap["PolicyArn"])
            _say(f"  detached {ap['PolicyName']}.")
        for ip in iam.list_role_policies(RoleName=LAMBDA_ROLE_NAME).get("PolicyNames", []):
            iam.delete_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyName=ip)
            _say(f"  removed inline policy {ip}.")
        iam.delete_role(RoleName=LAMBDA_ROLE_NAME)
        _say(f"Deleted role '{LAMBDA_ROLE_NAME}'.")
    except ClientError as e:
        _say(f"WARNING: role delete failed: {e.response['Error']['Code']}")


# ---------------------------------------------------------------------------
# 5. Local .env
# ---------------------------------------------------------------------------

def cleanup_env_file(*, assume_yes: bool, dry_run: bool) -> None:
    if not ENV_FILE.exists():
        return
    if dry_run:
        _say(f"Would remove local file {ENV_FILE}.")
        return
    if not _confirm(f"Remove local file {ENV_FILE}?", assume_yes=assume_yes, dry_run=dry_run):
        _say("Keeping .env.")
        return
    ENV_FILE.unlink()
    _say(f"Removed {ENV_FILE}.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Tear down the APO tutorial environment.")
    p.add_argument("-y", "--yes", action="store_true",
                   help="Accept all destructive confirmations.")
    p.add_argument("--dry-run", action="store_true",
                   help="List what would be deleted; perform no changes.")
    p.add_argument("--delete-bucket", action="store_true",
                   help="Also delete the S3 bucket itself (after emptying the prefix).")
    p.add_argument("--keep-env", action="store_true",
                   help="Do not delete the local .env file.")
    p.add_argument("--keep-perms", action="store_true",
                   help="Do not touch the caller inline IAM policy or the Lambda role.")
    args = p.parse_args()

    env = _read_env()
    _say(f"Region:  {env.get('REGION')}")
    _say(f"Profile: {env.get('PROFILE')}")
    _say(f"Bucket:  {env.get('BUCKET')}")
    print()

    if args.dry_run:
        _say("DRY RUN — no changes will be made.\n")

    cleanup_apo_jobs(env, assume_yes=args.yes, dry_run=args.dry_run)
    print()
    cleanup_lambdas(env, assume_yes=args.yes, dry_run=args.dry_run)
    print()
    cleanup_s3(env, assume_yes=args.yes, dry_run=args.dry_run,
               delete_bucket=args.delete_bucket)
    print()
    if not args.keep_perms:
        cleanup_caller_policy(env, assume_yes=args.yes, dry_run=args.dry_run)
        print()
        cleanup_lambda_role(env, assume_yes=args.yes, dry_run=args.dry_run)
        print()
    else:
        _say("--keep-perms passed; leaving caller policy and Lambda role intact.")
        print()
    if not args.keep_env:
        cleanup_env_file(assume_yes=args.yes, dry_run=args.dry_run)

    if args.dry_run:
        print()
        _say("Dry run complete. Re-run without --dry-run to perform deletions.")
    else:
        print()
        _say("Cleanup finished.")


if __name__ == "__main__":
    main()
