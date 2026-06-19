# 03 — Chunking and Parsing

Optimize how documents are processed during ingestion.

| # | Notebook | Description | Status |
|---|----------|-------------|--------|
| 01 | `02-multi-modal-rag-using-smart-parsing.ipynb]`| Smart Parsing — Multi-modal RAG with PDF, audio, and video content | automatic (default for BMKB) 


### Current default

All existing notebooks use **Smart Parsing** (hardcoded in `utils/managed_knowledge_base.py`). This is the only parsing strategy supported by BMKB.

> **Note for contributors:** The utility currently hardcodes `SMART_PARSING`. Chunking strategies (02) will need configurable `chunkingConfiguration` support. Advanced indexing (03) will need `mediaExtractionConfiguration` support.
