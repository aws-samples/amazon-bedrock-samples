#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Refine an AR policy using an updated document + natural-language feedback (ITERATIVELY_REFINE_POLICY).

Unlike INGEST_CONTENT (which extracts NEW rules from a document), this uses the document as context to
improve the EXISTING policy. Good for: source-doc revisions, fixing failed tests with guidance, or
adding concepts the policy is missing.

Usage:
    uv run iteratively_refine.py --policy-arn <ARN> --file updated.pdf \
        --feedback "Change parental-leave tenure from 12 to 6 months (section 3)." [--commit] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402

MAX_BYTES = 5 * 1024 * 1024


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--file", required=True, help="Document used as refinement context (PDF/text).")
    p.add_argument("--feedback", default="", help="Natural-language instructions for the refinement.")
    p.add_argument("--doc-name", default="Refinement context")
    p.add_argument("--commit", action="store_true", help="Commit the refined definition to DRAFT.")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    path = Path(args.file)
    if not path.exists():
        sys.exit(f"File not found: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        sys.exit("Document exceeds the 5 MB AR limit.")
    ctype = "pdf" if path.suffix.lower() == ".pdf" else "txt"

    if args.dry_run:
        policy_def = {"version": "1.0"}
    else:
        cur = ctx.call("bedrock", "get_automated_reasoning_policy", policyArn=args.policy_arn)
        policy_def = cur.get("policyDefinition", {"version": "1.0"})
        policy_def.setdefault("version", "1.0")

    # document is a BLOB — pass raw bytes (boto3 base64-encodes blobs itself).
    refinement: dict = {"documents": [{"document": raw, "documentContentType": ctype, "documentName": args.doc_name}]}
    if args.feedback:
        refinement["feedback"] = args.feedback

    start = ctx.call(
        "bedrock",
        "start_automated_reasoning_policy_build_workflow",
        policyArn=args.policy_arn,
        buildWorkflowType="ITERATIVELY_REFINE_POLICY",
        sourceContent={"policyDefinition": policy_def, "workflowContent": {"iterativeRefinementContent": refinement}},
    )
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
