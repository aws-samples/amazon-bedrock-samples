#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Create an Automated Reasoning policy resource (step 1 of 2).

Returns the policyArn + DRAFT version. Follow with build_from_document.py to extract rules.

Usage:
    uv run create_policy.py --name MyHRPolicy --description "..." [--kms-key-id arn] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make shared/ar_common.py importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="Policy name (unique within account+region).")
    p.add_argument("--description", default="", help="Policy purpose.")
    p.add_argument("--kms-key-id", help="Customer-managed KMS key ARN (optional).")
    p.add_argument("--client-request-token", help="Idempotency token (optional).")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    params: dict = {"name": args.name}
    if args.description:
        params["description"] = args.description
    if args.kms_key_id:
        params["kmsKeyId"] = args.kms_key_id
    if args.client_request_token:
        params["clientRequestToken"] = args.client_request_token

    resp = ctx.call("bedrock", "create_automated_reasoning_policy", **params)
    ar.emit(resp)
    if not args.dry_run:
        arn = resp.get("policyArn")
        sys.stderr.write(f"\nCreated policy: {arn}\nNext: build_from_document.py --policy-arn {arn} --file <doc>\n")


if __name__ == "__main__":
    main()
