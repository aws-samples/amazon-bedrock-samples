#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Fetch a single build-workflow result asset for an AR policy.

Asset types: BUILD_LOG, QUALITY_REPORT, POLICY_DEFINITION, GENERATED_TEST_CASES,
POLICY_SCENARIOS, FIDELITY_REPORT, ASSET_MANIFEST, SOURCE_DOCUMENT (needs --asset-id).

Usage:
    uv run get_assets.py --policy-arn <ARN> --asset-type QUALITY_REPORT [--build-workflow-id <id>]
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
    p.add_argument("--asset-type", required=True, choices=ar.ASSET_TYPES)
    p.add_argument("--build-workflow-id", help="Defaults to the latest COMPLETED build.")
    p.add_argument("--asset-id", help="Required for SOURCE_DOCUMENT when multiple docs were used.")
    ar.add_common_args(p)
    args = p.parse_args()

    if args.asset_type == "SOURCE_DOCUMENT" and not args.asset_id:
        sys.exit("--asset-id is required for SOURCE_DOCUMENT (get it from the ASSET_MANIFEST).")

    ctx = ar.ctx_from_args(args)
    build_id = args.build_workflow_id or ar.latest_completed_build_id(ctx, args.policy_arn)
    if not build_id:
        sys.exit("No COMPLETED build workflow found for this policy. Build it first.")
    resp = ar.get_result_asset(ctx, args.policy_arn, build_id, args.asset_type, args.asset_id)
    ar.emit(resp)


if __name__ == "__main__":
    main()
