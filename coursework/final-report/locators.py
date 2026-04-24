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
# 7 paragraphs, within the spec's 6-10 target range.
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
