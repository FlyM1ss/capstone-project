# tests/final_report/test_patch_2_jargon.py
"""Patch 2: seven targeted rewrites across §8.2 – §8.7."""
from pathlib import Path

from docx import Document

from apply_edits import patch_2_simplify_jargon, verify_2


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
