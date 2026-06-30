# Debugging Decisions & Annotation Recipes

## The triage (always start here)
When a test fails, read the finding's `translation`:
1. **Are the right variables assigned the right values?** If a phrase like "2 years" became
   `tenureMonths = 2` instead of `24`, that's a **translation** bug → fix the **variable description**.
2. **If the translation is correct but the result is wrong**, it's a **rule** bug → inspect
   `supportingRules` (for unexpected VALID) or `contradictingRules` (for unexpected INVALID/IMPOSSIBLE).
3. **Check `untranslatedPremises`/`untranslatedClaims`** — important content not translated may mean a
   missing variable.
4. **Check `confidence`** — low = the translation models disagreed → ambiguous descriptions.

## Decision table
| Actual result | Likely cause | Where to look / fix |
|---|---|---|
| `TRANSLATION_AMBIGUOUS` | overlapping vars, vague descriptions, ambiguous input | `options` in finding → improve descriptions, merge overlaps |
| `NO_TRANSLATIONS` | off-topic or missing variables | add variables; or filter off-topic upstream (topic policy) |
| `TOO_COMPLEX` | too many interacting rules; nonlinear arithmetic | simplify/split policy; shorten input |
| `IMPOSSIBLE` (input) | contradictory premises ("full-time AND part-time") | rewrite input; at runtime, ask user to clarify |
| `IMPOSSIBLE` (policy) | conflicting rules or a bare assertion | merge/delete conflicting rules; rewrite bare assertions |
| `VALID`, expected `INVALID` | missing rule, or rule too permissive | add a prohibiting rule, or add the missing condition |
| `INVALID`, expected `VALID` | rule too restrictive, or misextracted | relax the condition; fix/delete the rule |
| `SATISFIABLE`, expected `VALID` | response incomplete, or extra rules | diff `claimsTrueScenario` vs `claimsFalseScenario`; add conditions or remove irrelevant rules |

## Annotation recipes (`fixes.json` content for apply_annotations.py)

The file is a JSON array of annotation objects, passed as `policyRepairAssets.annotations`.

### Recipe 1 — Add a missing tenure requirement
```json
[
  { "addVariable": { "name": "tenureMonths", "type": "INT",
      "description": "Complete months continuously employed. Convert years to months (2 years = 24). 0 for new hires." } },
  { "addRuleFromNaturalLanguage": {
      "naturalLanguage": "If an employee is full-time and has more than 12 months of tenure, then they are eligible for parental leave." } }
]
```

### Recipe 2 — Fix overlapping variables causing TRANSLATION_AMBIGUOUS
```json
[
  { "deleteVariable": { "name": "monthsOfService" } },
  { "updateVariable": { "name": "tenureMonths",
      "description": "Complete months continuously employed. Covers 'tenure', 'months of service', 'time at company'." } },
  { "updateRule": { "id": "<RULE_ID>", "expression": "(=> (and isFullTime (> tenureMonths 12)) eligibleForParentalLeave)" } }
]
```

### Recipe 3 — Fix a bare assertion causing IMPOSSIBLE
```json
[
  { "deleteRule": { "id": "<BARE_RULE_ID>" } },
  { "addRuleFromNaturalLanguage": {
      "naturalLanguage": "If an employee is full-time and has more than 12 months of tenure, then they are eligible for parental leave." } }
]
```

### Recipe 4 — Natural-language feedback on a scenario/rule
```json
[
  { "updateFromScenarioFeedback": {
      "feedback": "Employees need at least 12 months of tenure for parental leave; a 3-month scenario should not be eligible." } }
]
```

## After applying
1. The REFINE_POLICY build proposes changes — review them.
2. `UpdateAutomatedReasoningPolicy` to commit to DRAFT (the script can do this if you pass the new definition).
3. Re-run `ar-policy-reviewer` (quality report) and `ar-policy-tester` (regression). Iterate.

## When to use the other workflows
- **RESOLVE_POLICY_AMBIGUITIES** (`resolve_ambiguities.py`) — bulk auto-refine of ambiguous variable
  descriptions/types when many TRANSLATION_AMBIGUOUS results appear.
- **ITERATIVELY_REFINE_POLICY** (`iteratively_refine.py`) — when the source document changed, or you want
  to guide refinement with a doc + natural-language feedback (vs. adding brand-new content via INGEST_CONTENT).
