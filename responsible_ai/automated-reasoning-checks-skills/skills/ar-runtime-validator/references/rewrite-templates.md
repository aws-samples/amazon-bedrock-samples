# Per-Finding-Type Rewrite Templates

Used by `rewrite_loop.py` to turn a non-VALID finding into a regeneration prompt. Each template is
filled with the user question, the current (rejected) answer, and the relevant rules/scenarios from the
finding, then sent to the LLM via Converse. Adapted from the aws-samples rewriting-chatbot templates.

Rewrite the **worst-severity** finding first (TRANSLATION_AMBIGUOUS → IMPOSSIBLE → INVALID → SATISFIABLE).

## INVALID
```
The previous answer was found to CONTRADICT the policy. Rewrite it to be consistent with these rules.

User question: {question}
Rejected answer: {answer}
Contradicting policy rules:
{contradicting_rules}

Produce a corrected answer that does not violate any of the contradicting rules. If the correct answer
is "no" or "not eligible", say so clearly. Answer only with the corrected response.
```

## SATISFIABLE
```
The previous answer is correct only under some conditions. Make it complete by stating the conditions
required by the policy.

User question: {question}
Incomplete answer: {answer}
Conditions that make the claim TRUE: {true_scenario}
Conditions that make the claim FALSE: {false_scenario}

Rewrite the answer to explicitly include the missing conditions so it is unconditionally valid.
```

## IMPOSSIBLE
```
The premises lead to a logical contradiction under the policy.

User question: {question}
Answer: {answer}
Conflicting rules / premises: {contradicting_rules}

If the contradiction comes from the user's input, ask a brief clarifying question instead of answering.
Otherwise, rewrite the answer to avoid the contradiction.
```

## TRANSLATION_AMBIGUOUS
```
The question/answer could be interpreted multiple ways, so it cannot be validated definitively.

User question: {question}
Answer: {answer}
Competing interpretations: {options}

Ask the user ONE concise clarifying question that would disambiguate between the interpretations.
Do not answer until the ambiguity is resolved.
```

## TOO_COMPLEX (do not loop)
```
The request is too complex to validate in one step. Ask the user to break it into smaller, separate
questions, or simplify the answer. Do not attempt to rewrite repeatedly.
```

## NO_TRANSLATIONS
```
The content appears unrelated to the policy's domain (no policy variables matched). If the question is
on-topic, the policy may be missing variables. Surface this. If off-topic, handle it outside AR
(e.g., a topic policy) instead of rewriting.
```

## Policy context injection
When available, prepend a `## Policy Context` block listing the relevant rules (identifier: natural
language) and variables (name: description) so the LLM rewrites with full knowledge of the constraints.
