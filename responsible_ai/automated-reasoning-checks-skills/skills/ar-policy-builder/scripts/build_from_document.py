#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Build (or merge into) an AR policy from a source document via INGEST_CONTENT (step 2 of 2).

Base64-encodes the document, starts the build workflow, and polls until COMPLETED.
With --merge, fetches the current policy definition and includes it so new rules merge
instead of replacing the existing policy.

Usage:
    uv run build_from_document.py --policy-arn <ARN> --file leave.pdf \
        --doc-name "HR Leave Policy" --doc-description "..." --instructions "..." [--merge] [--dry-run]

Notes:
    * Source documents must be <= 5 MB and <= 50,000 characters (images/tables count).
    * Max 2 build workflows per policy; only 1 IN_PROGRESS. Delete an old one first if needed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _content_type(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return {"pdf": "pdf", "txt": "txt", "md": "txt"}.get(ext, "txt")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--file", required=True, help="Path to the source document (PDF or text).")
    p.add_argument("--doc-name", required=True, help="Short document name.")
    p.add_argument("--doc-description", default="", help="What the doc covers + sample user questions.")
    p.add_argument("--instructions", default="", help="(Recommended) extraction guidance: use case, example questions, focus.")
    p.add_argument("--merge", action="store_true", help="Merge into the existing policy definition (fetches current).")
    p.add_argument("--no-poll", action="store_true", help="Start the build but don't wait for completion.")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    path = Path(args.file)
    if not path.exists():
        sys.exit(f"File not found: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        sys.exit(f"Document is {len(raw)} bytes; AR limit is 5 MB. Split into focused sections.")

    # Starting policy definition: empty, or the current one when merging.
    policy_def: dict = {"version": "1.0", "types": [], "rules": [], "variables": []}
    if args.merge:
        if args.dry_run:
            sys.stderr.write("[dry-run] would fetch current policy definition for merge\n")
        else:
            cur = ctx.call("bedrock", "get_automated_reasoning_policy", policyArn=args.policy_arn)
            policy_def = cur.get("policyDefinition", policy_def)
            policy_def.setdefault("version", "1.0")

    # documents[].document is a BLOB; pass RAW BYTES. boto3 base64-encodes blobs itself,
    # so handing it a base64 string would double-encode and the service extracts nothing.
    description = args.doc_description
    if args.instructions:
        description = (description + "\n\nInstructions: " + args.instructions).strip()
    document: dict = {"document": raw, "documentContentType": _content_type(path), "documentName": args.doc_name}
    if description:
        document["documentDescription"] = description

    source_content: dict = {"policyDefinition": policy_def, "workflowContent": {"documents": [document]}}
    params: dict = {
        "policyArn": args.policy_arn,
        "buildWorkflowType": "INGEST_CONTENT",
        "sourceContent": source_content,
    }

    resp = ctx.call("bedrock", "start_automated_reasoning_policy_build_workflow", **params)
    ar.emit(resp)

    if args.dry_run or args.no_poll:
        return
    build_id = resp.get("buildWorkflowId")
    final = ar.poll_build_workflow(ctx, args.policy_arn, build_id)
    status = final.get("status")
    sys.stderr.write(f"\nBuild {build_id} finished: {status}\n")
    if status == "COMPLETED":
        sys.stderr.write("Next: run ar-policy-reviewer on this policy ARN to check quality + fidelity reports.\n")
    else:
        sys.stderr.write("Build did not complete cleanly. Fetch the BUILD_LOG asset to investigate.\n")


if __name__ == "__main__":
    main()
