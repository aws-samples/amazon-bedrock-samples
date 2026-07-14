# RAG Evaluation

Measure and validate the quality of your Managed KB RAG pipeline.

| # | Notebook | Description | Status |
|---|----------|-------------|--------|
| 01 | `01-qna-generation-from-pdf.ipynb` | Generate synthetic Q&A dataset from Octank Financial PDF using Claude | Ready |
| 02 | `02-bedrock-evaluation-job.ipynb` | Bedrock Evaluation Job — retrieval-only eval (R+G not supported for Managed KBs) | Ready |
| 03 | `03-agentcore-evaluation-for-managed-kb.ipynb` | **AgentCore Evaluations** — evaluate Managed KB via OTEL trace spans | Ready |

## ⚠️ Managed KB evaluation limitations

Bedrock Evaluation Jobs (`CreateEvaluationJob`) have limited support for Managed KBs:

| Evaluation type | Supported? | Issue |
|-----------------|-----------|-------|
| Retrieval-only (`retrieveConfig`) | ❌ | Catch-22: API requires `vectorSearchConfiguration` but Managed KBs reject it at runtime |
| Retrieve + Generate (`retrieveAndGenerateConfig`) | ❌ | Uses `RetrieveAndGenerate` internally, not supported for Managed KBs |
| Precomputed responses (`precomputedRagSourceConfig`) | ✅ | Workaround: provide your own inference results |
| **AgentCore Evaluations** | ✅ | Evaluates OTEL trace spans — recommended approach |

See `EVALUATION_LIMITATIONS_MANAGED_KB.md` for the full write-up.

## Recommended approach: AgentCore Evaluations

AgentCore Evaluations works with Managed KBs because it evaluates **agent trace spans** (not KB APIs directly):

1. Agent calls `AgenticRetrieveStream` → OTEL spans written to `aws/spans`
2. Collect spans from CloudWatch by session ID
3. Call `AgentCore Evaluate` API with built-in evaluators
4. Get scores for Faithfulness, Helpfulness, Correctness, Tool Accuracy, etc.

```python
ace_client = boto3.client('bedrock-agentcore', region_name=region)
response = ace_client.evaluate(
    evaluatorId="Builtin.Faithfulness",
    evaluationInput={"sessionSpans": session_span_logs}
)
```

## Documentation

- [AgentCore Evaluations](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html)
- [Bedrock Evaluation Jobs](https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-kb.html)
- [AgentCore Evaluations samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/07-AgentCore-evaluations)
