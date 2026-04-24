# Final Report Outline

## AI-Driven Company-Wide Search Engine for Deloitte Resources

**Group Two — ITWS 4100 IT Capstone — Spring 2026**
Raven Levitt (PM) | Sophia Turnbow (User Research) | Matthew Voynovich (Security) | Jesse Gabriel (Developer) | Andrew Jung (Market Research) | Felix Tian (System Architect)

---

## Report Structure

Target: 30+ pages (main body ~15-18 pages of prose, remainder from diagrams, tables, charts, screenshots, and appendices).

---

## PART I: INTRODUCTION & CONTEXT (~3 pages)

### 1. Executive Summary (~1 page)
- One-paragraph problem statement (information overload at enterprise scale)
- One-paragraph solution summary (AI-powered hybrid search engine)
- Key results: working prototype, financial metrics (ROI, NPV, payback)
- One-paragraph strategic conclusion

### 2. Problem Statement (~1 page)
- Knowledge worker productivity statistics (1.8-2.5 hrs/day lost searching)
- Information silo prevalence (83% of companies, only 27% have proper search)
- Quantified cost at Deloitte scale: 470K employees x lost time = $10.6B/year
- Why keyword search fails (can't guess exact terms, no semantic understanding)

**Source material:** Midterm presentation slides 3-4, Deloitte Knowledge Management Research

### 3. Client Profile: Deloitte (~1 page)
- Scale: $70.5B revenue, 470K employees, 700+ offices, 150+ countries
- Four service lines and knowledge-intensive nature of work
- Deloitte's AI commitment (PairD launch, 36% digital budget on AI)
- Why Deloitte specifically benefits from this solution

**Source material:** Midterm presentation slides, Deloitte_Knowledge_Management_Research.md

---

## PART II: STRATEGIC ANALYSIS (~5-6 pages)

### 4. Industry & Market Analysis (~1.5 pages)
- Enterprise search market size: $7.47B (2026), projected $11.66B (2031), 9.31% CAGR
- Market drivers: AI adoption, remote work, regulatory compliance
- Segmentation: by deployment model, organization size, industry vertical

**Source material:** Mini_Strategic_Plan.md (external environment section)

### 5. Competitive Landscape (~1.5 pages)
- Porter's Five Forces analysis (table + narrative)
  - Threat of new entrants: High (open-source lowers barriers)
  - Supplier power: Low-Moderate (commoditized cloud + open models)
  - Buyer power: High (enterprises can build in-house)
  - Substitutes: Moderate (Slack AI, Copilot are "good enough" for simple cases)
  - Rivalry: High (Glean $7.2B, Elastic, Coveo)
- Competitor comparison table: Glean, Microsoft Search, Elastic, Coveo, Algolia
- Positioning map / differentiation analysis

**Source material:** Mini_Strategic_Plan.md (competitive analysis section)

### 6. Strategic Positioning (~1.5 pages)
- VRIN framework analysis (table: 5 resources evaluated on V/R/I/N)
- Key insight: sustainable advantage is in the data, not the technology
- Business strategy: focused differentiation (narrow scope, domain-tuned relevance, data sovereignty)
- Build vs. Buy rationale: $0/user vs. $20+/user (Glean) = $112M+/year savings at scale

**Source material:** Mini_Strategic_Plan.md (internal environment + VRIN sections)

### 7. Risk Assessment (~0.5 page)
- Technical risks: model hosting, latency at scale, document format edge cases
- Business risks: vendor lock-in (mitigated by open-source), data governance, adoption
- Mitigation strategies for each

**Source material:** Mini_Strategic_Plan.md (risk section), DESIGN_DECISIONS.md

---

## PART III: SYSTEM DESIGN & ARCHITECTURE (~6-7 pages)

### 8. System Overview & Requirements (~1 page)
- Functional requirements: natural language search, multi-format ingestion, RBAC, versioning
- Non-functional requirements: sub-2-second response, horizontal scalability, graceful degradation
- Use cases summary (5 core use cases)
- System context diagram

**Source material:** Technical_Architecture_Report.md (sections 1-2), past system requirements assignment

### 9. Technical Architecture (~2 pages)
- Four-layer architecture: Frontend → API → Processing → Data
- **Component diagram** (existing PNG)
- Technology stack table with rationale for each choice
- Design philosophy: open-source first, unified database, graceful degradation

**Visual assets:** component.png or modern-component-diagram.png, tech stack comparison table

**Source material:** Technical_Architecture_Report.md (section 3), DESIGN_DECISIONS.md

### 10. Search Pipeline Design (~2 pages)
- End-to-end query flow (validate → embed → parallel retrieval → RRF → rerank → filter)
- **Sequence diagram** (existing PNG)
- Hybrid search rationale: why neither keyword nor semantic search alone is sufficient
- Reciprocal Rank Fusion explanation with title boost weight (1.5x)
- Cohere Rerank v3.5 as final relevance arbiter
- Tuning parameters: SEARCH_TOP_K=50, RERANK_TOP_N=10, RRF_K=60

**Visual assets:** sequence.png or modern_sequence_diagram.png

**Source material:** Technical_Architecture_Report.md (search pipeline section), DESIGN_DECISIONS.md (search-related decisions)

### 11. Document Ingestion Pipeline (~1 page)
- Upload → Docling parse → version detection → chunking → embedding → storage
- **Activity diagram** (existing PNG)
- Chunking strategy: 512 tokens, 50-token overlap
- Content-hash deduplication
- Multi-format support: PDF, DOCX, PPTX

**Visual assets:** activity.png or modern-activity-diagram.png

**Source material:** Technical_Architecture_Report.md (ingestion section), DESIGN_DECISIONS.md

### 12. Key Design Decisions (~1 page)
- Top 4-5 architectural decisions with tradeoff analysis:
  1. Unified PostgreSQL (pgvector + ParadeDB) vs. separate vector DB
  2. Qwen3-Embedding-0.6B vs. OpenAI/Cohere embeddings
  3. Docling vs. alternative parsers (PyMuPDF, Unstructured)
  4. External embedding server vs. in-process model loading
  5. RRF vs. linear combination for result fusion
- Each with: decision, alternatives considered, tradeoffs, rationale

**Source material:** DESIGN_DECISIONS.md (this is the primary source)

---

## PART IV: IMPLEMENTATION (~4-5 pages)

### 13. Database Design (~1.5 pages)
- Schema diagram (5 tables: documents, document_chunks, document_title_embeddings, users, query_logs)
- Entity relationships, cascading deletes, version grouping
- Index strategy: HNSW for vector search, BM25 index for keyword search
- Vector storage: 1024-dimensional embeddings directly in PostgreSQL

**Visual assets:** Database schema diagram (create from init.sql), table structure summary

**Source material:** backend/db/init.sql, Technical_Architecture_Report.md (database section)

### 14. Security Architecture (~1 page)
- Three-tier RBAC: Analyst (public) → Manager (+ internal) → Admin (+ confidential, + upload)
- JWT authentication flow: bcrypt hashing → HS256 tokens → 60-min expiry
- Query-time access filtering (confidential docs never appear for unauthorized roles)
- Input validation: query length, content safety, injection prevention
- Audit trail: all queries logged with user, timestamp, results, latency
- Compliance alignment: GDPR, SOC 2

**Source material:** Technical_Architecture_Report.md (security section), midterm presentation

### 15. Frontend & User Experience (~1 page)
- Three-page application: Landing → Search Results → Admin Upload
- UI design decisions: shadcn/ui + Tailwind CSS 4 + Geist font
- Search experience: natural language input, relevance scores, metadata display, filters
- Admin portal: drag-and-drop upload, document management
- **Screenshots** of each page (landing, search results, admin upload)

**Visual assets:** 3-4 application screenshots (to be captured)

**Source material:** frontend/ code, README.md

### 16. Deployment Architecture (~0.5 page)
- Docker Compose: 3 containers (frontend, backend, db)
- **Deployment diagram** (existing PNG)
- Environment configuration, volume management, health checks
- One-command startup: `docker compose up -d`

**Visual assets:** deployment.png

**Source material:** docker-compose.yml, Technical_Architecture_Report.md (deployment section)

---

## PART V: RESULTS & EVALUATION (~3-4 pages)

### 17. Demonstration & Testing (~1.5 pages)
- 5 demo queries showing different system capabilities:
  1. "What is the company's remote work policy?" → version-aware ranking
  2. "password requirements and multi-factor authentication" → hybrid search
  3. "How do I report unethical behavior?" → semantic understanding (no keyword match)
  4. "Q3 2025 revenue and business performance" → PPTX ingestion + title boosting
  5. "employee benefits and wellness programs" → broad discovery + reranking
- For each: query, expected behavior, actual results, what it demonstrates
- **Screenshots of search results** for key queries

**Visual assets:** Search result screenshots for each demo query

**Source material:** docs/demo-queries.md, live system screenshots

### 18. Adversarial Robustness (~0.5 page)
- 24 poisoned documents with title/content mismatches in data/poisoned/
- How title boosting + hybrid search handles adversarial inputs
- Results: does the system surface correct content despite misleading titles?

**Source material:** data/poisoned/ directory, ingestion scripts (--poisoned flag)

### 19. Performance Metrics (~0.5 page)
- Query latency: sub-2-second end-to-end (target)
- Ingestion throughput: documents per minute
- Dataset statistics: 80+ auxiliary documents, multiple formats
- Relevance improvement from reranking (+33-40% per Cohere benchmarks)

### 20. Data Corpus (~0.5 page)
- 80+ curated documents simulating Deloitte's internal knowledge base
- Categories: HR policies, IT/security, compliance, finance, organizational, business
- Formats: PDF, DOCX, PPTX
- 30+ adversarial documents for robustness testing
- Document versioning: multiple versions of key policies (e.g., Remote Work Policy v1, v2)

---

## PART VI: FINANCIAL ANALYSIS (~2-3 pages)

### 21. Cost-Benefit Analysis (~2-3 pages)
- Cost breakdown: development, infrastructure, maintenance
- Benefit quantification: productivity recovery, avoided licensing fees
- Financial summary table:
  - ROI: ~5,936%
  - NPV: ~$51.5M (3-year horizon)
  - IRR: ~37.2%
  - Payback period: <1 year
  - Annual productivity recovery: $1.06B (10% search improvement)
- Build vs. Buy comparison: in-house ($0 licensing) vs. Glean ($112M+/year)
- Sensitivity analysis: what if adoption is 5% instead of 10%?
- Charts: NPV over time, cost comparison bar chart

**Visual assets:** Financial charts from CBA spreadsheet, comparison tables

**Source material:** coursework/cost-benefit-analysis/ (CBA_Narrative_v2.docx, CBA_Deloitte_v2.xlsx)

---

## PART VII: PROJECT MANAGEMENT & REFLECTION (~2-3 pages)

### 22. Project Deliverables & Timeline (~1 page)
- Deliverables table with status:
  - D1: Use Cases & Requirements — Complete
  - D2: Research Reports (Foundational Knowledge, NLP Security, Market Research) — Complete
  - D3: Technical Design (Architecture report, 5 UML diagrams) — Complete
  - D4: Working Prototype — Functional
  - Mini Strategic Plan — Complete
  - Cost-Benefit Analysis — Complete
- Development timeline / Gantt chart
- Milestones and how schedule was managed

### 23. Team Organization (~0.5 page)
- Role assignments and responsibilities
- Collaboration tools and workflow
- Meeting cadence and decision-making process

### 24. Challenges & Lessons Learned (~1 page)
- Technical challenges:
  - Embedding model deployment (GPU access → Colab + ngrok solution)
  - Unified database architecture (pgvector + ParadeDB in single PostgreSQL)
  - Hybrid search tuning (RRF weight balancing)
  - Document parsing complexity (diverse formats with tables/images)
- Team challenges:
  - Coordinating 6 schedules
  - Balancing research deliverables with development
  - Learning new technologies (NLP, vector databases, FastAPI)
- Key lessons and what we'd do differently

**Source material:** Midterm presentation (challenges section), team experience

---

## PART VIII: CONCLUSION (~1 page)

### 25. Future Work (~0.5 page)
- Short-term: auth integration, UI polish, search quality tuning, expanded dataset
- Medium-term: query suggestions, semantic caching, document preview, analytics dashboard
- Long-term: LLM-generated answers (RAG), multi-language support, federated search across platforms

### 26. Conclusion (~0.5 page)
- Restate the problem and its scale
- What was built and its key differentiators
- Strategic value: open-source, data sovereignty, $0/user licensing
- Final statement on impact potential

---

## APPENDICES (~10-15 pages of supporting material)

### Appendix A: Team Member Resumes
- One-page resume per team member (6 pages)

### Appendix B: System Requirements Specification
- Detailed functional and non-functional requirements
- Use case specifications (actors, preconditions, flows, postconditions)

**Source material:** Past system requirements assignment

### Appendix C: Database Schema & SQL
- Full init.sql with CREATE TABLE statements
- Index definitions (HNSW, BM25)
- Sample queries

**Source material:** backend/db/init.sql

### Appendix D: API Specification
- REST API endpoints table (health, auth, search, documents)
- Request/response schemas
- Authentication flow

**Source material:** backend/app/api/ routers, models/schemas.py

### Appendix E: Software Engineering Diagrams
- All 5 UML diagrams at full size:
  - Component diagram
  - Sequence diagram
  - Activity diagram
  - Deployment diagram
  - Use case diagram

**Source material:** software-engineering/diagrams/*.png

### Appendix F: HCI / User Interface
- Wireframes or screenshots of all pages
- UI design rationale
- Usability considerations

**Source material:** Past HCI assignment, frontend screenshots

### Appendix G: Cost-Benefit Analysis Detail
- Full financial model from CBA_Deloitte_v2.xlsx
- Assumptions and methodology
- Sensitivity analysis tables

**Source material:** coursework/cost-benefit-analysis/

### Appendix H: Networking & Deployment
- Docker Compose configuration
- Network topology between containers
- Environment variable reference

**Source material:** docker-compose.yml, .env.example

### Appendix I: Test Plan & Results
- Demo query test cases and results
- Adversarial robustness test results
- Performance benchmarks

### Appendix J: Project Plan
- Development timeline / Gantt chart
- Sprint/phase breakdown
- Git commit history summary

---

## PAGE COUNT ESTIMATE

| Section | Pages (est.) | Heavy on... |
|---------|-------------|-------------|
| Part I: Introduction & Context | 3 | Prose, statistics |
| Part II: Strategic Analysis | 5-6 | Tables, frameworks, charts |
| Part III: System Design | 6-7 | **Diagrams**, architecture visuals |
| Part IV: Implementation | 4-5 | **Screenshots**, schema diagrams, tables |
| Part V: Results & Evaluation | 3-4 | **Screenshots** of search results |
| Part VI: Financial Analysis | 2-3 | **Charts**, financial tables |
| Part VII: Project Management | 2-3 | Timeline charts, tables |
| Part VIII: Conclusion | 1 | Prose |
| **Main Body Total** | **~26-32** | |
| Appendices (A-J) | 10-15 | Diagrams, code, tables |
| **Grand Total** | **~36-47** | |

---

## EXISTING ASSETS TO INTEGRATE

| Asset | Location | Maps to Section(s) |
|-------|----------|-------------------|
| Technical_Architecture_Report.md (73KB) | coursework/software-engineering/ | 8, 9, 10, 11, 14, 16 |
| DESIGN_DECISIONS.md (50KB) | root | 12 |
| Foundational_Knowledge_Report.md (60KB) | coursework/research/ | Background context for 8, 10 |
| Research_KM_Deloitte.md (27KB) | coursework/research/ | 2, 3 |
| Mini_Strategic_Plan.md (30KB) | coursework/strategic-plan/ | 4, 5, 6, 7 |
| CBA_Narrative_v2.docx + spreadsheets | coursework/cost-benefit-analysis/ | 21 |
| demo-queries.md | docs/ | 17 |
| Midterm presentation | _missing — recover or omit cross-references_ | Cross-reference all |
| 8 rendered diagrams (PNG) | coursework/software-engineering/diagrams/ | 9, 10, 11, 16, Appendix E |
| 5 Mermaid source files (.mmd) | coursework/software-engineering/diagrams/ | Appendix E |
| Proposal_Deloitte_V4.pdf | coursework/proposals/ | 2, 3 |
| init.sql | backend/db/ | 13, Appendix C |
| Past assignments | coursework/past-examples/ | Appendices B, F, H |
| Draft_v1.pdf (prior draft) | coursework/final-report/ | Baseline to revise for final draft |

---

## WRITING APPROACH

1. **Don't rewrite from scratch** — adapt and synthesize existing documents
2. **Consistent voice** — unify the tone across sections written at different times
3. **Visual-heavy** — every section should have at least one diagram, table, chart, or screenshot
4. **Reference the working prototype** — this is the strongest differentiator (only working prototype among capstone teams)
5. **Strategic framing** — the professor uses a strategic management textbook; frame technical decisions in business terms
6. **Cite sources** — the syllabus has strict academic integrity requirements; cite all statistics, frameworks, and external references
