# tests/final_report/test_patch_5_financial.py
"""Patch 5: guardrail -- no stale figures, §1 and §9.3 IRR agree."""
from pathlib import Path

from docx import Document

from apply_edits import patch_5_financial_consistency, verify_5
import locators as L


def test_patch_5_passes_on_clean_doc(fresh_docx_copy: Path):
    """Happy path: unmodified source DOCX should pass (no-op)."""
    patch_5_financial_consistency(fresh_docx_copy)
    assert verify_5(fresh_docx_copy) is True


def test_patch_5_halts_on_injected_stale_figure(fresh_docx_copy: Path):
    """Inject a stale figure and confirm patch 5 halts with RuntimeError."""
    doc = Document(fresh_docx_copy)
    # Add a paragraph near §13 that contains a stale NPV figure
    doc.paragraphs[L.PARA_SECTION_13_HEADING + 1].text += " NPV is $51.5M."
    doc.save(fresh_docx_copy)

    try:
        patch_5_financial_consistency(fresh_docx_copy)
    except RuntimeError as e:
        assert "51.5M" in str(e)
        return
    raise AssertionError("Patch 5 should have raised on stale $51.5M")
