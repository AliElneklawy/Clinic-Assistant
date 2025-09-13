# Copilot Instructions for AI Coding Agents

## Project Overview
- **Domain:** Medical/clinical assistant with RAG (Retrieval-Augmented Generation) and embeddings.
- **Main Components:**
  - `src/embeddings/`: Embedding models (e.g., Cohere)
  - `src/rag/`: RAG logic (base and Cohere implementations)
  - `src/scripts/`: Utility scripts (API key, folder creation, file writing)
  - `src/settings/`: Configuration, logging, prompts, and paths
  - `src/utils/`: Progress tracking utilities
  - `data/`: Source and processed data (news, medical content, indexes)
  - `logs/`: Log files

## Key Patterns & Conventions
- **Embeddings and RAG:**
  - Use base classes (`base_embedding.py`, `base_rag.py`) for extensibility.
  - Implementations (e.g., `cohere_embedding.py`, `cohere_rag.py`) follow the base class interface.
- **Configuration:**
  - Centralized in `src/settings/` (e.g., `rag_config.py`, `paths.py`).
  - Logging via `logger.py`.
- **Scripts:**
  - Place one-off or utility scripts in `src/scripts/`.
  - Use `get_api_key.py` for API key management.
- **Data Handling:**
  - Raw and processed data in `data/`.
  - Indexes (e.g., FAISS) in `data/indexes/`.

## Developer Workflows
- **Run Main Application:**
  - Entry point: `src/main.py`
- **Add New Embedding or RAG Model:**
  - Subclass the relevant base class in `embeddings/` or `rag/`.
  - Register/configure in `settings/` as needed.
- **Logging:**
  - All logs go to `logs/logs.log` (see `settings/logger.py`).
- **Environment:**
  - Project uses `pyproject.toml` and `uv.lock` (likely [uv](https://github.com/astral-sh/uv) for dependency management).
  - Install dependencies: `uv pip install -r requirements.txt` or as specified in `pyproject.toml`.

## Integration & External Dependencies
- **Cohere API:** Used for embeddings and RAG (see `cohere_embedding.py`, `cohere_rag.py`).
- **FAISS:** Used for vector indexes (see `data/indexes/`).

## Project-Specific Advice
- **Follow the base class pattern** for new models/components.
- **Keep configuration in `settings/`** for consistency.
- **Use scripts in `src/scripts/`** for repeatable tasks.
- **Check `logs/`** for debugging and progress.

## Example: Adding a New Embedding
1. Create `my_embedding.py` in `src/embeddings/`.
2. Subclass `BaseEmbedding` from `base_embedding.py`.
3. Register in config if needed.
4. Update main logic to use the new embedding.

---
_If you are unsure about a workflow or pattern, check the corresponding directory for examples or ask for clarification._
