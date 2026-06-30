# Findings & Validation Results Reference

A **finding** = one factual claim extracted from the input + its validation result + the variable
assignments + the rules behind it. Most findings carry a `translation` object:
`premises`, `claims`, `confidence` (0.0–1.0), `untranslatedPremises`, `untranslatedClaims`, and a
`logicWarning` (present when the translation is trivially always-true/always-false).

**Aggregated result = the WORST finding by severity.** Severity (worst → best):
`TRANSLATION_AMBIGUOUS → IMPOSSIBLE → INVALID → SATISFIABLE → VALID`.
`TOO_COMPLEX` and `NO_TRANSLATIONS` are outside this ordering — handle separately.

| Result | Union key | Distinct fields | What it means | Recommended action |
|---|---|---|---|---|
| **VALID** | `valid` | `supportingRules`, `claimsTrueScenario` | Claims provably true given premises + rules | Serve. Log `supportingRules` + `claimsTrueScenario` for audit. Check `untranslated*` for unvalidated parts. |
| **INVALID** | `invalid` | `contradictingRules` | Claims contradict policy rules | Don't serve. Pass `contradictingRules` + claims to the LLM to rewrite, or block. |
| **SATISFIABLE** | `satisfiable` | `claimsTrueScenario` + `claimsFalseScenario` | True under some conditions, not all (incomplete) | Diff the two scenarios → add missing conditions, ask user, or serve with a caveat. |
| **IMPOSSIBLE** | `impossible` | `contradictingRules` (if policy-side) | Premises self-contradict, OR policy rules conflict | Check input for contradictions ("full-time AND part-time"). If input is fine, fix the policy (quality report). |
| **TRANSLATION_AMBIGUOUS** | `translationAmbiguous` | `options` (≤2 interpretations, each with own translation+confidence), `differenceScenarios` (≤2) | Translation models disagreed | Inspect `options`; improve variable descriptions / merge overlaps / ask user. Lowering threshold = last resort. |
| **TOO_COMPLEX** | `tooComplex` | none | Exceeded processing/latency capacity | Shorten input; reduce variables; avoid nonlinear arithmetic; split the policy. |
| **NO_TRANSLATIONS** | `noTranslations` | none | Couldn't map input to any variable (off-topic or missing vars) | If relevant, add variables; if off-topic, filter upstream (topic policy). Appears alongside other findings when part of the input was untranslated. |

## ⚠️ Critical caveats
- **`VALID` only covers translated claims.** Untranslated content is NOT validated — e.g. "I have a
  fake doctor's note" can pass if no variable models it. Treat `untranslatedPremises`,
  `untranslatedClaims`, and any `NO_TRANSLATIONS` finding as a **warning signal**.
- **Confidence ≠ correctness.** `confidence` measures translation-model agreement, not whether the
  answer is right. Low confidence → ambiguous variable descriptions for this input.

## Debugging decision table (actual result → likely cause → where to look)

| Actual result (unexpected) | Likely cause | Fix |
|---|---|---|
| `TRANSLATION_AMBIGUOUS` | overlapping/vague variables, ambiguous input | improve variable descriptions; merge overlaps |
| `NO_TRANSLATIONS` | off-topic, or missing variables for the concept | add variables, or filter off-topic upstream |
| `TOO_COMPLEX` | input/policy too big; nonlinear arithmetic | shorten input; split policy; simplify rules |
| `IMPOSSIBLE` | contradictory premises, or conflicting policy rules / bare assertions | fix input, or merge/delete conflicting rules; rewrite bare assertions |
| `VALID`/`INVALID`/`SATISFIABLE` but not expected | **check translation first** | translation wrong → fix variable descriptions; translation right → fix rules |

**Always check the translation first** — the SMT validation step is sound; most surprises come from
how natural language was mapped to variables. Fixing a description is faster and safer than changing rules.
