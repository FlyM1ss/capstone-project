# Demo Search Queries

## 1. "What is the company's remote work policy?"

Simple natural language question. Shows **version-aware ranking** — Remote Work Policy has v1 and v2, so toggling "show latest only" visibly changes results.

## 2. "password requirements and multi-factor authentication"

Keyword-heavy query. Shows **hybrid search** — BM25 matches exact terms while semantic search finds related security documents across PDF, DOCX, and PPTX formats.

## 3. "How do I report unethical behavior?"

No keywords match any document title. Shows **semantic understanding** — surfaces the Whistleblower Policy and Code of Conduct through meaning, not exact words.

## 4. "Q3 2025 revenue and business performance"

Searches inside a **PowerPoint** presentation. Shows multi-format ingestion and **title boosting** since "Q3 2025 Business Review" is a strong title match.

## 5. "employee benefits and wellness programs"

Broad discovery query. Shows **reranking** — pulls from many documents (wellness, benefits, leave policies) and sorts them by relevance.
