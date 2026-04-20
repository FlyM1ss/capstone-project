from pathlib import Path

import httpx

CONVERTED_DIR = "/data/converted"


async def get_pdf_bytes(doc_id: str, file_path: str, doc_type: str, gotenberg_url: str) -> bytes:
    if doc_type == "pdf":
        return Path(file_path).read_bytes()

    cached = Path(CONVERTED_DIR) / f"{doc_id}.pdf"
    if cached.exists():
        return cached.read_bytes()

    pdf_bytes = await _convert_via_gotenberg(file_path, gotenberg_url)

    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(pdf_bytes)
    return pdf_bytes


async def _convert_via_gotenberg(file_path: str, gotenberg_url: str) -> bytes:
    path = Path(file_path)
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(path, "rb") as f:
            response = await client.post(
                f"{gotenberg_url}/forms/libreoffice/convert",
                files={"files": (path.name, f, "application/octet-stream")},
            )
        response.raise_for_status()
        return response.content


def invalidate_cache(doc_id: str) -> None:
    cached = Path(CONVERTED_DIR) / f"{doc_id}.pdf"
    cached.unlink(missing_ok=True)
