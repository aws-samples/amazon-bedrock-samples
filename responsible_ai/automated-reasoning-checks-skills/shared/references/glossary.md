# Automated Reasoning Checks: Glossary

- **Automated Reasoning (AR) checks**: a Bedrock Guardrails policy type that uses formal logic + SMT
  solvers to mathematically verify whether an LLM answer is consistent with an encoded policy.
- **Policy**: account resource (ARN, Region-scoped) holding rules + a variable schema + custom types.
  Has a DRAFT version and numbered immutable versions.
- **Rule**: a formal-logic expression (SMT-LIB subset) relating variables; should be if-then (`=>`).
- **Variable**: a named, typed (BOOL/INT/NUMBER/enum) concept with a description. Descriptions drive
  translation accuracy.
- **Custom type (enum)**: a fixed set of named values a variable can take.
- **Translation**: step 1: FMs convert NL into formal logic over your variables (fallible).
- **Validation**: step 2: an SMT solver checks the logic against rules (sound).
- **Confidence**: 0.0–1.0; % of translation models that agreed. Set a **confidence threshold** to
  require a minimum agreement before a translation yields a definitive result.
- **Finding**: one extracted claim + its result + assignments + the rules behind it.
- **Premise / Claim**: premise = a condition/assumption from the input (often the question);
  claim = the assertion being verified (often the answer).
- **Aggregated result**: the worst finding by severity:
  `TRANSLATION_AMBIGUOUS > IMPOSSIBLE > INVALID > SATISFIABLE > VALID`.
- **Fidelity report**: how faithfully the policy represents the source (coverage + accuracy scores,
  per-rule grounding). SME-friendly.
- **Quality report**: structural issues: conflicting rules, unused vars/type-values, disjoint rule sets.
- **Bare assertion**: a rule with no if-then, an always-true axiom, a common cause of `IMPOSSIBLE`.
- **Build workflow**: an async job (INGEST_CONTENT, REFINE_POLICY, etc.) that produces assets.
- **Annotation**: a targeted policy correction (addRule, updateVariable, addRuleFromNaturalLanguage, …)
  applied via the REFINE_POLICY workflow.
- **Guardrail**: the runtime enforcement resource an AR policy version attaches to.
- **Valid@N**: number of rewrite iterations needed before an answer validates as VALID (N=1 = passed first try).
- **`automatedReasoningPolicyUnits`**: usage counter; **0 means AR did not run** (silent-skip trap).
