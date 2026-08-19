# Chunking and Parsing

Optimize how documents are processed during ingestion.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01-chunking-strategies.ipynb` | Default vs Fixed-size vs No Chunking — comparison |
| 02 | `02-multi-modal-rag-using-smart-parsing.ipynb` | Multi-modal RAG with Smart Parsing + Advanced Indexing (PDF, audio, video) |

## Chunking strategies for Managed KBs

| Strategy | Description | When to use |
|----------|-------------|-------------|
| **Default** (recommended) | ~300 tokens, sentence-aware | Most use cases |
| **Fixed-size** | Configurable token size + overlap % | Need more/less context per chunk |
| **No chunking** | 1 file = 1 chunk | Pre-split documents |

> **Note:** Semantic and Hierarchical chunking are only available for Customer-managed KBs.

## Advanced Indexing (Media Extraction)

| Toggle | File types | What gets indexed |
|--------|-----------|-------------------|
| `enable_image_extraction` | PDF, DOCX, PPT, HTML | Descriptions of charts, diagrams, screenshots |
| `enable_audio_extraction` | MP3, WAV, M4A, FLAC, OGG | Audio transcriptions |
| `enable_video_extraction` | MP4, MOV, M4V | Video content descriptions |

## Documentation

- [How content chunking works](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html)
- [Advanced indexing](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-advanced-indexing.html)
- [Create a managed knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-create.html)
