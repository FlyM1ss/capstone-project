"""Run the query edge-case test pack against the running backend; emit a markdown table.

Pass: every expected file in top 5. Partial: any expected in top 10, or stable response on
malformed/prompt-injection cases. Fail: nothing in top 10, or an HTTP error other than the
one Q-027 expects.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

BACKEND = "http://localhost:8000"
QUERIES_FILE = Path(__file__).parent / "queries.json"


async def search(client: httpx.AsyncClient, query: str, show_latest_only: bool = True) -> tuple[int, dict]:
    r = await client.post(
        f"{BACKEND}/api/search",
        json={"query": query, "top_k": 10, "show_latest_only": show_latest_only},
    )
    try:
        return r.status_code, r.json()
    except json.JSONDecodeError:
        return r.status_code, {"raw": r.text}


def _norm(s: str) -> str:
    # Match the backend's document_group canonicalization in
    # backend/app/services/ingestion.py:_extract_version_info so titles like
    # "Remote_Work_Policy_v2.docx" line up with Docling-derived "Remote Work Policy v2".
    return Path(s or "").stem.strip().lower().replace("_", " ").replace("-", " ")


def _matches(expected: str, titles: list[str]) -> bool:
    e = _norm(expected)
    return any(e in _norm(t) or _norm(t) in e for t in titles)


def _titles(payload: dict) -> list[str]:
    return [r.get("title") or r.get("filename", "") for r in payload.get("results", [])]


def grade(case: dict, status: int, payload: dict) -> tuple[str, str]:
    cat = case.get("category")
    if cat == "validation-reject":
        expected = case.get("expect_http", 400)
        if status == expected:
            return "Pass", f"Validation rejected with HTTP {status}"
        return "Fail", f"Expected HTTP {expected} got {status}; payload={json.dumps(payload)[:200]}"

    if status != 200:
        return "Fail", f"HTTP {status}: {json.dumps(payload)[:200]}"

    titles = _titles(payload)
    top5, top10 = titles[:5], titles[:10]

    if cat == "broad":
        return "Pass", f"top5={top5}"
    if cat in ("malformed-stable", "prompt-injection"):
        return "Partial", f"stable; top5={top5}"

    expects = case.get("expect", [])
    if not expects:
        return "Pass", f"top5={top5}"

    in_top5 = sum(1 for e in expects if _matches(e, top5))
    in_top10 = sum(1 for e in expects if _matches(e, top10))
    if in_top5 == len(expects):
        return "Pass", f"all expected in top5: {top5}"
    if in_top10 >= 1:
        return "Partial", f"{in_top10}/{len(expects)} in top10; top5={top5}"
    return "Fail", f"none of {expects} in top10; top5={top5}"


def _row(case_id: str, query: str, verdict: str, note: str) -> str:
    q = query.replace("|", "\\|")
    n = note.replace("|", "\\|").replace("\n", " ")
    return f"| {case_id} | {q} | {verdict} | {n} |"


async def _run_case(client: httpx.AsyncClient, c: dict) -> list[str]:
    status, payload = await search(client, c["query"])
    verdict, note = grade(c, status, payload)
    rows = [_row(c["id"], c["query"], verdict, note)]
    if c.get("also_run_no_filter"):
        _, payload2 = await search(client, c["query"], show_latest_only=False)
        rows.append(_row(f"{c['id']}b", f"{c['query']} (no version filter)", "n/a", f"top5={_titles(payload2)[:5]}"))
    return rows


async def _amain() -> int:
    cases = json.loads(QUERIES_FILE.read_text())
    async with httpx.AsyncClient(timeout=60.0) as client:
        results = await asyncio.gather(*(_run_case(client, c) for c in cases))
    rows = ["| Test ID | Query | Status | Notes |", "|---|---|---|---|"]
    for r in results:
        rows.extend(r)
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_amain()))
