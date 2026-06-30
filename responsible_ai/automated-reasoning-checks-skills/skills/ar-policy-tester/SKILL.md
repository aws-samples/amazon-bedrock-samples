---
name: ar-policy-tester
description: >
  Tests an Amazon Bedrock Automated Reasoning (AR) policy using generated scenarios (to validate rule
  correctness) and question-and-answer (QnA) tests (to validate translation accuracy end-to-end). Drives
  GENERATE_POLICY_SCENARIOS, GetAutomatedReasoningPolicyNextScenario, CreateAutomatedReasoningPolicyTestCase,
  StartAutomatedReasoningPolicyTestWorkflow, and result retrieval.

  Use this skill whenever the user wants to:
  - "Test my Automated Reasoning policy" / "generate test scenarios" / "add a QnA test"
  - "Validate all tests" or run a test workflow against a policy
  - Verify a policy's rules are correct and that it translates real user inputs accurately
  Trigger after a policy has been reviewed (ar-policy-reviewer) and before deployment.
license: Apache-2.0
---

# AR Policy Tester

## Overview
Testing targets the **two-step pipeline** separately:
- **Generated scenarios** test **rule correctness** — they're derived from your rules and remove
  translation uncertainty. Review each: thumbs-up saves a `SATISFIABLE` test; thumbs-down → annotate.
- **QnA tests** test the **full pipeline** (translation + validation) with realistic question/answer
  pairs and an expected result.

**Recommended order:** scenarios first (fix rules), then QnA (fix translations / variable descriptions).

**Reference:** `../../shared/references/ar-api-context.md`, `findings-reference.md` (severity ordering).

## When to use
- After `ar-policy-reviewer` is clean, to validate behavior before deploying.
- To build a regression suite that re-runs whenever the policy changes.

## Key directives
1. **Scenarios before QnA.** Validate rules before spending effort on translation tests.
2. **Cover both valid and invalid cases** — e.g. a response that correctly states a rule AND one that
   states a wrong threshold.
3. **`expectedAggregatedFindingsResult` = the WORST finding** by severity
   (`TRANSLATION_AMBIGUOUS > IMPOSSIBLE > INVALID > SATISFIABLE > VALID`). A test with one IMPOSSIBLE
   finding aggregates to IMPOSSIBLE even if others are VALID.
4. **Test workflow needs a COMPLETED build id.** The script resolves the latest one automatically.
5. On failures, hand off to `ar-policy-debugger` — don't guess at fixes here.

## Workflow
```
# 1. Generate scenarios (start workflow + fetch them one at a time)
uv run scripts/generate_scenarios.py --policy-arn <ARN> [--count 10]

# 2. Create QnA tests (the answer is required; the question is optional context)
uv run scripts/create_test.py --policy-arn <ARN> \
  --output "No, only full-time employees are eligible for leave of absence." \
  --input  "Can I take a leave if I'm part-time?" \
  --expected VALID --confidence 0.8

# 3. Run tests + collect results
uv run scripts/run_tests.py --policy-arn <ARN>            # all tests
uv run scripts/run_tests.py --policy-arn <ARN> --test-case-ids test-123 test-456
```

## Interpreting results
Each result has **expected**, **actual** (aggregated worst-severity), and pass/fail. For what each result
type means and how to react, see `../../shared/references/findings-reference.md`. If actual ≠ expected,
**check the translation first** (premises/claims/confidence) before suspecting the rules.

## Resources
- `scripts/generate_scenarios.py`, `scripts/create_test.py`, `scripts/run_tests.py` (all `--help` + `--dry-run`).
- `../../shared/references/ar-api-context.md`, `findings-reference.md`.
