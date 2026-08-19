---
name: ar-runtime-validator
description: >
  Validates LLM outputs at runtime against an Amazon Bedrock Automated Reasoning (AR) guardrail and runs
  an iterative rewrite loop (Valid@N) to correct non-VALID answers. Calls ApplyGuardrail (or Converse)
  with correct qualifiers, parses the findings union, guards against the silent-skip trap, and rewrites
  answers using per-finding-type templates and rule context.

  Use this skill whenever the user wants to:
  - "Validate this answer with Automated Reasoning" / "call ApplyGuardrail" / "check my chatbot response"
  - "Set up a rewrite loop" / "make the model fix its answer until it's valid" / "Valid@N"
  - Parse automatedReasoningPolicy findings or integrate AR into a Converse/InvokeModel app
  Trigger after a guardrail is deployed (ar-guardrail-deployer), or whenever an answer needs AR validation.
license: Apache-2.0
---

# AR Runtime Validator

## Overview
At runtime you validate an LLM answer against a guardrail that has an AR policy attached, read the
**findings**, and (if the answer isn't VALID) feed the contradicting/insufficient rules back to the LLM
to **rewrite**, then re-validate. Repeat until VALID or a max-iteration cap (Valid@N).

**Reference:** `../../shared/references/ar-api-context.md` (runtime section + qualifier rules),
`findings-reference.md` (result types + actions), `references/rewrite-templates.md` (per-type prompts).

## Key directives
1. **⚠️ Silent-skip guard.** A misconfigured (untagged) request still succeeds but runs no AR checks
   (`automatedReasoningPolicyUnits: 0`). **Always assert that value is > 0** (`ar_common.assert_ar_ran`).
2. **Qualifier rules:** `ApplyGuardrail` blocks default to **claim** (agent-side); mark the user question
   with `qualifiers:["query"]`. `ApplyGuardrail` appends **no** model response, so include ≥1 claim block
   or you get `ValidationException`. **`Converse` uses snake_case** qualifiers; **`InvokeModel` camelCase**.
3. **Use a numbered guardrail version** in production, not DRAFT.
4. **Rewrite by worst finding first** (severity order). `VALID` → serve; `TOO_COMPLEX` → ask the user to
   simplify (don't loop); `TRANSLATION_AMBIGUOUS`/`IMPOSSIBLE` from input → consider asking for clarification.
5. **Log the audit trail.** Findings + supporting/contradicting rules per iteration are
   mathematically-verifiable evidence. Keep them.

## Workflow
```
# One-shot validation
uv run scripts/validate_response.py --guardrail-id <ID> --guardrail-version 1 \
  --question "Am I eligible for parental leave after 2 years full-time?" \
  --answer "Yes, you are eligible."

# Iterative rewrite loop (Valid@N)
uv run scripts/rewrite_loop.py --guardrail-id <ID> --guardrail-version 1 \
  --question "..." --answer "<initial answer>" \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 --max-iter 5
```
`validate_response.py` prints the findings + aggregated result and asserts AR actually ran.
`rewrite_loop.py` validates → on non-VALID, renders the matching template with the finding's rules →
regenerates via Converse → re-validates, up to `--max-iter`, logging each iteration.

## Interpreting findings
See `../../shared/references/findings-reference.md` for the full table. Quick guide:
- **VALID** → serve (check `untranslated*` for unvalidated parts).
- **INVALID** → rewrite using `contradictingRules`.
- **SATISFIABLE** → add missing conditions (diff true/false scenarios) or caveat.
- **IMPOSSIBLE** → contradictory input or policy conflict; clarify or fix policy.
- **TRANSLATION_AMBIGUOUS** → ask user to clarify / improve policy descriptions.
- **TOO_COMPLEX / NO_TRANSLATIONS** → simplify input / handle off-topic separately.

## Resources
- `scripts/validate_response.py`, `scripts/rewrite_loop.py` (`--help` + `--dry-run`).
- `references/rewrite-templates.md`: per-finding-type rewrite prompts (lifted from aws-samples).
- `../../shared/references/ar-api-context.md`, `findings-reference.md`.
