# tests/final_report/conftest.py
"""Pytest fixtures for final-report patch tests."""
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
FINAL_REPORT_DIR = REPO_ROOT / "coursework" / "final-report"
SOURCE_DOCX = FINAL_REPORT_DIR / "Final Report Draft.docx"

# Expose coursework/final-report/ on sys.path so tests can do bare imports
# like `from apply_edits import patch_1_8_10_screenshots`. The directory uses
# a hyphen (non-importable as a dotted module), so this is cleaner than
# renaming the directory or using importlib.util in every test.
if str(FINAL_REPORT_DIR) not in sys.path:
    sys.path.insert(0, str(FINAL_REPORT_DIR))


@pytest.fixture
def fresh_docx_copy(tmp_path: Path) -> Path:
    """Copy the source DOCX to a tmp location so tests can mutate freely."""
    target = tmp_path / "report.docx"
    shutil.copy2(SOURCE_DOCX, target)
    return target
