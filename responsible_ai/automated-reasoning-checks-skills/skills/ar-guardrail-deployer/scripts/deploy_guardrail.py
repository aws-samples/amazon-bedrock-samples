#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Attach an AR policy version to a Bedrock Guardrail (idempotent create-or-update by name).

Looks up the guardrail by name; creates it if absent, updates it if present, then creates a guardrail
version. Includes the required automatedReasoningPolicyConfig + crossRegionConfig (guardrail profile
derived from the policy ARN's account + region).

Usage:
    uv run deploy_guardrail.py --policy-arn <ARN> --policy-version 1 \
        [--guardrail-name ar-guardrail] [--confidence 1.0] [--profile-id us.guardrail.v1:0] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402

DEFAULT_PROFILE = "us.guardrail.v1:0"


def parse_arn(policy_arn: str) -> tuple[str, str]:
    """Return (region, account) from an AR policy ARN."""
    # arn:aws:bedrock:REGION:ACCOUNT:automated-reasoning-policy/ID
    parts = policy_arn.split(":")
    if len(parts) < 6:
        raise ValueError(f"Unexpected policy ARN: {policy_arn}")
    return parts[3], parts[4]


def find_guardrail(ctx: ar.ARContext, name: str) -> dict | None:
    resp = ctx.call("bedrock", "list_guardrails")
    for g in resp.get("guardrails", []):
        if g.get("name") == name:
            return g
    return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--policy-version", required=True, help="Numbered policy version to attach.")
    p.add_argument("--guardrail-name", default="ar-guardrail")
    p.add_argument("--confidence", type=float, default=1.0, help="Confidence threshold (default 1.0).")
    p.add_argument("--profile-id", default=DEFAULT_PROFILE, help=f"Guardrail profile id (default {DEFAULT_PROFILE}).")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    region, account = parse_arn(args.policy_arn)
    profile_arn = f"arn:aws:bedrock:{region}:{account}:guardrail-profile/{args.profile_id}"

    # automatedReasoningPolicyConfig.policies is a REQUIRED list of versioned policy ARNs
    # (e.g. arn:...:automated-reasoning-policy/<id>:<version>). Build the versioned ARN.
    versioned_arn = args.policy_arn if ":" in args.policy_arn.split("/")[-1] else f"{args.policy_arn}:{args.policy_version}"
    ar_config = {
        "policies": [versioned_arn],
        "confidenceThreshold": args.confidence,
    }
    cross_region = {"guardrailProfileIdentifier": profile_arn}
    base = dict(
        name=args.guardrail_name,
        automatedReasoningPolicyConfig=ar_config,
        crossRegionConfig=cross_region,
        blockedInputMessaging="Input blocked by guardrail.",
        blockedOutputsMessaging="Output blocked by guardrail.",
    )

    existing = None if args.dry_run else find_guardrail(ctx, args.guardrail_name)
    if existing:
        gid = existing.get("id") or existing.get("guardrailId")
        resp = ctx.call("bedrock", "update_guardrail", guardrailIdentifier=gid, **base)
    else:
        resp = ctx.call("bedrock", "create_guardrail", **base)
    ar.emit(resp)
    if args.dry_run:
        return

    gid = resp.get("guardrailId") or resp.get("id") or (existing or {}).get("id")
    ver = ctx.call("bedrock", "create_guardrail_version", guardrailIdentifier=gid)
    ar.emit(ver)
    sys.stderr.write(
        f"\nGuardrail {gid} version {ver.get('version')} ready. "
        f"Validate with ar-runtime-validator --guardrail-id {gid} --guardrail-version {ver.get('version')}.\n"
    )


if __name__ == "__main__":
    main()
