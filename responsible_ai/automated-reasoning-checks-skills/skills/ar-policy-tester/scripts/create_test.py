#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Create a QnA test case for an AR policy.

The OUTPUT (foundation-model answer) is required and is validated; the INPUT (user question) is
optional context. expected = the worst-severity aggregated result you expect.

Usage:
    uv run create_test.py --policy-arn <ARN> --output "<answer>" [--input "<question>"] \
        --expected VALID [--confidence 0.8] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402

EXPECTED_CHOICES = ar.SEVERITY_ORDER + ar.OUT_OF_BAND_RESULTS


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--output", required=True, help="The model answer to validate (guardContent).")
    p.add_argument("--input", help="The user question (the `query`, optional context).")
    p.add_argument("--expected", choices=EXPECTED_CHOICES, required=True, help="Expected aggregated result (required).")
    p.add_argument("--confidence", type=float, help="Confidence threshold 0.0-1.0 (optional).")
    p.add_argument("--client-request-token", help="Idempotency token (optional).")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    params: dict = {
        "policyArn": args.policy_arn,
        "guardContent": args.output,
        "expectedAggregatedFindingsResult": args.expected,
    }
    if args.input:
        params["query"] = args.input
    if args.confidence is not None:
        params["confidenceThreshold"] = args.confidence
    if args.client_request_token:
        params["clientRequestToken"] = args.client_request_token

    resp = ctx.call("bedrock", "create_automated_reasoning_policy_test_case", **params)
    ar.emit(resp)
    if not args.dry_run:
        sys.stderr.write(f"\nCreated test {resp.get('testCaseId')}. Run with run_tests.py.\n")


if __name__ == "__main__":
    main()
