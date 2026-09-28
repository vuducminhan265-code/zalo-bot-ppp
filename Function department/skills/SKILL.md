---
name: zalo-bot-function-department
description: "Project management, directory structure, Zalo bot automation, and RAG knowledge retrieval skill for Alexander."
---

# Zalo Bot & Function Department Guidelines

## 1. Directory Structure Rule
All components must strictly remain under `Function department/`:
- `Function department/ai_core`: Gemini/Claude file analysis engines.
- `Function department/rag_engine`: Document indexer, hybrid retriever, and synthesis pipeline.
- `Function department/tools`: Task tracker Excel/Sheets helpers and test scripts.
- `Function department/zalo_service`: Zalo bot service listener, n8n workflows, Apps Script integrations.
- `Function department/skills`: Specialized operational skills.

## 2. Local RAG Engine Protocol
- Documents stored in `data/documents/`.
- SQLite database stored at `data/database/rag_index.db`.
- Execute indexer: `python -m "Function department.rag_engine.rag_indexer"`
- Query pipeline: `python -m "Function department.rag_engine.rag_pipeline"`

## 3. Zalo Bot Workflow
- Cron Reminders: Scheduled at 08:30 and 16:30 daily.
- File Submission Review: Multimodal inspection via Gemini Flash with status decisions (`completed` vs `needs_revision`).
