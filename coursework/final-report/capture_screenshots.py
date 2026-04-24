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
    ("/",                            "landing.png"),
    ("/search?q=remote+work+policy", "search-results.png"),
    ("/admin/upload",                "admin-upload.png"),
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
