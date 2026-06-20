# Chunking and Parsing

Optimize how documents are processed during ingestion.

| # | Notebook | Description | Status |
|---|----------|-------------|--------|
| 01 | `01-chunking-strategies-TBD.ipynb` | Default, Fixed-size, No Chunking — comparison | Ready |
| 02 | `02-multi-modal-rag-using-smart-parsing.ipynb` | Multi-modal RAG with Smart Parsing + Advanced Indexing (PDF, audio, video) | Ready |
| 03 | `03-advanced-indexing-TBD.ipynb` | Advanced Indexing — compare default vs image extraction | Ready |

## How it works

```
Source Document
    │
    ▼
Smart Parsing (always on for Managed KBs)
    │
    ├── Text extraction (PDF, DOCX, PPT, HTML, CSV, etc.)
    ├── Image extraction (if enable_image_extraction=True)
    ├── Audio processing (if enable_audio_extraction=True)
    └── Video processing (if enable_video_extraction=True)
    │
    ▼
Chunking Strategy
    │
    ├── Default: ~300 tokens per chunk (sentence-aware)
    ├── Fixed-size: Configurable token size + overlap %
    └── No chunking: 1 file = 1 chunk
    │
    ▼
Embedding → Vector Store → Retrieval
```

## Chunking Strategies

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

## Utility Support

Both chunking strategies and advanced indexing are supported in `utils/managed_knowledge_base.py`:

```python
from utils.managed_knowledge_base import ManagedKnowledgeBase

# Fixed-size chunking + image extraction
kb = ManagedKnowledgeBase(
    kb_name="my-kb",
    data_sources=[{
        'type': 'S3',
        'bucket_name': 'my-bucket',
        'chunking_strategy': 'FIXED_SIZE',
        'max_tokens': 500,
        'overlap_percentage': 20,
        'enable_image_extraction': True,
    }],
)
```

## Documentation

- [How content chunking works](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html)
- [Advanced indexing for managed KBs](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-advanced-indexing.html)
- [Create a managed knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-create.html)
