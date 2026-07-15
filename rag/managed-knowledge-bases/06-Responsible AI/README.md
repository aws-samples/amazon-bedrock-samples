# Responsible AI — Guardrails

Apply Bedrock Guardrails to Managed Knowledge Bases for content safety and grounding checks.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01-guardrails-with-bmkb.ipynb` | Bedrock Guardrails integration with AgenticRetrieveStream |
| 02 | `02-guardrails-contextual-grounding-with-bmkb.ipynb` | Contextual grounding — detect and block hallucinated responses |

## How Guardrails work with Managed KBs

Guardrails are applied via the `policyConfiguration` parameter in `AgenticRetrieveStream`:

```python
response = runtime_client.agentic_retrieve_stream(
    ...,
    policyConfiguration={
        'guardrailId': 'your-guardrail-id',
        'guardrailVersion': 'DRAFT',
    },
)
```

## Contextual grounding

Checks whether the generated response is:
1. **Grounded** — factually supported by the retrieved source chunks
2. **Relevant** — answers the user's actual question

If either check fails → response is **BLOCKED**.

## Limitations

- Only `BLOCK` action is supported (not `MASK`) with AgenticRetrieveStream
- Grounding source limit: 100,000 characters
- Query limit: 1,000 characters
- Response limit: 5,000 characters

## Documentation

- [Contextual grounding check](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html)
- [Guardrails with agentic retrieval](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-agentic-retrieve.html)
- [Create a guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-create.html)
