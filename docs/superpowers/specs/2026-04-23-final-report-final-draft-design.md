# Final Report Final-Draft Polish Pass — Design

**Date:** 2026-04-23
**Owner:** Felix Tian (System Architect)
**Course:** ITWS 4100 Capstone, Group Two
**Deadline:** Monday 2026-04-27, 23:59 EDT
**Status:** Approved for implementation

## Goal

Convert `Final Report Draft.docx` (currently ~57 pages, scored near-perfect in AI feedback) into the submission-ready final draft by closing the small number of deductions the feedback identified, without restructuring or rewriting content that already scored full marks.

## Non-goals

- Restructuring to match `coursework/final-report/OUTLINE.md` (26 sections + 9 appendices). The AI feedback validates the current 13-section structure — its scoring rubric matches Draft_v1's sections exactly.
- Adding appendices (not in rubric, not in deductions).
- Rewriting §1–§7, §9–§13 (all scored 10/10 or 5/5 in the new draft after §12/§13 content was added).
- Adding new references (the current 19 are sufficient and properly formatted).
- Changing financial methodology (numbers are internally consistent at NPV $2,168,378 / ROI 5,832% / payback < 1 year; only stale outliers need to be scrubbed).

## Inputs

| Artifact | Path | Role |
|---|---|---|
| DOCX source | `coursework/final-report/Final Report Draft.docx` | Edit-in-place target (4.2MB, 389 paragraphs, 15 tables, 11 embedded images, 13 sections) |
| PDF reference | `coursework/final-report/Final Report Draft 1.pdf` | Read-only snapshot for cross-checking |
| AI feedback | In chat history (2026-04-23) | Authoritative deduction list |
| Outline | `coursework/final-report/OUTLINE.md` | Reference only; structure does not apply |
| Existing screenshot pipeline target | `coursework/final-report/screenshots/` (to create) | Destination for captured PNGs |
| Styling reference | `coursework/final-report/build_section12.py` | Source of truth for DOCX visual conventions (Calibri 11pt, navy #2E4057 header shading, alternating row shading) |

## Architecture

Single python-docx-based script: `coursework/final-report/apply_edits.py`.

```
Final Report Draft.docx
          │
          ▼
   apply_edits.py  ──calls──►  patch_1_8_10_screenshots()
   (argparse CLI)              patch_2_simplify_jargon()
          │                    patch_3_normalize_tables()
          │                    patch_4_copyedit_pass()
          │                    patch_5_financial_consistency()
          │                    (verify_* after each)
          ▼
Final Report Draft.final.docx
          │
          ▼ manual: open in Word/Docs, F9 to refresh TOC
          ▼
   Upload to Drive as new Google Doc
```

Each patch function is self-contained:
- Opens the working DOCX
- Locates the target (by heading text, paragraph index, or table index)
- Applies its mutation
- Runs a paired `verify_*` function that re-reads the written DOCX and asserts the expected state

This isolation means a regression in one patch can't silently corrupt another patch's work.

## Patches (five units + one manual step)

### Patch 1: §8.10 screenshots

**Problem:** §8.10 currently reads *"Screenshots of the working system will be included in the final version of this report."* Feedback: "The document is incomplete as noted in Section 8.10 regarding screenshots." Cost: 1 point on IS/IT Design (24/25).

**Fix:**
1. Capture 3 PNG screenshots via docker compose + the central-db Auto UI Testing bot:
   - `landing.png` — landing page with search input
   - `search-results.png` — search results for a representative query showing relevance scores + filters
   - `admin-upload.png` — admin upload portal with a queued file
2. Save to `coursework/final-report/screenshots/`.
3. `patch_1_8_10_screenshots()` replaces the placeholder paragraph with:
   - One short lead-in sentence
   - Three figures in document order, each with:
     - Inline image (width ~6.0 inches to match other embedded figures)
     - Italicized caption beneath ("Figure 8.10.N: ...")
     - One descriptive sentence per figure noting what it demonstrates

**Verify:** output DOCX contains 3 new inline shapes whose preceding heading is "8.10 Working System and Screenshots"; placeholder sentence is absent.

### Patch 2: simplify jargon for executive audience

**Problem:** Feedback: "A few instances of overly technical language that could be simplified for executive audiences." Contributes to the 2-point deduction on Writing Quality (8/10).

**Fix:** Targeted sentence-level rewrites in §8.2 (Technical Architecture), §8.3 (Search Pipeline), §8.5 (Database Design), §8.6 (Security Architecture). Exact rewrites enumerated in the implementation plan (not the spec). Principle: keep the technical precision in-line but add a clause that translates to business impact. Example transformation:
- Before: "HNSW index with 1024-dim cosine similarity."
- After: "A vector index that finds semantically similar document chunks in milliseconds, using the same HNSW algorithm that powers production search systems at scale."

Target: 6–10 such rewrites. No wholesale section rewrites.

**Verify:** specific target sentences (identified by stable locator strings) are replaced; adjacent sentences unchanged.

### Patch 3: normalize table formatting

**Problem:** Feedback: "Some minor formatting inconsistencies in tables and figures." Contributes to Writing Quality deduction.

**Fix:** Walk all 15 tables. Apply the `build_section12.py` convention uniformly:
- Header row: dark navy `#2E4057` shading, white Calibri 10pt bold, centered
- Data rows: Calibri 10pt
- Odd data rows: light grey `#F2F2F2` shading; even: white
- Table alignment: center
- Borders: `Table Grid` style

**Verify:** every table in the output DOCX has the header shading tag and alternating row pattern.

### Patch 4: copyedit pass

**Problem:** Writing Quality 8/10 — general polish.

**Fix:** 15–25 micro-edits across §1–§13:
- Em-dash → comma / period / parenthesis (project global rule, no em dashes unless explicitly invoking `write-like-me`)
- Transition word tightening where paragraphs stack without connective tissue
- Tense consistency (past tense for describing what was built, present tense for describing what the system does)
- Redundancy removal (e.g., "in order to" → "to")

Each edit is a locator-string-based `text.replace()`. Each is listed in the implementation plan.

**Verify:** no em dashes remain in body text (character `—` count = 0), target redundant phrases absent.

### Patch 5: financial consistency scrub

**Problem:** OUTLINE.md carries stale numbers (NPV $51.5M, ROI ~5,936%). The draft itself is internally consistent (NPV $2,168,378, ROI 5,832%, payback < 1 year), but I need to verify exec-summary IRR (~3,700%) matches §9.3 and scrub any stale figures.

**Fix:**
1. Scan document for occurrences of `51.5M`, `51,500,000`, `5,936`, `5936` → fail loudly if any are found (nothing should match, but this is a guardrail).
2. Extract IRR figure from §1 executive summary and from §9.3; assert they match.
3. No mutation expected under normal circumstances — this patch is a verifier, not a rewriter. If it finds stale data, halt and flag for manual review.

**Verify:** patch is a no-op in the common case; a test failure here is a spec bug, not a silent data issue.

### Manual step: refresh TOC

Word's native TOC field updates only in the editor. After `apply_edits.py` runs, open `Final Report Draft.final.docx` in Word or Google Docs and press F9 (Word) or click the TOC and "Update table of contents" (Docs). The current TOC claims 44 pages; the real document is ~57 pages.

## Screenshot capture pipeline

1. From WSL bash, start Docker Compose via PowerShell:
   ```
   powershell.exe -Command "cd 'D:\RPI CAPSTONE\capstone-project'; docker compose up -d"
   ```
2. Wait for health checks on all four services (db, embedding, backend, frontend) — poll `http://localhost:8000/api/health`.
3. Ingest the default corpus if not already present:
   ```
   docker compose exec backend python -m app.scripts.ingest_all
   ```
4. Capture 3 pages at 1920x1080 using the central-db Auto UI Testing bot if discoverable via central-db search, otherwise a direct Playwright script (`scripts/capture_screenshots.py`). Either path produces the same three PNGs:
   - `/` → `landing.png`
   - `/search?q=remote+work+policy` → `search-results.png`
   - `/admin/upload` → `admin-upload.png`
5. Bot discovery happens at the start of the screenshot step — whichever is available is used. Fallback is equally acceptable; both produce the same output.

## Testing strategy

- Each `patch_N_*` function has a paired `verify_N_*` function.
- `apply_edits.py` accepts `--dry-run` flag that runs all patches against a copy, verifies, and reports without writing.
- Visual diff: after full run, open both PDFs side by side (existing + regenerated) to catch any layout surprises. This is a manual QA step, not automated.

## Error handling

- If a patch can't find its target (e.g., heading text changed upstream), it raises a descriptive exception with the expected locator string. Fail fast, no silent skips.
- If the screenshot capture pipeline fails, screenshot patches degrade gracefully: insert the placeholder paragraph with a TODO comment in the DOCX, log the failure, continue with other patches. Better to deliver 4/5 fixes than 0/5.

## Timeline

| Day | Work | Gate |
|---|---|---|
| Thu 2026-04-23 | Spec (this doc), implementation plan, commit, start implementation | Spec approved |
| Fri 2026-04-24 | Run patches 1–5, capture screenshots, produce `Final Report Draft.final.docx` | Output DOCX opens cleanly in Word |
| Sat 2026-04-25 | Circulate to Group Two for review | Team sign-off |
| Sun 2026-04-26 | Apply team feedback, regenerate, upload to Drive as new Google Doc, verify TOC refresh | Google Doc shares cleanly |
| Mon 2026-04-27 AM | Final sanity check, submit | — |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Central-db Auto UI bot can't be located or doesn't fit | Medium | Fallback to Playwright script, pre-written in implementation plan |
| Docker Compose doesn't start on this Windows/WSL setup (e.g., GPU passthrough fails) | Low | External embedding mode already exists (`docker-compose.external-embedding.yml`); fall back if needed |
| A patch's locator string doesn't match because the DOCX was edited upstream | Low-Medium | Patches fail loudly with the expected locator; adjust and rerun |
| Team review surfaces content changes I can't easily script | Low | Day 4 (Sun) is the buffer for hand-edits in the DOCX before export |
| Google Doc upload loses formatting (fonts, table shading) | Medium | Use "Upload file" → "Do not convert" then open, or test with a throwaway upload first |

## Commit strategy

- This spec: one commit (`docs(spec): final-report polish pass design`)
- Implementation plan: one commit (from writing-plans skill)
- Patches: one commit per patch, each with its verify function, so any regression is bisectable
- Screenshots: one commit adding PNGs + updating §8.10 patch
- Final generated DOCX: not committed to git (build artifact; the `.final.docx` is re-generatable from the source + apply_edits.py)
