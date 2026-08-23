# Deployment Architecture: Vercel + Render + Supabase

**Phase**: DEPLOY-1  
**Date**: 2026-08-23  
**Status**: ACTIVE  

---

## 1. System Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Vercel Frontend                          │
│               (Vite + React + TailwindCSS)                  │
│             VITE_API_BASE_URL=https://api.domain.com        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / JSON / Multipart
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Render Backend (Flask + Gunicorn)          │
│                0.0.0.0:$PORT | Config & Secrets             │
├──────────────────────────────┬──────────────────────────────┤
│  DocumentStorage Layer       │  Repository / Data Layer     │
│  - LocalDocumentStorage      │  - SessionRepository         │
│  - SupabaseDocumentStorage   │  - DocumentRepository        │
│                              │  - ProposalRepository        │
│                              │  - LineageRepository         │
│                              │  - PilotEventRepository      │
├──────────────────────────────┴──────────────────────────────┤
│  AI Provider Seam (Server-Side Only, Zero Fallback)         │
│  - Workbench (Luna, Sol) | Gemini (3.6 Flash, 3.5 Flash)    │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│   Supabase Object Storage    │ │   Supabase Postgres DB     │
│   - documents (private)      │ │   - sessions               │
│   - generated (private)      │ │   - documents & versions   │
│   - source-artifacts (priv)  │ │   - proposals & manifests  │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## 2. Core Responsibilities

### 2.1 Vercel Frontend
- Serves the compiled single-page React app (`dist/`).
- Dispatches all API requests through `VITE_API_BASE_URL`.
- Manages optimistic UI updates, document rendering (`DocxRenderer`, `XlsxRenderer`, `PdfViewer`), and agent chat interactions.
- Never stores API keys or backend credentials.

### 2.2 Render Backend
- Runs the Python Flask application using `gunicorn` on `0.0.0.0:$PORT` with multi-threading and 120s worker timeouts.
- Performs deterministic document perception (`python-docx`, `openpyxl`, `pdfplumber`), anchoring, and element classification.
- Executes governed writeback mutations (`WritebackEngine`, `StructuralWritebackEngine`).
- Orchestrates Agent reasoning server-side via Google Gemini or KPMG Workbench.

### 2.3 Supabase Postgres & Storage
- **Postgres**: Authoritative repository for session records, versioned document metadata, action proposals with locking, cryptographic lineage logs, and pilot events.
- **Storage**: Private binary buckets (`documents`, `generated`, `source-artifacts`) with signed URL and service-role streaming.

---

## 3. Invariants & Governance

1. **No Provider Fallback**: Exact four model IDs (`workbench_luna`, `workbench_sol`, `gemini_3_6_flash`, `gemini_3_5_flash`). Unavailable models return explicit provider errors.
2. **Ephemeral Render Storage**: Local Render container storage is treated as ephemeral scratch space. All persistent documents are saved to Supabase Storage.
3. **Guaranteed Temp-File Cleanup**: Downloads to temporary disk for perception or mutation are wrapped in `finally` blocks to prevent disk leaks.
4. **Session & User Isolation**: All storage operations and database queries enforce user and session boundaries.
