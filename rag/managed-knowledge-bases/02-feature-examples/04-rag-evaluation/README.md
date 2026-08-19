# RAG Evaluation

Measure and validate the quality of your Managed KB RAG pipeline.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01-agentic-rag-evaluation-for-managed-kb.ipynb` | Evaluate Managed KB using AgentCore Evaluations (OTEL trace spans) |
| 02 | `02-ragas-evaluation.ipynb` | Evaluate retrieval and generation quality using the RAGAS framework |

## Evaluation approaches for Managed KBs

| Approach | Works? | How |
|----------|--------|-----|
| **AgentCore Evaluations** | ✅ Yes | Evaluates OTEL trace spans from agent invocations |
| **RAGAS (open-source)** | ✅ Yes | Run AgenticRetrieveStream, feed results to RAGAS |

## AgentCore Evaluations (Notebook 01)

Evaluates the end-to-end RAG pipeline by scoring OTEL spans from your agent:

```python
ace_client = boto3.client('bedrock-agentcore', region_name=region)
response = ace_client.evaluate(
    evaluatorId="Builtin.Faithfulness",
    evaluationInput={"sessionSpans": session_span_logs}
)
```

Available evaluators: `Builtin.Faithfulness`, `Builtin.Correctness`, `Builtin.Helpfulness`, `Builtin.ContextRelevance`, `Builtin.GoalSuccessRate`, `Builtin.ToolSelectionAccuracy`

## RAGAS Evaluation (Notebook 02)

Uses the open-source RAGAS framework for offline evaluation:

1. Run `AgenticRetrieveStream` on your eval questions
2. Collect responses and retrieved contexts
3. Feed to RAGAS for faithfulness, answer relevancy, context precision, and recall scores

## Why not Bedrock Evaluation Jobs?

The `CreateEvaluationJob` API has a catch-22 for Managed KBs:
- API schema only accepts `vectorSearchConfiguration` 
- But Managed KBs reject `vectorSearchConfiguration` at runtime (need `managedSearchConfiguration`)
- `RetrieveAndGenerate` (used internally for R+G eval) is not supported for Managed KBs

## Documentation

- [AgentCore Evaluations](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html)
- [RAGAS framework](https://docs.ragas.io/)
- [AgentCore Evaluations samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/07-AgentCore-evaluations)
