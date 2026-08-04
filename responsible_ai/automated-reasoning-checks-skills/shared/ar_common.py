#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Shared helpers for Amazon Bedrock Automated Reasoning (AR) skill scripts.

Every AR skill script imports from this module. It centralizes:
  - boto3 client creation (control plane `bedrock`, runtime `bedrock-runtime`)
  - a --dry-run mechanism that prints the request instead of calling AWS
  - build-workflow polling
  - result-asset fetching + JSON decode
  - finding parsing (the tagged-union -> typed result)
  - the `automatedReasoningPolicyUnits > 0` safety guard
  - exponential-backoff retry around throttled/transient calls
  - small CLI argument helpers shared across scripts

This file is also runnable directly for a self-test:
    uv run ar_common.py --help
    uv run ar_common.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

DEFAULT_REGION = "us-east-1"

# Severity order, worst -> best. The aggregated result is the worst finding present.
SEVERITY_ORDER = [
    "TRANSLATION_AMBIGUOUS",
    "IMPOSSIBLE",
    "INVALID",
    "SATISFIABLE",
    "VALID",
]
# These sit outside the severity ordering and are handled separately.
OUT_OF_BAND_RESULTS = ["TOO_COMPLEX", "NO_TRANSLATIONS"]

# Maps the union key returned in a finding to the canonical result name.
FINDING_KEY_TO_RESULT = {
    "valid": "VALID",
    "invalid": "INVALID",
    "satisfiable": "SATISFIABLE",
    "impossible": "IMPOSSIBLE",
    "translationAmbiguous": "TRANSLATION_AMBIGUOUS",
    "tooComplex": "TOO_COMPLEX",
    "noTranslations": "NO_TRANSLATIONS",
}

# Valid enum values pulled from the Bedrock User Guide, for arg validation + docs.
BUILD_WORKFLOW_TYPES = [
    "INGEST_CONTENT",
    "REFINE_POLICY",
    "IMPORT_POLICY",
    "GENERATE_FIDELITY_REPORT",
    "GENERATE_POLICY_SCENARIOS",
    "RESOLVE_POLICY_AMBIGUITIES",
    "ITERATIVELY_REFINE_POLICY",
]
ASSET_TYPES = [
    "BUILD_LOG",
    "QUALITY_REPORT",
    "POLICY_DEFINITION",
    "GENERATED_TEST_CASES",
    "POLICY_SCENARIOS",
    "FIDELITY_REPORT",
    "ASSET_MANIFEST",
    "SOURCE_DOCUMENT",
]
TERMINAL_BUILD_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}

# A policy allows at most this many build workflows per pool, with at most 1 active.
# Builds are partitioned into two pools that are counted separately: fidelity-report
# builds vs. everything else. (Mirrors manageBuildSlot in the ARchitect sample.)
MAX_BUILDS_PER_POOL = 2
FIDELITY_BUILD_TYPES = {"GENERATE_FIDELITY_REPORT"}


# --------------------------------------------------------------------------- #
# Clients + dry-run
# --------------------------------------------------------------------------- #
@dataclass
class ARContext:
    """Holds clients + flags threaded through a script run."""

    region: str = DEFAULT_REGION
    dry_run: bool = False
    _bedrock: Any = field(default=None, repr=False)
    _runtime: Any = field(default=None, repr=False)

    @property
    def bedrock(self):
        """Control-plane client (policies, build workflows, tests, guardrails)."""
        if self._bedrock is None:
            import boto3

            self._bedrock = boto3.client("bedrock", region_name=self.region)
        return self._bedrock

    @property
    def runtime(self):
        """Runtime client (apply_guardrail, converse)."""
        if self._runtime is None:
            import boto3

            self._runtime = boto3.client("bedrock-runtime", region_name=self.region)
        return self._runtime

    def call(self, client_name: str, method: str, **params) -> dict:
        """Invoke a boto3 method, or print it under --dry-run.

        client_name: "bedrock" or "bedrock-runtime".
        Returns the API response dict, or a stub {"dryRun": True, ...} when dry.
        """
        if self.dry_run:
            # Note to stderr so the script's own emit() of the returned stub stays the
            # single machine-readable stdout artifact (no double-print).
            sys.stderr.write(f"[dry-run] {client_name}.{method}\n")
            return {"dryRun": True, "client": client_name, "method": method, "params": _trim_for_print(params)}
        client = self.bedrock if client_name == "bedrock" else self.runtime
        fn = getattr(client, method)
        return retry_call(lambda: fn(**params))


def _trim_for_print(params: dict) -> dict:
    """Shorten huge base64 blobs so --dry-run output stays readable."""
    out: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 200:
            out[k] = f"<{len(v)} chars omitted>"
        elif isinstance(v, dict):
            out[k] = _trim_for_print(v)
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------- #
# Retry
# --------------------------------------------------------------------------- #
RETRYABLE = {
    "ThrottlingException",
    "TooManyRequestsException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelTimeoutException",
}


def retry_call(fn: Callable[[], dict], max_retries: int = 3, base_delay: float = 1.0) -> dict:
    """Call `fn`, retrying transient Bedrock errors with exponential backoff."""
    from botocore.exceptions import ClientError

    attempt = 0
    while True:
        try:
            return fn()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in RETRYABLE and attempt < max_retries:
                delay = base_delay * (2**attempt)
                sys.stderr.write(f"[retry] {code}; sleeping {delay:.1f}s\n")
                time.sleep(delay)
                attempt += 1
                continue
            raise


# --------------------------------------------------------------------------- #
# Build-workflow polling + assets
# --------------------------------------------------------------------------- #
def poll_build_workflow(
    ctx: ARContext,
    policy_arn: str,
    build_workflow_id: str,
    interval: float = 10.0,
    timeout: float = 1800.0,
) -> dict:
    """Poll a build workflow until it reaches a terminal status. Returns last response."""
    if ctx.dry_run:
        print(f"[dry-run] would poll build workflow {build_workflow_id}")
        return {"dryRun": True, "status": "COMPLETED"}
    waited = 0.0
    while True:
        resp = ctx.call(
            "bedrock",
            "get_automated_reasoning_policy_build_workflow",
            policyArn=policy_arn,
            buildWorkflowId=build_workflow_id,
        )
        status = resp.get("status") or resp.get("buildWorkflowStatus")
        sys.stderr.write(f"[build] {build_workflow_id} -> {status}\n")
        if status in TERMINAL_BUILD_STATUSES:
            return resp
        if waited >= timeout:
            raise TimeoutError(f"Build {build_workflow_id} not terminal after {timeout}s (last={status})")
        time.sleep(interval)
        waited += interval


def get_result_asset(ctx: ARContext, policy_arn: str, build_workflow_id: str, asset_type: str, asset_id: str | None = None) -> Any:
    """Fetch one build result asset and return the raw API response.

    Returns the full response dict. The payload itself is nested under
    `buildWorkflowAssets` (see `asset_payload` to unwrap it). Not every asset
    exists for every build type (e.g. FIDELITY_REPORT is absent on REFINE_POLICY
    builds), so callers should use `try_get_result_asset` when an asset is optional.
    """
    if asset_type not in ASSET_TYPES:
        raise ValueError(f"asset_type must be one of {ASSET_TYPES}")
    params = dict(policyArn=policy_arn, buildWorkflowId=build_workflow_id, assetType=asset_type)
    if asset_id:
        params["assetId"] = asset_id
    return ctx.call("bedrock", "get_automated_reasoning_policy_build_workflow_result_assets", **params)


def try_get_result_asset(ctx: ARContext, policy_arn: str, build_workflow_id: str, asset_type: str, asset_id: str | None = None) -> Any | None:
    """Like get_result_asset, but returns None if the asset doesn't exist for this build."""
    from botocore.exceptions import ClientError

    try:
        return get_result_asset(ctx, policy_arn, build_workflow_id, asset_type, asset_id)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
            return None
        raise


def asset_payload(resp: dict, key: str | None = None) -> Any:
    """Unwrap the `buildWorkflowAssets.<key>` payload from a result-asset response.

    The API wraps every asset under `buildWorkflowAssets`, e.g.
    `buildWorkflowAssets.policyDefinition` or `.qualityReport`. With no key, returns
    the inner dict's single value. Returns {} if absent.
    """
    if not isinstance(resp, dict):
        return {}
    assets = resp.get("buildWorkflowAssets", resp)
    if key:
        return assets.get(key, {})
    # no key: return the one nested asset if there's exactly one
    if isinstance(assets, dict) and len(assets) == 1:
        return next(iter(assets.values()))
    return assets


def latest_completed_build_id(ctx: ARContext, policy_arn: str) -> str | None:
    """Return the id of the most recent COMPLETED build workflow, or None."""
    if ctx.dry_run:
        return "DRYRUN_BUILD_ID"
    resp = ctx.call("bedrock", "list_automated_reasoning_policy_build_workflows", policyArn=policy_arn)
    summaries = resp.get("automatedReasoningPolicyBuildWorkflowSummaries", [])
    completed = [s for s in summaries if s.get("status") == "COMPLETED"]
    if not completed:
        return None
    completed.sort(key=lambda s: s.get("updatedAt") or s.get("createdAt") or "", reverse=True)
    return completed[0].get("buildWorkflowId")


# --------------------------------------------------------------------------- #
# Build-slot management (the "too many build workflows" fix)
# --------------------------------------------------------------------------- #
def _is_fidelity_build(build_type: str | None) -> bool:
    """Fidelity-report builds are counted in a separate pool from policy builds."""
    return (build_type or "") in FIDELITY_BUILD_TYPES


def list_builds(ctx: ARContext, policy_arn: str) -> list[dict]:
    """Return the policy's build-workflow summaries (id, status, type, timestamps)."""
    resp = ctx.call(
        "bedrock", "list_automated_reasoning_policy_build_workflows", policyArn=policy_arn, maxResults=50
    )
    return resp.get("automatedReasoningPolicyBuildWorkflowSummaries", [])


def delete_build(ctx: ARContext, policy_arn: str, build_workflow_id: str, last_updated_at: Any) -> dict:
    """Delete one build workflow. `last_updated_at` is the summary's updatedAt (a concurrency token)."""
    return ctx.call(
        "bedrock",
        "delete_automated_reasoning_policy_build_workflow",
        policyArn=policy_arn,
        buildWorkflowId=build_workflow_id,
        lastUpdatedAt=last_updated_at,
    )


def ensure_build_slot(ctx: ARContext, policy_arn: str, build_type: str) -> None:
    """Free a build slot before starting a new build, so we never hit the per-policy cap.

    A policy allows at most MAX_BUILDS_PER_POOL build workflows per pool (fidelity-report builds
    vs. everything else), counted separately. If the relevant pool is at capacity, delete the
    OLDEST terminal build (COMPLETED/FAILED/CANCELLED) to free a slot. Never touches an in-progress
    build. Raises if every slot in the pool is occupied by an in-progress build.

    Mirrors manageBuildSlot in the ARchitect sample
    (github.com/aws-samples/sample-automated-reasoning-formalization, src/services/policy-service.ts).
    """
    if ctx.dry_run:
        sys.stderr.write(f"[dry-run] would ensure a free build slot for {build_type}\n")
        return
    is_fidelity = _is_fidelity_build(build_type)
    pool = [b for b in list_builds(ctx, policy_arn) if _is_fidelity_build(b.get("buildWorkflowType")) == is_fidelity]
    if len(pool) < MAX_BUILDS_PER_POOL:
        return
    terminal = sorted(
        (b for b in pool if b.get("status") in TERMINAL_BUILD_STATUSES),
        key=lambda b: b.get("createdAt") or "",
    )
    pool_name = "fidelity-report" if is_fidelity else "policy"
    if not terminal:
        raise RuntimeError(
            f"All {MAX_BUILDS_PER_POOL} {pool_name} build slots are in use by in-progress builds. "
            "Wait for one to complete, then retry."
        )
    oldest = terminal[0]
    sys.stderr.write(f"[slot] freeing a {pool_name} build slot: deleting old build {oldest.get('buildWorkflowId')} ({oldest.get('status')})\n")
    delete_build(ctx, policy_arn, oldest["buildWorkflowId"], oldest.get("updatedAt"))


def start_build(ctx: ARContext, policy_arn: str, build_type: str, source_content: dict, client_request_token: str | None = None) -> dict:
    """Free a slot, then start a build workflow. Returns the start response (with buildWorkflowId)."""
    ensure_build_slot(ctx, policy_arn, build_type)
    params: dict = {"policyArn": policy_arn, "buildWorkflowType": build_type, "sourceContent": source_content}
    if client_request_token:
        params["clientRequestToken"] = client_request_token
    return ctx.call("bedrock", "start_automated_reasoning_policy_build_workflow", **params)


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    result: str
    raw: dict

    @property
    def translation(self) -> dict:
        return self.raw.get(_result_to_key(self.result), {}).get("translation", {})


def _result_to_key(result: str) -> str:
    for key, name in FINDING_KEY_TO_RESULT.items():
        if name == result:
            return key
    return ""


def parse_findings(apply_guardrail_response: dict) -> list[Finding]:
    """Extract typed findings from an ApplyGuardrail/Converse response."""
    findings: list[Finding] = []
    for assessment in apply_guardrail_response.get("assessments", []):
        ar = assessment.get("automatedReasoningPolicy", {})
        for raw in ar.get("findings", []):
            result = next((FINDING_KEY_TO_RESULT[k] for k in FINDING_KEY_TO_RESULT if k in raw), "UNKNOWN")
            findings.append(Finding(result=result, raw=raw))
    return findings


def aggregate_result(findings: Iterable[Finding]) -> str:
    """Worst-severity result across findings (the 'aggregated' result). VALID if none."""
    results = [f.result for f in findings]
    for sev in SEVERITY_ORDER:  # worst first
        if sev in results:
            return sev
    for ob in OUT_OF_BAND_RESULTS:
        if ob in results:
            return ob
    return "VALID"


def assert_ar_ran(apply_guardrail_response: dict) -> int:
    """Guard against the silent-skip trap.

    A misconfigured (untagged) request still succeeds but runs no AR checks, returning
    automatedReasoningPolicyUnits == 0. Raise so the caller notices.
    Returns the unit count when > 0.
    """
    usage = apply_guardrail_response.get("usage", {})
    units = usage.get("automatedReasoningPolicyUnits", usage.get("automatedReasoningPolicies", 0))
    if not units:
        raise RuntimeError(
            "automatedReasoningPolicyUnits == 0: Automated Reasoning did NOT run. "
            "Check that content is tagged (guard_content / a guardContent block) and the "
            "guardrail has an AR policy attached."
        )
    return units


# --------------------------------------------------------------------------- #
# CLI helpers
# --------------------------------------------------------------------------- #
def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add --region and --dry-run, used by every script."""
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", DEFAULT_REGION),
        help=f"AWS region (default: {DEFAULT_REGION} or $AWS_REGION).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the API request(s) instead of calling AWS.",
    )


def ctx_from_args(args: argparse.Namespace) -> ARContext:
    return ARContext(region=getattr(args, "region", DEFAULT_REGION), dry_run=getattr(args, "dry_run", False))


def emit(obj: Any) -> None:
    """Print a result as pretty JSON to stdout (the script's machine-readable output)."""
    print(json.dumps(obj, indent=2, default=str))


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def _selftest() -> None:
    sample = {
        "usage": {"automatedReasoningPolicyUnits": 2},
        "assessments": [
            {
                "automatedReasoningPolicy": {
                    "findings": [
                        {"valid": {"translation": {"confidence": 1.0}}},
                        {"invalid": {"contradictingRules": [{"identifier": "R3"}]}},
                    ]
                }
            }
        ],
    }
    findings = parse_findings(sample)
    assert [f.result for f in findings] == ["VALID", "INVALID"], findings
    assert aggregate_result(findings) == "INVALID"
    assert assert_ar_ran(sample) == 2
    empty = {"usage": {"automatedReasoningPolicyUnits": 0}}
    try:
        assert_ar_ran(empty)
    except RuntimeError:
        pass
    else:
        raise AssertionError("assert_ar_ran should have raised on 0 units")
    print("ar_common self-test: OK")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Shared AR helpers (library). Run --selftest to verify.")
    p.add_argument("--selftest", action="store_true", help="Run internal sanity checks (no AWS).")
    args = p.parse_args()
    if args.selftest:
        _selftest()
    else:
        p.print_help()
