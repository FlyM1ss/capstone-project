# tests/final_report/test_patch_1_screenshots.py
"""Patch 1: §8.10 placeholder replaced with 3 screenshots + captions."""
from pathlib import Path

import pytest
from docx import Document

from apply_edits import patch_1_8_10_screenshots, verify_1


@pytest.fixture
def fake_screenshots(tmp_path: Path) -> dict[str, Path]:
    """Create 3 tiny PNG stubs so patch_1 can embed them."""
    # Minimal valid 1x1 RGB PNG
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
        "0000000c49444154789c63f8ffff3f0005fe02fe0def46b80000000049454e44ae426082"
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

    body_text = "\n".join(p.text for p in doc.paragraphs)
    assert "will be included in the final version" not in body_text

    assert len(doc.inline_shapes) == 14  # 11 existing + 3 new

    assert verify_1(fresh_docx_copy) is True
