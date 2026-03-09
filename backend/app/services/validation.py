import re

from fastapi import HTTPException


def validate_query(query: str) -> None:
    """Validate search query: length, content, injection patterns."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")

    # Block obvious prompt injection patterns
    injection_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"system\s*prompt",
        r"you\s+are\s+now",
        r"<\s*script",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="Query contains disallowed patterns")
