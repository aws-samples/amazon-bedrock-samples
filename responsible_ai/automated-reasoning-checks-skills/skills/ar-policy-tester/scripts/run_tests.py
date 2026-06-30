#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Run an AR policy's test cases and collect results.

Starts a test workflow against the latest COMPLETED build (or --build-workflow-id), then lists results.

Usage:
    uv run run_tests.py --policy-arn <ARN> [--test-case-ids id1 id2] [--build-workflow-id <id>] [--dry-run]
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
    p.add_argument("--test-case-ids", nargs="*", help="Specific test ids (default: all tests).")
    p.add_argument("--build-workflow-id", help="Defaults to the latest COMPLETED build.")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    build_id = args.build_workflow_id or ar.latest_completed_build_id(ctx, args.policy_arn)
    if not build_id and not args.dry_run:
        sys.exit("No COMPLETED build workflow found. Build the policy first.")
    build_id = build_id or "DRYRUN_BUILD_ID"

    start_params: dict = {"policyArn": args.policy_arn, "buildWorkflowId": build_id}
    if args.test_case_ids:
        start_params["testCaseIds"] = args.test_case_ids
    start = ctx.call("bedrock", "start_automated_reasoning_policy_test_workflow", **start_params)
    ar.emit(start)
    if args.dry_run:
        return

    # Which test cases to report on.
    case_ids = args.test_case_ids
    if not case_ids:
        listing = ctx.call("bedrock", "list_automated_reasoning_policy_test_cases", policyArn=args.policy_arn)
        cases = listing.get("testCases") or listing.get("automatedReasoningPolicyTestCaseSummaries") or []
        case_ids = [c.get("testCaseId") for c in cases if c.get("testCaseId")]
    if not case_ids:
        sys.exit("No test cases found for this policy. Create some with create_test.py.")

    # Fetch each result via Get (per-case) — more reliable than the List op on some service
    # versions. Poll briefly until each test leaves a non-terminal state.
    import time

    rows = []
    for cid in case_ids:
        res = None
        for _ in range(12):  # up to ~60s
            res = ctx.call("bedrock", "get_automated_reasoning_policy_test_result",
                           policyArn=args.policy_arn, buildWorkflowId=build_id, testCaseId=cid)
            tr = res.get("testResult", res)
            if str(tr.get("testRunStatus", "")).upper() in ("COMPLETED", "FAILED", ""):
                break
            time.sleep(5)
        tr = (res or {}).get("testResult", res or {})
        tc = tr.get("testCase", {})
        expected = tc.get("expectedAggregatedFindingsResult")
        findings = tr.get("testFindings", [])
        actual = ar.aggregate_result(
            [ar.Finding(result=next((ar.FINDING_KEY_TO_RESULT[k] for k in ar.FINDING_KEY_TO_RESULT if k in f), "UNKNOWN"), raw=f) for f in findings]
        ) if findings else None
        passed = (expected == actual) if actual else None
        rows.append({"testCaseId": cid, "expected": expected, "actual": actual,
                     "status": tr.get("testRunStatus"), "passed": passed})

    ar.emit({"buildWorkflowId": build_id, "results": rows})
    npass = sum(1 for r in rows if r["passed"])
    sys.stderr.write(f"\n{npass}/{len(rows)} tests passed. Failures -> ar-policy-debugger.\n")


if __name__ == "__main__":
    main()
