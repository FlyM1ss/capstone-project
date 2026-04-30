# Final Report Polish Pass — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `Final Report Draft.final.docx` by running five isolated python-docx patches against `coursework/final-report/Final Report Draft.docx`, embedding three UI screenshots into §8.10, and regenerating the Word TOC — closing every deduction from the 2026-04-23 AI instructor feedback without restructuring the 13-section rubric-validated layout.

**Architecture:** A single CLI script `coursework/final-report/apply_edits.py` with `patch_1..patch_5` + paired `verify_1..verify_5` functions + `--dry-run`. A separate `coursework/final-report/capture_screenshots.py` drives docker compose + Playwright (fallback from the central-db UI bot). A locator module `coursework/final-report/locators.py` holds concrete paragraph/table indices derived from a pre-flight scan, so every patch references named constants instead of magic numbers.

**Tech Stack:** python-docx 1.1.x (already installed), Playwright (`pip install playwright && playwright install chromium`), Docker Compose (existing), pytest (new, for the verify harness), requests (for health checks).

**Deadline:** Mon 2026-04-27 23:59 EDT.

**Review checkpoints:** After each of patches 1–5, STOP and let the user open the intermediate DOCX in Word to sanity-check before the next patch applies.

---

## File Structure

```
coursework/final-report/
├── Final Report Draft.docx           (source — read-only for patches)
├── Final Report Draft.final.docx     (build artifact — NOT committed)
├── apply_edits.py                    (NEW — CLI, patch orchestrator)
├── locators.py                       (NEW — frozen paragraph/table indices)
├── capture_screenshots.py            (NEW — docker + playwright driver)
├── build_section12.py                (EXISTING — styling reference)
└── screenshots/
    ├── landing.png                   (NEW)
    ├── search-results.png            (NEW)
    └── admin-upload.png              (NEW)
tests/final_report/                   (NEW)
├── __init__.py
├── conftest.py                       (fixtures: tmp DOCX copies)
├── test_patch_1_screenshots.py
├── test_patch_2_jargon.py
├── test_patch_3_tables.py
├── test_patch_4_copyedit.py
└── test_patch_5_financial.py
```

Each patch lives in `apply_edits.py` as two functions (`patch_N_*` + `verify_N_*`) plus a test module. Patches run in numbered order; each commits independently for bisect safety.

---

## Phase 0 — Pre-flight (locator module)

Before any patch runs, we freeze the paragraph/table indices into a source-controlled Python module. If the source DOCX is edited upstream and indices shift, only `locators.py` needs updating, not every patch.

### Task 0.1: Create locators.py

**Files:**
- Create: `coursework/final-report/locators.py`

- [ ] **Step 1: Write locator module with values from pre-flight scan**

```python
# coursework/final-report/locators.py
"""
Frozen paragraph and table indices for Final Report Draft.docx.

Derived from a pre-flight scan on 2026-04-23. If the source DOCX is
re-exported from Google Docs, re-run `python -m apply_edits --scan` to
regenerate these constants.
"""
from dataclasses import dataclass

# ── Paragraph indices (section headings + specific targets) ───────────
PARA_SECTION_1_HEADING = 16        # "Section 1: Executive Summary"
PARA_SECTION_9_HEADING = 199       # "Section 9: Financial & Cost-Benefit Analysis"
PARA_SECTION_13_HEADING = 359      # "Section 13: Summary and Conclusions"
PARA_HEADING_8_10 = 196            # "8.10 Working System and Screenshots"
PARA_PLACEHOLDER_8_10 = 197        # "Screenshots of the working system will be included..."
PARA_HEADING_IRR = 232             # "Internal Rate of Return (IRR)" (§9.3)

# ── Jargon-rewrite targets (§8.2 – §8.7, selected by jargon density ≥2) ──
# 7 paragraphs, within the spec's 6–10 target range.
PARAS_JARGON_REWRITE = [148, 149, 150, 156, 157, 169, 183]

# ── Table indices ─────────────────────────────────────────────────────
# Real data tables (multi-row, multi-column) — get header shading + alt rows
TABLES_DATA = [0, 1, 2, 5, 6, 9, 10, 11, 12, 13, 14]
# Callout boxes (1x1 single-cell tables) — MUST be skipped by patch 3
TABLES_CALLOUT = [3, 4, 7, 8]

# ── Style conventions from build_section12.py ─────────────────────────
HEADER_FILL_HEX = "2E4057"   # dark navy
ROW_ALT_FILL_HEX = "F2F2F2"  # light grey
FONT_NAME = "Calibri"
FONT_SIZE_BODY_PT = 11
FONT_SIZE_TABLE_PT = 10

# ── Canonical financial figures (from Draft §1 + §9) ──────────────────
CANONICAL_NPV = "$2,168,378"
CANONICAL_ROI = "5,832%"
CANONICAL_PAYBACK = "< 1 year"
CANONICAL_PILOT_COST = "$44,933"
CANONICAL_WORST_CASE_NPV = "$645,033"

# ── Stale figures that must NEVER appear in the final draft ───────────
STALE_FIGURES = ["51.5M", "51,500,000", "5,936", "5936%", "$51.5 million"]


@dataclass(frozen=True)
class PatchPreflight:
    """Run-time confirmation that the DOCX structure still matches."""
    expected_para_count_min: int = 365
    expected_para_count_max: int = 400
    expected_table_count: int = 15
    expected_inline_shape_count_before: int = 11
```

- [ ] **Step 2: Verify locator module imports cleanly**

Run: `python3 -c "from coursework.final_report.locators import PARA_PLACEHOLDER_8_10; print(PARA_PLACEHOLDER_8_10)"`
Expected output: `197`

- [ ] **Step 3: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/locators.py
git commit -m "feat(final-report): freeze locator indices for polish pass"
```

### Task 0.2: Add rescan command to apply_edits.py skeleton

**Files:**
- Create: `coursework/final-report/apply_edits.py` (skeleton only — patches come in later tasks)

- [ ] **Step 1: Write the apply_edits.py CLI skeleton with --scan**

```python
# coursework/final-report/apply_edits.py
"""
Apply surgical polish patches to Final Report Draft.docx.

Usage:
    python apply_edits.py                 # run all patches -> Final Report Draft.final.docx
    python apply_edits.py --dry-run       # run patches against a temp copy, verify only
    python apply_edits.py --scan          # re-enumerate locators and print the values
    python apply_edits.py --only N        # run only patch N (1..5)
    python apply_edits.py --up-to N       # run patches 1..N
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from docx import Document

HERE = Path(__file__).parent
SOURCE = HERE / "Final Report Draft.docx"
OUTPUT = HERE / "Final Report Draft.final.docx"


def scan(source: Path) -> None:
    doc = Document(source)
    print(f"Paragraphs: {len(doc.paragraphs)}")
    print(f"Tables: {len(doc.tables)}")
    print(f"Inline shapes: {len(doc.inline_shapes)}")
    print("\nHeadings:")
    for i, p in enumerate(doc.paragraphs):
        if p.style.name.startswith("Heading") and p.text.strip():
            print(f"  {i:4d} [{p.style.name:10s}] {p.text[:80]}")
    print("\nTables:")
    for i, tbl in enumerate(doc.tables):
        r0 = tbl.rows[0]
        preview = " | ".join(c.text.strip()[:20] for c in r0.cells[:3])
        print(f"  {i:2d}: {len(tbl.rows)}x{len(tbl.columns)}  hdr: {preview}")


def _run_patches(source: Path, target: Path, up_to: int | None, only: int | None) -> int:
    """Skeleton — patches are registered in later tasks."""
    shutil.copy2(source, target)
    # Patches will register here in tasks 2.1 – 2.5 as they land.
    print(f"Wrote {target}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--only", type=int, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--up-to", type=int, choices=[1, 2, 3, 4, 5])
    args = ap.parse_args()

    if args.scan:
        scan(SOURCE)
        return 0

    target = OUTPUT
    if args.dry_run:
        target = HERE / ".dry_run.docx"

    rc = _run_patches(SOURCE, target, up_to=args.up_to, only=args.only)

    if args.dry_run and target.exists():
        target.unlink()
    return rc


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify the skeleton runs**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py --scan | head -20`
Expected: header counts + list of headings matching the locators we baked in (paragraph 196 = "8.10 Working System and Screenshots", 15 tables).

- [ ] **Step 3: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/apply_edits.py
git commit -m "feat(final-report): apply_edits.py skeleton with --scan + --dry-run"
```

### Task 0.3: Add pytest scaffolding

**Files:**
- Create: `tests/final_report/__init__.py` (empty)
- Create: `tests/final_report/conftest.py`

- [ ] **Step 1: Write conftest with a copy-fixture**

```python
# tests/final_report/conftest.py
"""Pytest fixtures for final-report patch tests."""
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SOURCE_DOCX = REPO_ROOT / "coursework" / "final-report" / "Final Report Draft.docx"


@pytest.fixture
def fresh_docx_copy(tmp_path: Path) -> Path:
    """Copy the source DOCX to a tmp location so tests can mutate freely."""
    target = tmp_path / "report.docx"
    shutil.copy2(SOURCE_DOCX, target)
    return target
```

- [ ] **Step 2: Verify pytest discovers the fixture**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/ --collect-only 2>&1 | tail -5`
Expected: `no tests ran` or similar — zero collected, no errors.

- [ ] **Step 3: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add tests/final_report/
git commit -m "test(final-report): add pytest conftest with fresh_docx_copy fixture"
```

---

## Phase 1 — Patch 1: §8.10 screenshots

Depends on the screenshots existing. Screenshot capture is Phase 2 (below) — but we can write the patch + verifier + test first using placeholder image files.

### Task 1.1: Write test for patch_1

**Files:**
- Create: `tests/final_report/test_patch_1_screenshots.py`

- [ ] **Step 1: Write the test**

```python
# tests/final_report/test_patch_1_screenshots.py
"""Patch 1: §8.10 placeholder replaced with 3 screenshots + captions."""
from pathlib import Path

import pytest
from docx import Document

from coursework.final_report.apply_edits import patch_1_8_10_screenshots, verify_1


@pytest.fixture
def fake_screenshots(tmp_path: Path) -> dict[str, Path]:
    """Create 3 tiny PNG stubs so patch_1 can embed them."""
    # 1x1 PNG, minimal valid file
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c626001000000050001a5f645400000000049454e44ae426082"
    )
    out = {}
    for name in ("landing.png", "search-results.png", "admin-upload.png"):
        p = tmp_path / name
        p.write_bytes(png)
        out[name] = p
    return out


def test_patch_1_removes_placeholder_and_adds_3_images(
    fresh_docx_copy: Path, fake_screenshots: dict[str, Path]
):
    patch_1_8_10_screenshots(fresh_docx_copy, fake_screenshots)
    doc = Document(fresh_docx_copy)

    # Placeholder text must be gone
    body_text = "\n".join(p.text for p in doc.paragraphs)
    assert "will be included in the final version" not in body_text

    # 3 new inline shapes should have been added
    assert len(doc.inline_shapes) == 14  # 11 existing + 3 new

    # Verify_1 must pass against the mutated DOCX
    assert verify_1(fresh_docx_copy) is True
```

- [ ] **Step 2: Run to confirm failure (function not imported yet)**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_1_screenshots.py -v 2>&1 | tail -5`
Expected: ImportError on `patch_1_8_10_screenshots`.

### Task 1.2: Implement patch_1 + verify_1

**Files:**
- Modify: `coursework/final-report/apply_edits.py`

- [ ] **Step 1: Add patch and verify functions**

Insert at the top of `apply_edits.py` below the imports, before `def scan`:

```python
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from coursework.final_report import locators as L


# ═════════════════════════════════════════════════════════════════════
# Patch 1: §8.10 screenshots
# ═════════════════════════════════════════════════════════════════════
CAPTION_STYLE_NAME = "Caption"

SCREENSHOT_SPECS = [
    (
        "landing.png",
        "Figure 8.10.1: Landing page with natural language search input.",
        "The landing page accepts plain-English queries and surfaces the core "
        "value proposition above the fold.",
    ),
    (
        "search-results.png",
        "Figure 8.10.2: Search results with relevance scores, metadata, and filters.",
        "Each result card shows the document title, a scored relevance indicator, "
        "snippet highlights, and filter controls for role-based access and document type.",
    ),
    (
        "admin-upload.png",
        "Figure 8.10.3: Admin upload portal with drag-and-drop ingestion.",
        "Administrators can queue new documents through a drag-and-drop panel; "
        "ingestion status is reported inline.",
    ),
]


def patch_1_8_10_screenshots(docx_path: Path, screenshots: dict[str, Path]) -> None:
    doc = Document(docx_path)

    # Confirm the placeholder is where we expect
    placeholder = doc.paragraphs[L.PARA_PLACEHOLDER_8_10]
    if "will be included in the final version" not in placeholder.text:
        raise RuntimeError(
            f"§8.10 placeholder not found at paragraph {L.PARA_PLACEHOLDER_8_10}. "
            f"Got: {placeholder.text[:120]!r}"
        )

    # Rewrite the placeholder paragraph as the new lead-in
    placeholder.text = (
        "The working prototype exposes three primary interfaces, captured below. "
        "Each screenshot is drawn from the live system running via docker compose "
        "against the full 80-document corpus."
    )

    # Append 3 figure blocks (image + caption + description) after the placeholder.
    # python-docx does not expose insert-after natively; we use the underlying XML.
    from docx.oxml.ns import qn
    anchor_xml = placeholder._element

    for name, caption, desc in SCREENSHOT_SPECS:
        png_path = screenshots[name]

        # Image paragraph
        img_para = doc.add_paragraph()
        img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = img_para.add_run()
        run.add_picture(str(png_path), width=Inches(6.0))

        # Caption paragraph (italic)
        cap_para = doc.add_paragraph()
        cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_run = cap_para.add_run(caption)
        cap_run.italic = True
        cap_run.font.size = Pt(10)

        # Description paragraph
        desc_para = doc.add_paragraph(desc)
        desc_para.paragraph_format.space_after = Pt(12)

        # python-docx adds these at end-of-body; move them right after anchor
        for xml_para in (img_para._element, cap_para._element, desc_para._element):
            anchor_xml.addnext(xml_para)
            anchor_xml = xml_para  # chain so next one lands after previous

    doc.save(docx_path)


def verify_1(docx_path: Path) -> bool:
    doc = Document(docx_path)
    body_text = "\n".join(p.text for p in doc.paragraphs)
    if "will be included in the final version" in body_text:
        raise AssertionError("Patch 1 failed: placeholder text still present.")
    if len(doc.inline_shapes) < 14:
        raise AssertionError(
            f"Patch 1 failed: expected >=14 inline shapes, got {len(doc.inline_shapes)}."
        )
    return True
```

- [ ] **Step 2: Register patch_1 in _run_patches**

Replace the `_run_patches` body with:

```python
def _run_patches(source: Path, target: Path, up_to: int | None, only: int | None) -> int:
    shutil.copy2(source, target)

    screenshots_dir = HERE / "screenshots"
    screenshots = {
        name: screenshots_dir / name
        for name in ("landing.png", "search-results.png", "admin-upload.png")
    }

    patches = [
        (1, lambda: patch_1_8_10_screenshots(target, screenshots), verify_1),
        # 2..5 land in later tasks
    ]

    for n, run_fn, verify_fn in patches:
        if only is not None and only != n:
            continue
        if up_to is not None and n > up_to:
            break
        print(f"Running patch {n}...")
        run_fn()
        verify_fn(target)
        print(f"  ✓ patch {n} verified")

    print(f"Wrote {target}")
    return 0
```

- [ ] **Step 3: Run the test**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_1_screenshots.py -v 2>&1 | tail -5`
Expected: `1 passed`.

- [ ] **Step 4: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/apply_edits.py tests/final_report/test_patch_1_screenshots.py
git commit -m "feat(final-report): patch 1 — replace §8.10 placeholder with 3 screenshot blocks"
```

### REVIEW CHECKPOINT A (after patch 1)

STOP. Report to the user:
> Patch 1 landed + test green. Screenshots still use stub 1x1 PNGs — real captures come in Phase 2. Open `Final Report Draft.final.docx` once Phase 2 finishes to confirm the §8.10 layout. Proceed to patch 2?

---

## Phase 2 — Screenshots (capture pipeline)

### Task 2.1: Write capture_screenshots.py

**Files:**
- Create: `coursework/final-report/capture_screenshots.py`
- Create: `coursework/final-report/screenshots/.gitkeep`

- [ ] **Step 1: Write capture script (Playwright primary)**

```python
# coursework/final-report/capture_screenshots.py
"""
Capture three UI screenshots for final-report §8.10.

Assumes:
  - docker compose up -d has already started the stack (ports 3000, 8000)
  - Playwright is installed: pip install playwright && playwright install chromium
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
OUT_DIR = HERE / "screenshots"
OUT_DIR.mkdir(exist_ok=True)

FRONTEND = "http://localhost:3000"
BACKEND_HEALTH = "http://localhost:8000/api/health"
VIEWPORT = {"width": 1920, "height": 1080}

TARGETS = [
    ("/",                         "landing.png"),
    ("/search?q=remote+work+policy", "search-results.png"),
    ("/admin/upload",             "admin-upload.png"),
]


def wait_for_health(url: str, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"Backend never healthy at {url} within {timeout_s}s")


def capture(page, route: str, out: Path) -> None:
    page.goto(FRONTEND + route, wait_until="networkidle", timeout=30_000)
    # Give any client-side hydration a beat to settle
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out), full_page=False)
    print(f"  wrote {out.name} ({out.stat().st_size} bytes)")


def main() -> int:
    print("Waiting for backend health...")
    wait_for_health(BACKEND_HEALTH)
    print("Backend healthy. Capturing screenshots...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = context.new_page()
        for route, fname in TARGETS:
            capture(page, route, OUT_DIR / fname)
        browser.close()

    print(f"\nAll 3 screenshots written to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Install playwright**

Run: `pip install playwright && python3 -m playwright install chromium 2>&1 | tail -3`
Expected: "Chromium installed" or already-present message.

- [ ] **Step 3: Create the screenshots dir (committed; PNGs will be added in Task 2.2)**

```bash
touch "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report/screenshots/.gitkeep"
```

Screenshots are committed (not gitignored): regeneration depends on the live stack running, so baking the reviewed PNGs into git protects against stack drift between now and submission.

- [ ] **Step 4: Commit the script (no screenshots yet)**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/capture_screenshots.py coursework/final-report/screenshots/.gitkeep
git commit -m "feat(final-report): playwright screenshot capture driver"
```

### Task 2.2: Run the full capture pipeline

- [ ] **Step 1: Start docker stack from WSL**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && powershell.exe -Command "cd 'D:\RPI CAPSTONE\capstone-project'; docker compose up -d" 2>&1 | tail -10`
Expected: 4 services started (db, embedding, backend, frontend) or "already running."

- [ ] **Step 2: Verify corpus is ingested**

Run: `curl -s http://localhost:8000/api/health` 
Expected: `{"status":"ok"}` (or similar success JSON).

If the DB has no documents, ingest:
```bash
powershell.exe -Command "cd 'D:\RPI CAPSTONE\capstone-project'; docker compose exec backend python -m app.scripts.ingest_all"
```

- [ ] **Step 3: Run capture script**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 capture_screenshots.py 2>&1 | tail -10`
Expected: 3 PNG files in `screenshots/` each > 50KB (real content, not a 1x1 stub).

- [ ] **Step 4: Manually eyeball each screenshot**

Open each PNG in an image viewer; confirm the UI is rendered correctly (not a blank page, not an error toast). If any is wrong, re-run step 3.

- [ ] **Step 5: Commit the screenshots**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/screenshots/*.png
git commit -m "feat(final-report): capture 3 UI screenshots for §8.10"
```

### Task 2.3: Re-run apply_edits.py with real screenshots

- [ ] **Step 1: Regenerate final DOCX**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py --up-to 1 2>&1 | tail -5`
Expected: `Running patch 1... ✓ patch 1 verified` then `Wrote Final Report Draft.final.docx`.

- [ ] **Step 2: Open output in Word or LibreOffice**

Eyeball §8.10: 3 screenshots should be centered, captioned, and followed by description text.

### REVIEW CHECKPOINT B (after real screenshots embedded)

STOP. Report:
> Real screenshots embedded, §8.10 should now be complete. Confirm visually before moving to patch 2 (jargon simplification).

---

## Phase 3 — Patch 2: simplify jargon (§8.2–§8.7)

Six paragraph rewrites. Each rewrite keeps the technical precision but adds a business-impact clause. Locator indices: `L.PARAS_JARGON_REWRITE = [148, 149, 156, 157, 169, 183]`.

### Task 3.1: Write test for patch_2

**Files:**
- Create: `tests/final_report/test_patch_2_jargon.py`

- [ ] **Step 1: Write the test**

```python
# tests/final_report/test_patch_2_jargon.py
"""Patch 2: six targeted rewrites across §8.2 – §8.7."""
from pathlib import Path

from docx import Document

from coursework.final_report.apply_edits import patch_2_simplify_jargon, verify_2


# Expected: each rewrite keeps one or more technical anchor terms AND
# adds at least one plain-language business phrase.
EXPECTED_BUSINESS_PHRASES = [
    "within milliseconds",              # para 148 (Processing Layer)
    "single database instance",         # para 149 (Data Layer)
    "numerical representation",         # para 150 (External services)
    "three retrieval signals",          # para 156 (parallel retrieval)
    "combines the strengths",           # para 157 (RRF explanation)
    "searchable representation",        # para 169 (document_chunks)
    "merge strategy",                   # para 183 (hybrid fusion)
]


def test_patch_2_rewrites_target_paragraphs(fresh_docx_copy: Path):
    patch_2_simplify_jargon(fresh_docx_copy)
    doc = Document(fresh_docx_copy)

    text_by_para = {i: p.text for i, p in enumerate(doc.paragraphs)}

    targets = [148, 149, 150, 156, 157, 169, 183]
    for i, phrase in zip(targets, EXPECTED_BUSINESS_PHRASES):
        assert phrase in text_by_para[i], (
            f"Paragraph {i} missing expected business phrase {phrase!r}. "
            f"Got: {text_by_para[i][:200]!r}"
        )

    assert verify_2(fresh_docx_copy) is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_2_jargon.py -v 2>&1 | tail -5`
Expected: ImportError on `patch_2_simplify_jargon`.

### Task 3.2: Implement patch_2 + verify_2

**Files:**
- Modify: `coursework/final-report/apply_edits.py`

- [ ] **Step 1: Add patch_2 function**

Append to `apply_edits.py` after verify_1:

```python
# ═════════════════════════════════════════════════════════════════════
# Patch 2: simplify jargon for executive audience (§8.2 – §8.7)
# ═════════════════════════════════════════════════════════════════════

# Six rewrites, each keyed by paragraph index. Each replaces the full text
# of the target paragraph. Technical anchors are kept; business-impact
# clauses are added.
JARGON_REWRITES: dict[int, str] = {
    148: (
        "The Processing Layer contains the system's core business logic. "
        "The search service orchestrates the hybrid retrieval pipeline — "
        "converting each query into a numerical representation, running three "
        "retrieval signals against the database in parallel, and returning a "
        "ranked result list within milliseconds. Reranking and access-control "
        "filtering run as final steps before results reach the user."
    ),
    149: (
        "The Data Layer centers on a single database instance running the "
        "ParadeDB image, which bundles PostgreSQL with two extensions the "
        "system relies on: pgvector for semantic (meaning-based) search and "
        "pg_search for keyword search. Consolidating both capabilities into "
        "one database removes the operational overhead of running a separate "
        "vector store, and keeps every search signal within the same "
        "transactional boundary."
    ),
    150: (
        "External services include the Qwen3-Embedding-0.6B model (deployed "
        "locally or via an external GPU host) and the Cohere Rerank v3.5 API. "
        "The embedding model converts text to a numerical representation the "
        "database can search; the reranker reorders the top candidates by "
        "deeper relevance before they are shown to the user."
    ),
    156: (
        "The system performs three retrieval signals in parallel against a "
        "single database call. A semantic search finds chunks whose meaning "
        "matches the query; a keyword search finds chunks whose words match; "
        "and a title search boosts documents whose title alone closely "
        "matches the query. Running these in parallel keeps total latency "
        "bounded by the slowest single signal, not their sum."
    ),
    157: (
        "The three ranked lists are merged using Reciprocal Rank Fusion (RRF), "
        "a rank aggregation method that combines the strengths of each signal "
        "without requiring hand-tuned weights. RRF rewards documents that "
        "rank highly across multiple signals and penalizes documents that "
        "appear only in one, which makes the final ranking resilient to "
        "any single signal's weaknesses."
    ),
    169: (
        "The document_chunks table stores the searchable representation of "
        "each document. Every row holds a segment of text (roughly 512 "
        "tokens), its numerical embedding, its parent document ID, and the "
        "access-control level it inherits. A specialized index on the "
        "embedding column (HNSW) enables meaning-based lookups in "
        "milliseconds, even as the table grows."
    ),
    183: (
        "The fourth decision was the merge strategy for combining the three "
        "retrieval signals. Rather than a linear combination — which would "
        "require hand-tuned weights and would quietly drift as the corpus "
        "changes — the system uses Reciprocal Rank Fusion. RRF is "
        "parameter-free relative to query content, scales naturally from "
        "dozens to millions of documents, and degrades gracefully if any "
        "one signal underperforms."
    ),
}


def patch_2_simplify_jargon(docx_path: Path) -> None:
    doc = Document(docx_path)
    for idx, new_text in JARGON_REWRITES.items():
        para = doc.paragraphs[idx]
        # Keep the paragraph's style; replace only the text
        # python-docx: setting .text clears runs and formats — acceptable here
        # because these body paragraphs have no inline formatting to preserve
        para.text = new_text
    doc.save(docx_path)


def verify_2(docx_path: Path) -> bool:
    doc = Document(docx_path)
    for idx, new_text in JARGON_REWRITES.items():
        actual = doc.paragraphs[idx].text
        # Allow whitespace-only differences
        if actual.strip() != new_text.strip():
            raise AssertionError(
                f"Patch 2 failed at paragraph {idx}: expected rewrite not present."
            )
    return True
```

- [ ] **Step 2: Register patch_2 in _run_patches**

Update the `patches` list in `_run_patches`:

```python
    patches = [
        (1, lambda: patch_1_8_10_screenshots(target, screenshots), verify_1),
        (2, lambda: patch_2_simplify_jargon(target), verify_2),
    ]
```

- [ ] **Step 3: Run the test**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_2_jargon.py -v 2>&1 | tail -5`
Expected: `1 passed`.

- [ ] **Step 4: Run patch via CLI**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py --up-to 2 2>&1 | tail -5`
Expected: both patches succeed.

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/apply_edits.py tests/final_report/test_patch_2_jargon.py
git commit -m "feat(final-report): patch 2 — simplify jargon in §8.2-§8.7 for exec audience"
```

### REVIEW CHECKPOINT C (after patch 2)

STOP. Report:
> Patch 2 landed. 7 paragraphs rewritten across §8.2-§8.7 with technical anchors kept + business clauses added. Please open Final Report Draft.final.docx and skim those sections before patch 3. Proceed?

---

## Phase 4 — Patch 3: normalize table formatting

### Task 4.1: Write test for patch_3

**Files:**
- Create: `tests/final_report/test_patch_3_tables.py`

- [ ] **Step 1: Write the test**

```python
# tests/final_report/test_patch_3_tables.py
"""Patch 3: uniform header shading + alternating rows on all data tables."""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from coursework.final_report.apply_edits import patch_3_normalize_tables, verify_3
from coursework.final_report import locators as L


def _cell_fill(cell) -> str | None:
    shd = cell._element.find(qn("w:tcPr") + "/" + qn("w:shd"))
    if shd is None:
        return None
    return shd.get(qn("w:fill"))


def test_patch_3_applies_header_and_alt_shading(fresh_docx_copy: Path):
    patch_3_normalize_tables(fresh_docx_copy)
    doc = Document(fresh_docx_copy)

    for t_idx in L.TABLES_DATA:
        tbl = doc.tables[t_idx]
        # Header row: every cell has fill = HEADER_FILL_HEX
        for c in tbl.rows[0].cells:
            assert _cell_fill(c) == L.HEADER_FILL_HEX, (
                f"Table {t_idx} header cell missing navy fill"
            )
        # Odd data rows (1-indexed row #) should have alt fill
        for row_idx in range(1, len(tbl.rows)):
            expected = L.ROW_ALT_FILL_HEX if row_idx % 2 == 1 else None
            for c in tbl.rows[row_idx].cells:
                got = _cell_fill(c)
                if expected is None:
                    assert got in (None, "auto"), (
                        f"Table {t_idx} row {row_idx} unexpected fill {got}"
                    )
                else:
                    assert got == expected, (
                        f"Table {t_idx} row {row_idx} fill got {got} expected {expected}"
                    )

    # Callout tables MUST NOT be touched
    for t_idx in L.TABLES_CALLOUT:
        tbl = doc.tables[t_idx]
        # Single-cell callout — header logic shouldn't have applied a navy fill
        fill = _cell_fill(tbl.rows[0].cells[0])
        assert fill != L.HEADER_FILL_HEX, (
            f"Callout table {t_idx} was incorrectly shaded as a data-table header"
        )

    assert verify_3(fresh_docx_copy) is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_3_tables.py -v 2>&1 | tail -5`
Expected: ImportError.

### Task 4.2: Implement patch_3 + verify_3

**Files:**
- Modify: `coursework/final-report/apply_edits.py`

- [ ] **Step 1: Add patch_3**

Append:

```python
# ═════════════════════════════════════════════════════════════════════
# Patch 3: normalize table formatting (data tables only, not callouts)
# ═════════════════════════════════════════════════════════════════════
from docx.oxml.ns import qn as _qn
from docx.oxml import OxmlElement


def _set_cell_fill(cell, fill_hex: str) -> None:
    tcPr = cell._element.get_or_add_tcPr()
    # Remove any existing <w:shd>
    for old in tcPr.findall(_qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(_qn("w:val"), "clear")
    shd.set(_qn("w:color"), "auto")
    shd.set(_qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _clear_cell_fill(cell) -> None:
    tcPr = cell._element.get_or_add_tcPr()
    for old in tcPr.findall(_qn("w:shd")):
        tcPr.remove(old)


def _style_header_cell(cell) -> None:
    _set_cell_fill(cell, L.HEADER_FILL_HEX)
    for p in cell.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(L.FONT_SIZE_TABLE_PT)
            run.font.name = L.FONT_NAME
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _style_body_cell(cell, shaded: bool) -> None:
    if shaded:
        _set_cell_fill(cell, L.ROW_ALT_FILL_HEX)
    else:
        _clear_cell_fill(cell)
    for p in cell.paragraphs:
        for run in p.runs:
            run.font.size = Pt(L.FONT_SIZE_TABLE_PT)
            run.font.name = L.FONT_NAME


def patch_3_normalize_tables(docx_path: Path) -> None:
    doc = Document(docx_path)
    for t_idx in L.TABLES_DATA:
        tbl = doc.tables[t_idx]
        # Header row
        for cell in tbl.rows[0].cells:
            _style_header_cell(cell)
        # Body rows with alternating shading
        for row_idx in range(1, len(tbl.rows)):
            shaded = (row_idx % 2 == 1)
            for cell in tbl.rows[row_idx].cells:
                _style_body_cell(cell, shaded)
    doc.save(docx_path)


def verify_3(docx_path: Path) -> bool:
    doc = Document(docx_path)
    for t_idx in L.TABLES_DATA:
        tbl = doc.tables[t_idx]
        # Header shading present
        for cell in tbl.rows[0].cells:
            tcPr = cell._element.find(_qn("w:tcPr"))
            shd = tcPr.find(_qn("w:shd")) if tcPr is not None else None
            if shd is None or shd.get(_qn("w:fill")) != L.HEADER_FILL_HEX:
                raise AssertionError(
                    f"Patch 3 failed: table {t_idx} header missing navy fill"
                )
    return True
```

- [ ] **Step 2: Register patch_3**

```python
    patches = [
        (1, lambda: patch_1_8_10_screenshots(target, screenshots), verify_1),
        (2, lambda: patch_2_simplify_jargon(target), verify_2),
        (3, lambda: patch_3_normalize_tables(target), verify_3),
    ]
```

- [ ] **Step 3: Run the test**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_3_tables.py -v 2>&1 | tail -5`
Expected: `1 passed`.

- [ ] **Step 4: Run CLI**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py --up-to 3 2>&1 | tail -5`

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/apply_edits.py tests/final_report/test_patch_3_tables.py
git commit -m "feat(final-report): patch 3 — uniform table header/row shading on data tables"
```

### REVIEW CHECKPOINT D (after patch 3)

STOP. Report:
> Patch 3 landed. All 11 data tables now carry navy headers + alternating rows; the 4 callout tables (3, 4, 7, 8) deliberately untouched. Open the output DOCX and flip through — every data table should look consistent. Proceed to patch 4?

---

## Phase 5 — Patch 4: copyedit pass

### Task 5.1: Write test for patch_4

**Files:**
- Create: `tests/final_report/test_patch_4_copyedit.py`

- [ ] **Step 1: Write the test**

```python
# tests/final_report/test_patch_4_copyedit.py
"""Patch 4: em-dashes removed, redundancies trimmed."""
from pathlib import Path

from docx import Document

from coursework.final_report.apply_edits import patch_4_copyedit_pass, verify_4


def _all_body_text(doc) -> str:
    parts = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append(p.text)
    return "\n".join(parts)


def test_patch_4_removes_em_dashes(fresh_docx_copy: Path):
    patch_4_copyedit_pass(fresh_docx_copy)
    doc = Document(fresh_docx_copy)
    text = _all_body_text(doc)
    assert "—" not in text, (
        f"Expected 0 em-dashes; found {text.count(chr(0x2014))}"
    )
    # Redundant phrases gone
    assert "in order to" not in text.lower()
    assert verify_4(fresh_docx_copy) is True
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_4_copyedit.py -v 2>&1 | tail -5`
Expected: ImportError.

### Task 5.2: Implement patch_4 + verify_4

**Files:**
- Modify: `coursework/final-report/apply_edits.py`

- [ ] **Step 1: Add patch_4**

Append:

```python
# ═════════════════════════════════════════════════════════════════════
# Patch 4: copyedit pass — em-dashes, redundancies, transitions
# ═════════════════════════════════════════════════════════════════════

# Global text substitutions applied to every paragraph run.
# Order matters: longer patterns first to avoid partial-match hazards.
COPYEDIT_REPLACEMENTS: list[tuple[str, str]] = [
    # Em-dash → comma/period (project global rule). The right replacement
    # depends on context; we default to ", " which is a safe sentence-internal
    # pause. Cases where the em-dash bounds a parenthetical will still read
    # cleanly as a comma.
    ("—", ", "),
    # Redundancy removal
    (" in order to ", " to "),
    (" In order to ", " To "),
    # Tense consistency (a few recurring slips in the draft)
    (" will be able to ", " can "),
    # Double-space typos
    ("  ", " "),
]


def _replace_in_runs(para, old: str, new: str) -> None:
    """Walk paragraph runs and replace old→new while preserving per-run formatting."""
    if old not in para.text:
        return
    # Simple case: one run — direct swap
    if len(para.runs) == 1:
        para.runs[0].text = para.runs[0].text.replace(old, new)
        return
    # Multi-run case: join, replace, then rewrite into first run and blank others.
    # This loses intra-paragraph formatting but is acceptable for body prose.
    joined = "".join(r.text for r in para.runs).replace(old, new)
    para.runs[0].text = joined
    for r in para.runs[1:]:
        r.text = ""


def patch_4_copyedit_pass(docx_path: Path) -> None:
    doc = Document(docx_path)

    def walk_paragraphs():
        for p in doc.paragraphs:
            yield p
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        yield p

    for para in walk_paragraphs():
        if not para.text:
            continue
        for old, new in COPYEDIT_REPLACEMENTS:
            _replace_in_runs(para, old, new)

    doc.save(docx_path)


def verify_4(docx_path: Path) -> bool:
    doc = Document(docx_path)
    def _text():
        for p in doc.paragraphs:
            yield p.text
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        yield p.text
    full = "\n".join(_text())
    if "—" in full:
        n = full.count("—")
        raise AssertionError(f"Patch 4 failed: {n} em-dash(es) remain")
    if "in order to" in full.lower():
        raise AssertionError("Patch 4 failed: 'in order to' still present")
    return True
```

- [ ] **Step 2: Register patch_4**

```python
    patches = [
        (1, lambda: patch_1_8_10_screenshots(target, screenshots), verify_1),
        (2, lambda: patch_2_simplify_jargon(target), verify_2),
        (3, lambda: patch_3_normalize_tables(target), verify_3),
        (4, lambda: patch_4_copyedit_pass(target), verify_4),
    ]
```

- [ ] **Step 3: Run the test**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_4_copyedit.py -v 2>&1 | tail -5`
Expected: `1 passed`.

- [ ] **Step 4: Run CLI**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py --up-to 4 2>&1 | tail -5`

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/apply_edits.py tests/final_report/test_patch_4_copyedit.py
git commit -m "feat(final-report): patch 4 — copyedit pass (em-dashes, redundancies)"
```

### REVIEW CHECKPOINT E (after patch 4)

STOP. Report:
> Patch 4 landed: 26 em-dashes removed, 'in order to' → 'to' throughout, double-space typos cleaned. Open the DOCX and spot-check a few spots where em-dashes used to live — make sure the comma replacement reads naturally. If any read awkwardly, I'll hand-patch those paragraphs before patch 5.

---

## Phase 6 — Patch 5: financial consistency guardrail

### Task 6.1: Write test for patch_5

**Files:**
- Create: `tests/final_report/test_patch_5_financial.py`

- [ ] **Step 1: Write the test**

```python
# tests/final_report/test_patch_5_financial.py
"""Patch 5: guardrail — no stale figures, §1 and §9.3 IRR agree."""
from pathlib import Path

from docx import Document

from coursework.final_report.apply_edits import patch_5_financial_consistency, verify_5
from coursework.final_report import locators as L


def test_patch_5_passes_on_clean_doc(fresh_docx_copy: Path):
    # Apply patch 5 on the untouched source — should no-op and pass.
    patch_5_financial_consistency(fresh_docx_copy)
    assert verify_5(fresh_docx_copy) is True


def test_patch_5_halts_on_injected_stale_figure(fresh_docx_copy: Path):
    # Inject a stale figure and confirm patch 5 halts.
    doc = Document(fresh_docx_copy)
    doc.paragraphs[L.PARA_SECTION_13_HEADING + 1].text += " NPV is $51.5M."
    doc.save(fresh_docx_copy)

    try:
        patch_5_financial_consistency(fresh_docx_copy)
        raise AssertionError("Patch 5 should have raised on stale $51.5M")
    except RuntimeError as e:
        assert "51.5M" in str(e)
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_5_financial.py -v 2>&1 | tail -5`
Expected: ImportError.

### Task 6.2: Implement patch_5 + verify_5

**Files:**
- Modify: `coursework/final-report/apply_edits.py`

- [ ] **Step 1: Add patch_5**

Append:

```python
# ═════════════════════════════════════════════════════════════════════
# Patch 5: financial consistency guardrail
# ═════════════════════════════════════════════════════════════════════
import re


def _all_body_text(doc) -> str:
    parts = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append(p.text)
    return "\n".join(parts)


def _extract_irr(text_block: str) -> str | None:
    """Find the first IRR percentage in a chunk of text."""
    m = re.search(r"IRR[^0-9]{0,30}([0-9][0-9,\.]*)\s*%", text_block, re.IGNORECASE)
    return m.group(1) if m else None


def patch_5_financial_consistency(docx_path: Path) -> None:
    doc = Document(docx_path)
    full_text = _all_body_text(doc)

    # 1. Stale-figure scan
    for stale in L.STALE_FIGURES:
        if stale in full_text:
            raise RuntimeError(
                f"Patch 5 halt: stale figure {stale!r} found in document. "
                "Manual review required — canonical figures are in locators.py."
            )

    # 2. IRR consistency between §1 (Executive Summary) and §9.3 (IRR subsection)
    # Grab ~2000 chars after each heading for comparison.
    paras = [p.text for p in doc.paragraphs]
    sec1_block = " ".join(paras[L.PARA_SECTION_1_HEADING:L.PARA_SECTION_1_HEADING + 20])
    sec9_block = " ".join(paras[L.PARA_HEADING_IRR:L.PARA_HEADING_IRR + 8])

    irr_1 = _extract_irr(sec1_block)
    irr_9 = _extract_irr(sec9_block)

    if irr_1 and irr_9 and irr_1 != irr_9:
        # Normalize commas for comparison
        if irr_1.replace(",", "") != irr_9.replace(",", ""):
            raise RuntimeError(
                f"Patch 5 halt: IRR disagreement — §1 reports {irr_1}%, "
                f"§9.3 reports {irr_9}%. Reconcile before submitting."
            )

    # Patch 5 is a no-op in the common case. doc.save is skipped.


def verify_5(docx_path: Path) -> bool:
    # verify_5 simply re-runs the patch and trusts it to raise if broken.
    patch_5_financial_consistency(docx_path)
    return True
```

- [ ] **Step 2: Register patch_5**

```python
    patches = [
        (1, lambda: patch_1_8_10_screenshots(target, screenshots), verify_1),
        (2, lambda: patch_2_simplify_jargon(target), verify_2),
        (3, lambda: patch_3_normalize_tables(target), verify_3),
        (4, lambda: patch_4_copyedit_pass(target), verify_4),
        (5, lambda: patch_5_financial_consistency(target), verify_5),
    ]
```

- [ ] **Step 3: Run tests**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project" && python3 -m pytest tests/final_report/test_patch_5_financial.py -v 2>&1 | tail -5`
Expected: `2 passed` (one happy path, one halt path).

- [ ] **Step 4: Run full pipeline**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py 2>&1 | tail -10`
Expected: all 5 patches verified; `Wrote Final Report Draft.final.docx`.

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
git add coursework/final-report/apply_edits.py tests/final_report/test_patch_5_financial.py
git commit -m "feat(final-report): patch 5 — financial consistency guardrail (scan + IRR check)"
```

### REVIEW CHECKPOINT F (after patch 5)

STOP. Report:
> All 5 patches landed + tests green + full pipeline runs clean end-to-end. `Final Report Draft.final.docx` exists and is the candidate for Google Drive upload. Next: manual TOC refresh, final visual QA, upload.

---

## Phase 7 — Final integration + manual TOC refresh

### Task 7.1: Run the full pipeline and capture output stats

- [ ] **Step 1: Run apply_edits.py end-to-end**

Run: `cd "/mnt/d/RPI CAPSTONE/capstone-project/coursework/final-report" && python3 apply_edits.py 2>&1 | tee /tmp/final-run.log | tail -15`
Expected: all 5 patches report "✓ patch N verified", output DOCX written.

- [ ] **Step 2: Check output DOCX metadata**

Run: `python3 -c "from docx import Document; d = Document('coursework/final-report/Final Report Draft.final.docx'); print(f'Paragraphs: {len(d.paragraphs)}'); print(f'Tables: {len(d.tables)}'); print(f'Images: {len(d.inline_shapes)}')"`
Expected: paragraphs ~390, tables 15, images 14 (11 original + 3 screenshots).

### Task 7.2: Manual TOC refresh

**This step is manual — python-docx cannot trigger Word's TOC field refresh.**

- [ ] **Step 1: Open the final DOCX in Microsoft Word or Google Docs**

- [ ] **Step 2: Refresh the TOC**
  - Word: click the Table of Contents → press F9 → choose "Update entire table"
  - Google Docs: upload to Drive → open as Google Doc → click the TOC → "Update table of contents"

- [ ] **Step 3: Verify TOC now shows ~57 pages, not the stale 44**

- [ ] **Step 4: Save the refreshed DOCX back over `Final Report Draft.final.docx`** (or accept the Google Docs version as canonical)

### Task 7.3: Final visual QA pass

- [ ] **Step 1: Open both PDFs side-by-side in two windows**
  - Original: `coursework/final-report/Final Report Draft 1.pdf`
  - New: export `Final Report Draft.final.docx` to PDF for comparison

- [ ] **Step 2: Flip through section-by-section**. Confirm:
  - §8.10 shows 3 screenshots with captions
  - §8.2-§8.7 reads more business-friendly than before
  - Every data table has navy header + alternating rows
  - No em-dashes visible anywhere
  - Financial figures in §1 and §9 agree
  - TOC page numbers are accurate

- [ ] **Step 3: Upload to Google Drive as a new Google Doc**

Via browser: Drive → New → File upload → `Final Report Draft.final.docx` → right-click → "Open with Google Docs" → File → Save as Google Doc.

- [ ] **Step 4: Share with Group Two for review**

### Task 7.4: Update central-db spec status

- [ ] **Step 1: Mark the spec completed in central-db**

Edit `/mnt/d/CENTRAL-DATABASE/specs/itws4100-final-report-03.md`: change `status: approved` → `status: in_progress` while patches run; change to `status: completed` only after the Google Doc is uploaded and shared.

- [ ] **Step 2: Re-index and commit**

```bash
cd /mnt/d/CENTRAL-DATABASE
.venv/Scripts/python.exe scripts/build_index.py --validate 2>&1 | tr -d '\r'
git add specs/itws4100-final-report-03.md
git commit -m "spec: mark itws4100-final-report-03 completed"
```

- [ ] **Step 3: Close the queue task**

Via MCP: `mcp__central-db-queue__complete_current_task(task_id="itws4100-final-report-03")`.

---

## Rollback Procedure

If any patch corrupts the DOCX in a way the verify function doesn't catch:

```bash
cd "/mnt/d/RPI CAPSTONE/capstone-project"
# Identify the last-good commit
git log --oneline -10 | grep "feat(final-report)"
# Reset apply_edits.py to a known-good state
git checkout <commit-sha> -- coursework/final-report/apply_edits.py
# Regenerate from source
cd coursework/final-report && python3 apply_edits.py --up-to <last_good_patch_N>
```

Because each patch has its own commit, `git bisect` can isolate which patch introduced a regression.

---

## Self-review checklist (for the executing agent)

Before reporting the plan complete, confirm:
- [ ] All 10 acceptance criteria in `specs/itws4100-final-report-03.md` pass
- [ ] Output DOCX opens in Word 2019+ and Google Docs without corruption warnings
- [ ] `pytest tests/final_report/` runs all 5 test modules green
- [ ] No em-dashes in the output DOCX body text (confirmed by `verify_4`)
- [ ] `apply_edits.py --dry-run` exits 0
- [ ] Screenshots at `coursework/final-report/screenshots/*.png` are real (not stubs)
- [ ] Google Doc shared with Group Two, link verified
