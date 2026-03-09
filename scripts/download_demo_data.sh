#!/bin/bash
# Downloads publicly available PDFs for demo purposes
# These simulate the types of documents Deloitte employees search for

OUT="data/sample-docs"
mkdir -p "$OUT"

echo "Downloading demo documents..."

# Public consulting/business reports (short + long, with tables/charts)
# Add URLs to publicly available PDFs here as the team curates them
# Example:
# curl -sL "https://example.com/report.pdf" -o "$OUT/annual-report-2024.pdf"

echo "Place PDF files in $OUT/ directory"
echo "Then run: docker compose exec backend python -m app.scripts.ingest_all"
