#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Generate test scenarios for an AR policy.

Starts a GENERATE_POLICY_SCENARIOS build workflow, then fetches scenarios one at a time with
GetAutomatedReasoningPolicyNextScenario. Review each scenario: if it should be possible, save it as a
SATISFIABLE test (create_test.py); if not, it reveals a rule issue (hand to ar-policy-debugger).

Usage:
    uv run generate_scenarios.py --policy-arn <ARN> [--count 10] [--dry-run]
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
    p.add_argument("--count", type=int, default=10, help="Max scenarios to fetch.")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)

    # Need the current policy definition as sourceContent for the scenario workflow.
    if args.dry_run:
        policy_def = {"version": "1.0", "rules": [], "variables": [], "types": []}
    else:
        cur = ctx.call("bedrock", "get_automated_reasoning_policy", policyArn=args.policy_arn)
        policy_def = cur.get("policyDefinition", {"version": "1.0"})

    start = ctx.call(
        "bedrock",
        "start_automated_reasoning_policy_build_workflow",
        policyArn=args.policy_arn,
        buildWorkflowType="GENERATE_POLICY_SCENARIOS",
        sourceContent={"policyDefinition": policy_def},
    )
    ar.emit(start)
    if args.dry_run:
        return
    build_id = start.get("buildWorkflowId")
    ar.poll_build_workflow(ctx, args.policy_arn, build_id)

    scenarios = []
    for i in range(args.count):
        try:
            sc = ctx.call(
                "bedrock",
                "get_automated_reasoning_policy_next_scenario",
                policyArn=args.policy_arn,
                buildWorkflowId=build_id,
            )
        except Exception as e:  # noqa: BLE001 - no more scenarios / transient
            sys.stderr.write(f"[stop] no more scenarios ({e})\n")
            break
        if not sc or not sc.get("scenario"):
            break
        scenarios.append(sc)
    ar.emit({"buildWorkflowId": build_id, "scenarios": scenarios})
    sys.stderr.write(f"\nFetched {len(scenarios)} scenarios. Save good ones with create_test.py --expected SATISFIABLE.\n")


if __name__ == "__main__":
    main()
