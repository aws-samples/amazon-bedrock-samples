#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Auto-resolve ambiguous variable descriptions/types via RESOLVE_POLICY_AMBIGUITIES.

Use when many TRANSLATION_AMBIGUOUS results stem from overlapping/vague variable descriptions.
After the build, retrieve the refined POLICY_DEFINITION and (optionally) commit it to DRAFT.

Usage:
    uv run resolve_ambiguities.py --policy-arn <ARN> [--commit] [--dry-run]
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
    p.add_argument("--commit", action="store_true", help="Commit the refined definition to DRAFT.")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    if args.dry_run:
        policy_def = {"version": "1.0"}
    else:
        cur = ctx.call("bedrock", "get_automated_reasoning_policy", policyArn=args.policy_arn)
        policy_def = cur.get("policyDefinition", {"version": "1.0"})
        policy_def.setdefault("version", "1.0")

    # start_build frees a build slot first (deletes an old terminal build if at the cap).
    start = ar.start_build(ctx, args.policy_arn, "RESOLVE_POLICY_AMBIGUITIES", {"policyDefinition": policy_def})
    ar.emit(start)
    if args.dry_run:
        return

    build_id = start.get("buildWorkflowId")
    if not build_id:
        sys.exit(f"No buildWorkflowId in start response: {start}")
    ar.poll_build_workflow(ctx, args.policy_arn, build_id)
    refined = ar.get_result_asset(ctx, args.policy_arn, build_id, "POLICY_DEFINITION")
    ar.emit({"refinedDefinition": refined})

    if args.commit:
        new_def = refined.get("policyDefinition") or refined.get("buildWorkflowAssets", {}).get("policyDefinition")
        if new_def:
            ctx.call("bedrock", "update_automated_reasoning_policy", policyArn=args.policy_arn, policyDefinition=new_def)
            sys.stderr.write("\nCommitted to DRAFT. Re-run reviewer + tester.\n")


if __name__ == "__main__":
    main()
