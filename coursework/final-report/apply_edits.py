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
