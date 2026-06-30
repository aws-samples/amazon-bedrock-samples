#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Snapshot an AR policy's DRAFT into an immutable numbered version.

CreateAutomatedReasoningPolicyVersion requires the current definitionHash as a concurrency token;
this script fetches it from GetAutomatedReasoningPolicy first.

Usage:
    uv run create_version.py --policy-arn <ARN> [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--client-request-token", help="Idempotency token (optional).")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    if args.dry_run:
        definition_hash = "DRYRUN_HASH"
    else:
        cur = ctx.call("bedrock", "get_automated_reasoning_policy", policyArn=args.policy_arn)
        definition_hash = cur.get("definitionHash")
        if not definition_hash:
            sys.exit("Could not read definitionHash from the policy; cannot version safely.")

    params: dict = {"policyArn": args.policy_arn, "lastUpdatedDefinitionHash": definition_hash}
    if args.client_request_token:
        params["clientRequestToken"] = args.client_request_token
    resp = ctx.call("bedrock", "create_automated_reasoning_policy_version", **params)
    ar.emit(resp)
    if not args.dry_run:
        sys.stderr.write(f"\nCreated version {resp.get('version')}. Deploy with deploy_guardrail.py --policy-version {resp.get('version')}.\n")


if __name__ == "__main__":
    main()
