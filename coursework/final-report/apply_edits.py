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
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

import locators as L

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


# ═════════════════════════════════════════════════════════════════════
# Patch 1: §8.10 screenshots
# ═════════════════════════════════════════════════════════════════════

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
    # python-docx's add_* methods append to end-of-body; we use the underlying
    # XML addnext() to chain them right after the lead-in paragraph.
    anchor_xml = placeholder._element

    for name, caption, desc in SCREENSHOT_SPECS:
        png_path = screenshots[name]

        img_para = doc.add_paragraph()
        img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = img_para.add_run()
        run.add_picture(str(png_path), width=Inches(6.0))

        cap_para = doc.add_paragraph()
        cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_run = cap_para.add_run(caption)
        cap_run.italic = True
        cap_run.font.size = Pt(10)

        desc_para = doc.add_paragraph(desc)
        desc_para.paragraph_format.space_after = Pt(12)

        # Move the three paragraphs from end-of-doc to right after the anchor,
        # chaining so the next iteration lands after the previous description.
        for xml_para in (img_para._element, cap_para._element, desc_para._element):
            anchor_xml.addnext(xml_para)
            anchor_xml = xml_para

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
