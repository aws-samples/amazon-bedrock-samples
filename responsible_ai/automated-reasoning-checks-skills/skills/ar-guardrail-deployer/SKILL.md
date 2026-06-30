---
name: ar-guardrail-deployer
description: >
  Versions an Amazon Bedrock Automated Reasoning (AR) policy and attaches it to a Bedrock Guardrail for
  production use. Creates an immutable numbered policy version, then creates or updates a guardrail with
  the required automatedReasoningPolicyConfig and cross-region guardrail profile.

  Use this skill whenever the user wants to:
  - "Deploy my Automated Reasoning policy" / "attach my AR policy to a guardrail"
  - "Version this policy" / "create a numbered version" / "promote DRAFT to production"
  - "Create a guardrail with my AR policy"
  Trigger after a policy passes testing and is ready for production.
license: Apache-2.0
---

# AR Guardrail Deployer

## Overview
A guardrail enforces an AR policy at runtime. Deployment is two steps: (1) snapshot the tested DRAFT into
an **immutable numbered version**, (2) attach that version to a **guardrail** (create or update) with the
required **cross-region guardrail profile**. Updating DRAFT later won't affect a guardrail pinned to a number.

**Reference:** `../../shared/references/ar-api-context.md` (deployment section).

## Key directives
1. **Version before deploying.** `CreateAutomatedReasoningPolicyVersion` needs the current
   `definitionHash` (concurrency token) from a get/create/update response — the script fetches it.
2. **Pin guardrails to a numbered version in production**, not DRAFT.
3. **⚠️ AR guardrails require a `crossRegionConfig`** (a guardrail profile, e.g. `us.guardrail.v1:0`).
   The script derives the profile ARN from the policy ARN's account+region.
4. **⚠️ Max 2 AR policies per guardrail.**
5. **Confirm before deploying** — this is an outward-facing change. Don't overwrite an existing guardrail
   without checking what it currently points to.
6. **Default `confidenceThreshold` = 1.0** (most stringent). Lower only with a tested reason.

## Workflow
```
# 1. Snapshot DRAFT into a numbered version (handles the definitionHash concurrency token)
uv run scripts/create_version.py --policy-arn <ARN>

# 2. Create or update a guardrail attached to that version (idempotent on guardrail name)
uv run scripts/deploy_guardrail.py --policy-arn <ARN> --policy-version 1 \
  --guardrail-name my-ar-guardrail --confidence 1.0
```
`deploy_guardrail.py` is idempotent: it looks up the guardrail by name and creates or updates it, then
creates a guardrail version. It returns the guardrail id + version to use with `ar-runtime-validator`.

## After deployment
Hand off to `ar-runtime-validator` to validate LLM outputs with `ApplyGuardrail`/`Converse` against the
new guardrail id + version.

## Resources
- `scripts/create_version.py` — snapshot DRAFT → numbered version.
- `scripts/deploy_guardrail.py` — ensure-guardrail (create/update) + version, with cross-region profile.
- `../../shared/references/ar-api-context.md`.
