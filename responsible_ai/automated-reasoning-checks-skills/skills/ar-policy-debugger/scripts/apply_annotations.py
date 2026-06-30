#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Apply annotations to an AR policy via the REFINE_POLICY build workflow.

Reads a JSON file containing an array of annotation objects (see
ar-policy-debugger/references/debugging-decisions.md for recipes), fetches the current policy
definition, and starts the refine build. Optionally commits the refined definition to DRAFT.

Usage:
    uv run apply_annotations.py --policy-arn <ARN> --annotations-file fixes.json [--commit] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--annotations-file", required=True, help="JSON array of annotation objects.")
    p.add_argument("--commit", action="store_true",
                   help="After build, fetch refined POLICY_DEFINITION and UpdateAutomatedReasoningPolicy (DRAFT).")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    annotations = json.loads(Path(args.annotations_file).read_text())
    if not isinstance(annotations, list):
        sys.exit("Annotations file must contain a JSON array of annotation objects.")

    if args.dry_run:
        policy_def = {"version": "1.0", "rules": [], "variables": [], "types": []}
    else:
        cur = ctx.call("bedrock", "get_automated_reasoning_policy", policyArn=args.policy_arn)
        policy_def = cur.get("policyDefinition", {"version": "1.0"})
        policy_def.setdefault("version", "1.0")

    start = ctx.call(
        "bedrock",
        "start_automated_reasoning_policy_build_workflow",
        policyArn=args.policy_arn,
        buildWorkflowType="REFINE_POLICY",
        sourceContent={
            "policyDefinition": policy_def,
            "workflowContent": {"policyRepairAssets": {"annotations": annotations}},
        },
    )
    ar.emit(start)
    if args.dry_run:
        return

    build_id = start.get("buildWorkflowId")
    ar.poll_build_workflow(ctx, args.policy_arn, build_id)
    refined = ar.get_result_asset(ctx, args.policy_arn, build_id, "POLICY_DEFINITION")
    ar.emit({"refinedDefinition": refined})

    if args.commit:
        new_def = refined.get("policyDefinition") or refined.get("buildWorkflowAssets", {}).get("policyDefinition")
        if not new_def:
            sys.exit("Could not locate refined policyDefinition in assets; commit manually.")
        upd = ctx.call(
            "bedrock", "update_automated_reasoning_policy", policyArn=args.policy_arn, policyDefinition=new_def
        )
        ar.emit(upd)
        sys.stderr.write("\nCommitted refined definition to DRAFT. Re-run reviewer + tester.\n")
    else:
        sys.stderr.write("\nReview the refined definition above, then re-run with --commit (or edit and UpdateAutomatedReasoningPolicy).\n")


if __name__ == "__main__":
    main()
