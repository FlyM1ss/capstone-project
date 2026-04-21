# AI Summary Panel on Document Page

**Date:** 2026-04-21
**Status:** Approved, ready for implementation

## Goal

When a user opens a document, display an AI-generated bulleted summary in a side
panel to the right of the preview/text content, so users can triage documents
without reading them in full. The "AI Summary" header aligns horizontally with
the existing `Preview` / `Text Content` tab bar.

## Scope

### In scope
- New backend endpoint `GET /api/documents/{id}/summary` with per-document DB caching.
- Cohere Chat API (`command-r-08-2024`) integration in a new `summarizer` service.
- Schema additions: `documents.summary TEXT`, `documents.summary_generated_at TIMESTAMPTZ`.
- Two-column grid layout on `DocumentPage` with a new `DocumentSummaryPanel` component.
- Loading / loaded / error UX states.
- Graceful degradation when `COHERE_API_KEY` is missing or the API fails.

### Out of scope
- Streaming token-by-token display.
- User-triggered regeneration (no refresh button).
- Auth-gated regeneration.
- Summary versioning or history.
- Prompt customization UI.

## Architecture

### Backend

**New file:** `backend/app/services/summarizer.py`
- `async def generate_summary(document) -> str` — takes a `Document` ORM object, pulls its chunks, concatenates up to ~8K chars, calls Cohere Chat, returns parsed bullet text.
- `class SummarizerUnavailable(Exception)` — raised when `COHERE_API_KEY` is empty or Cohere call fails. Mirrors the `EmbeddingServiceUnavailable` pattern.
- Prompt template produces 5–7 bullets, each starting with `- `, no preamble.

**Modified:** `backend/app/api/documents.py`
- Add route `GET /documents/{doc_id}/summary`.
- Logic: fetch doc → if `summary` populated, return cached. Else call summarizer, persist `summary` + `summary_generated_at`, commit, return fresh.
- Returns `SummaryResponse { summary: str, cached: bool, generated_at: datetime }`.
- Maps `SummarizerUnavailable` to HTTP 503.

**Modified:** `backend/app/models/db.py`
- Add `summary: Mapped[str | None] = mapped_column(Text)`.
- Add `summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))`.

**Modified:** `backend/app/models/schemas.py`
- Add `SummaryResponse` Pydantic model.

**Modified:** `backend/db/init.sql`
- `ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;`
- `ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary_generated_at TIMESTAMPTZ;`

**Modified:** `backend/app/main.py`
- On startup, run the same `ADD COLUMN IF NOT EXISTS` statements so existing
  deployments pick up the new columns without a full re-init.

### Frontend

**New component:** `frontend/src/components/DocumentSummaryPanel/`
- `DocumentSummaryPanel.tsx` — props: `{ documentId: string }`. Internally fetches summary on mount, manages loading/error state.
- `DocumentSummaryPanel.module.scss` — panel styles, bullet list, skeleton shimmer.

**Modified:** `frontend/src/api/documents.ts`
- Add `export async function getDocumentSummary(id: string): Promise<SummaryResponse>`.

**Modified:** `frontend/src/pages-views/DocumentPage/DocumentPage.tsx`
- Wrap tab row + content area in a two-column grid.
- Right column: `"AI Summary"` header bar (matches tab bar height/border) + `DocumentSummaryPanel`.
- Summary fetch fires in parallel with doc/chunks fetch.

**Modified:** `frontend/src/pages-views/DocumentPage/DocumentPage.module.scss`
- `.page` max-width: `860px` → `1280px`.
- New `.splitLayout` grid with `1fr minmax(300px, 360px)`.
- Media query `(max-width: 1100px)`: collapse to single column, summary drops below content.
- New `.summaryHeader` matching `.tabBtn` row height and bottom border.

## Data Flow

```
User clicks document card
  → navigate to /documents/:id
  → DocumentPage mounts
  → Promise.all([getDocumentById, getDocumentChunks]) fires
  → getDocumentSummary() fires in parallel (independent)
  → Preview/Text renders as soon as doc+chunks resolve
  → Summary panel shows skeleton until summary resolves
```

Backend flow for `/summary`:

```
Receive GET /api/documents/:id/summary
  → SELECT * FROM documents WHERE id = :id
  → if doc.summary is not null → return { summary, cached: true, generated_at }
  → else:
      fetch doc chunks (ordered by chunk_index)
      concatenate content, truncate to 8000 chars
      call cohere.chat(model="command-r-08-2024", message=<prompt>, temperature=0.3)
      parse response, strip preambles, normalize bullets
      UPDATE documents SET summary = ..., summary_generated_at = NOW() WHERE id = :id
      return { summary, cached: false, generated_at }
```

## Prompt Template

```
You are summarizing an internal business document for employees
searching a company knowledge base.

Document title: {title}
{author_line}

Document content:
{truncated_content}

Produce 5-7 concise bullet points capturing the most useful takeaways:
key facts, decisions, figures, and conclusions. Each bullet starts with
"- " on its own line. No preamble, no closing remark, no headers.
```

Temperature `0.3` for consistency across reloads.

## Error Handling

- **Missing `COHERE_API_KEY`**: summarizer raises `SummarizerUnavailable`, endpoint returns 503 with `error_code: "summarizer_unavailable"`. Frontend shows "Summary unavailable for this document."
- **Cohere API error (network, 5xx)**: same path, 503 with a reason string.
- **Empty document (no chunks)**: endpoint returns 200 with `summary: null, cached: false, generated_at: null`. Frontend shows "No content to summarize." in the panel body.
- **Viewport < 1100px**: grid collapses; panel still functions, just appears below content.

Failures never block the document preview or text tab.

## Testing

Manual acceptance criteria:
1. Open any ingested PDF from the search results → within ~4s, right-side panel shows 5–7 bullets.
2. Reload the same doc → panel populates instantly (cache hit visible in backend logs).
3. Clear `COHERE_API_KEY` in `.env` and restart backend → opening a new doc shows the "unavailable" message, preview still works.
4. Resize browser below 1100px → summary panel moves below content, remains functional.
5. "AI Summary" header bottom border is flush with "Preview" / "Text Content" tab underline when viewport is wide.

No automated tests yet (repo has no test framework configured).

## Model & Cost

- Model: `command-r-08-2024` via Cohere Chat API.
- Per-doc call: ~3K input tokens + ~150 output tokens.
- Lifetime cost for a 200-doc capstone demo corpus: well under the free tier allowance (20 RPM, ~1K calls/month on trial keys).
- Caching means 1 call per unique doc, ever.

## File Touchpoints Summary

| Area | File | Change |
|---|---|---|
| Backend | `backend/db/init.sql` | Add summary columns |
| Backend | `backend/app/main.py` | Startup `ADD COLUMN IF NOT EXISTS` |
| Backend | `backend/app/models/db.py` | Add summary fields to `Document` |
| Backend | `backend/app/models/schemas.py` | Add `SummaryResponse` |
| Backend | `backend/app/services/summarizer.py` | **NEW** — Cohere wrapper |
| Backend | `backend/app/api/documents.py` | Add `/summary` route |
| Frontend | `frontend/src/api/documents.ts` | Add `getDocumentSummary` |
| Frontend | `frontend/src/components/DocumentSummaryPanel/*` | **NEW** — panel component |
| Frontend | `frontend/src/pages-views/DocumentPage/DocumentPage.tsx` | Grid + panel wiring |
| Frontend | `frontend/src/pages-views/DocumentPage/DocumentPage.module.scss` | Grid + widened max-width |
