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
