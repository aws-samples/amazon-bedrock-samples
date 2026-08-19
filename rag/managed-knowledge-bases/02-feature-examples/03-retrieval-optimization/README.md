# Retrieval Optimization

Improve the quality and relevance of retrieved results.

| # | Notebook | Description | Status |
|---|----------|-------------|--------|
| 01 | `01-retrieval-optimization.ipynb` | Hybrid search, numberOfResults, reranking, query types | Ready |
| 02 | `02-metadata-filtering.ipynb` | Metadata sidecar files + filter operators at query time | Ready |
| 03 | `03-agentic-retrieval-deep-dive.ipynb` | AgenticRetrieveStream: traces, iterations, multi-turn, multi-KB, citations | Ready |

## Key concepts

| Feature | Managed KB behavior |
|---------|-------------------|
| **Hybrid search** | Always on (keyword + semantic) — not configurable |
| **Reranking** | Managed (free) by default; CUSTOM or NONE at query time |
| **Metadata filtering** | `.metadata.json` sidecar files + filter operators at query time |
| **numberOfResults** | 1–100, default 5 |
| **Agentic retrieval** | Multi-hop decomposition, up to 5 iterations, up to 5 retrievers |

## Documentation

- [Query configurations](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html)
- [Use agentic retrieval](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-agentic-retrieve.html)
- [Include metadata in a data source](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-metadata.html)
- [Retrieve API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html)
- [AgenticRetrieveStream API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_AgenticRetrieveStream.html)
