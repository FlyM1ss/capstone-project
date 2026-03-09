# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ITWS 4100 (IT Capstone) project — an AI-driven company-wide search engine prototype for Deloitte. The system uses NLP with hybrid retrieval (semantic + BM25 keyword search) to let employees search internal resources via natural language queries.

**Tech stack:** Next.js (App Router) + TypeScript + Vercel AI SDK 6 frontend, FastAPI backend, PostgreSQL 16 with pgvector + ParadeDB (unified hybrid search), Qwen3-Embedding-0.6B embeddings, Cohere Rerank 4, Docling (document parsing), NextAuth.js + Keycloak (auth), Docker Compose deployment.

## Repository Structure

- `software-engineering/` — Software design deliverable: Python scripts that generate a formatted .docx and Google Doc with embedded UML diagrams
  - `build_docx.py` — Generates .docx using python-docx (run with `python3 build_docx.py`)
  - `create_gdoc.py` — Creates Google Doc in shared Drive folder via Google Docs API
  - `setup_google_docs.py` — OAuth setup + alternative doc creation script
  - `diagrams/` — Mermaid source files (.mmd) and rendered PNGs (usecase, activity, sequence, component, deployment)
- `Proposal/` — Project proposal documents (PDFs)
- `Pre-Project-Research/` — Foundational research on knowledge management
- `CostBenefitAnalysis/` — CBA worksheets and narratives
- `past-examples/` — Reference materials from prior capstone teams

## Key Commands

```bash
# Generate the software engineering .docx
cd software-engineering && python3 build_docx.py

# Render Mermaid diagrams to PNG (requires mmdc / mermaid-cli)
mmdc -i diagrams/usecase.mmd -o diagrams/usecase.png -p diagrams/puppeteer.json

# Create Google Doc (requires credentials.json in software-engineering/)
python3 software-engineering/create_gdoc.py
```

## Secrets

`credentials.json` and `token.json` (Google OAuth) live in `software-engineering/` but are gitignored. Never commit these files. The `.gitignore` covers `*.pem`, `*.key`, `.env*`, `credentials.json`, `token.json`, and `service-account*.json`.

## Conventions

- Hardcoded paths in `build_docx.py` use a Windows/WSL path format (`/mnt/c/Users/...`). Update the `DIAGRAMS` constant and `out_path` if running from a different machine.
- Diagram source of truth is the `.mmd` files; PNGs are rendered outputs.
