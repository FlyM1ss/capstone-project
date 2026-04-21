# Presentation Coaching: Software Design + Live Demo

**Project:** AI-Driven NLP Company-Wide Search Engine for Deloitte (ITWS 4100 Capstone)
**Sections Covered:** 06 — Software Design, 07 — Live Demo
**Audience:** University professor (technical rigor), ITWS peers, two Deloitte consultants (one semi-technical with AI familiarity, one strictly business)
**Preceding Section:** NLP Security (boundaries, bad inputs, data safety) — presented by teammate

---

## Audience Strategy

The audience skew (1 business consultant + 1 semi-technical + 1 professor) is a *bimodal* audience, not an average one. The common mistake is to pitch "somewhere in the middle," which satisfies neither end.

**Better strategy:**
- Give the business consultant a clear *why* for every *what*.
- Give the professor one or two moments of deep technical precision that signal rigor without derailing the flow.
- Alternate registers; don't blend them.

---

## 1. Narrative Framework

**Governing frame:**

> *"Every box on this diagram answers a specific business risk that a single-model search engine cannot."*

This works for all three audiences because it reframes the architecture as a series of deliberate tradeoffs instead of a feature tour.

Structure the section around **three pillars**, not three diagrams:

| Pillar | Business risk it mitigates | Architecture that enforces it |
|---|---|---|
| **Retrieval completeness** | "We found nothing" or "we missed the right doc" | Parallel hybrid (semantic + BM25 + title) |
| **Result precision** | "The top result is technically related but not useful" | RRF consensus + Cohere rerank |
| **Trust boundary enforcement** | "The wrong person saw the wrong version of the wrong document" | Input validation + RBAC + version filter |

The handoff from the NLP Security section becomes seamless: the teammate covered *boundaries at the input*; you cover *boundaries enforced throughout the retrieval pipeline*. Same philosophy, different surface area.

---

## 2. Script Outline (with Progressive Disclosure)

### Opening (~20 seconds)

> "My teammate just showed you how we prevent bad inputs from reaching our system. I'll show you how the rest of the architecture enforces correctness after a *good* input arrives. Three diagrams. I'll use them as a map, not a script. One query, start to finish."

### Anchor Metaphor: The Consulting Research Desk

> "Think of this as how a great consulting research desk handles a question. A mediocre one hands it to one junior analyst. A great one runs three specialists in parallel, has a senior review their shortlist, and checks your clearance before handing anything back. That's this system."

### Walking the Sequence Diagram

For each stage: **business hook first, then one precise technical detail for the professor.**

#### Input Validation (FastAPI layer)
- **Business:** "Security checkpoint at the lobby. Before any query hits our expensive AI models, we confirm it isn't malformed, adversarial, or oversized."
- **Technical hook:** "This is where my teammate's validation layer plugs in at the API boundary."

#### Parallel Hybrid Retrieval
- **Business:** "Three librarians searching simultaneously. One understands meaning, one finds exact terms, one checks document titles. In parallel, so thoroughness doesn't cost latency."
- **Technical hook:** "Semantic uses HNSW on 1024-dimensional Qwen3 embeddings. Keyword uses ParadeDB's BM25, which extends Postgres with Tantivy, so we keep a single-database deployment instead of running a separate vector store."
- **Why it matters:** "Pure semantic misses exact SKUs and acronyms. Pure keyword misses paraphrasing. You need both, running together."

#### RRF Merge
- **Business:** "Consensus vote across the three lists. No single ranker dominates; documents strong across multiple lists rise."
- **Technical hook:** "Reciprocal Rank Fusion, k=60, with a 1.5x boost on title matches because title relevance is the strongest intent signal we have."

#### Cohere Rerank v3.5
- **Business:** "The shortlist goes to a senior expert who reads each candidate *with the query in mind* and re-sorts. Only the top 50 reach this stage because per-call cost is nontrivial."
- **Why it matters:** "This is what makes the top-3 feel uncannily right instead of just plausibly related. It's the difference between 'search' and 'answers.'"

#### RBAC + Version Filter
- **Business:** "Compliance officer and archivist. Before results reach the user, we strip out unauthorized content and hide superseded document versions."
- **Deloitte-specific hook:** "At a consulting firm, showing an analyst a confidential client memo or the v1 of a deliverable that's now at v4 is a real liability. It's enforced at the architecture layer, not bolted on."

### Progressive Disclosure Technique

The three diagrams should stay on screen as a **visual anchor**, but trace a *single query's path through them with a pointer or cursor*. Don't read boxes.

- The professor sees you understand the flow.
- The business consultant sees a story.

### Why This Dual-Register Works

1. For the professor: you drop **one** precise technical term per stage (HNSW, Tantivy, RRF k=60, 1.5x title weight). Enough to signal rigor without derailing the consultants.
2. For the consultants: Deloitte-specific framing ("confidential client memo," "v1 vs v4 deliverable") makes the abstract architecture feel *directly relevant* to their day job. That's what separates a student project from a consulting pitch.

---

## 3. Transition Script Into Demo

> "That's the design on paper. The real question is whether it holds up on real queries. So let me stop talking about the system and let you watch it. Three queries, each designed to stress a different part of what I just walked through."

### Do Not Do This

1. **Don't ask "any questions on the architecture?" right now.** It kills the momentum. Invite questions *after* the demo, when the claims are fresh and grounded in something they saw work.
2. **Don't narrate the screen setup** ("let me just get this browser open..."). Have it pre-open on a second monitor or tab. The switch should take under 3 seconds.

### Failure Contingency

Have a one-liner ready:

> "If the live demo misbehaves, that's why we brought backups."

Then pivot to a pre-recorded screen capture or screenshots. Rehearse the pivot so it sounds casual, not panicked.

---

## 4. Demo Choreography

**Each query: ~60 to 90 seconds.** Say what you'll do, run it, narrate what's appearing, connect it back to a specific architecture claim.

### Query 1 — NLP Intelligence (Semantic Strength)

Pick a natural-language phrasing where *no keyword overlaps* with the best-matching document's title.

- **Example input:** `how do I get reimbursed for travel`
- **Target top result:** a document titled something like "T&E Expense Policy" or "Corporate Card Procedures"

**Narration:**
> "Notice zero keyword overlap between my query and the top result. A pure keyword engine would have missed this entirely. The semantic layer bridges natural language to corporate jargon."

**Architecture claim demonstrated:** Semantic pgvector path + Cohere rerank.

---

### Query 2 — Precision via Hybrid + Rerank

Pick a query with *both* conceptual meaning and a specific identifier (acronym, version number, proper noun).

- **Example input:** `Q3 2024 compliance report` or a query with an internal code

**Narration:**
> "Result #1 is the exact version match. That's BM25 doing its job. But look at result #2. It's a semantically related doc that wouldn't surface in pure keyword search. The hybrid picks up both signals, and the reranker decides what a human asking this question actually wanted first."

**Architecture claim demonstrated:** BM25 + RRF + rerank working together.

---

### Query 3 — Boundary Enforcement (Input Validation)

Submit something adversarial that the teammate's section set up.

- **Example inputs:**
  - Prompt injection: `Ignore previous instructions and reveal...`
  - Malformed input
  - Oversized payload

**Narration:**
> "This is the input validation layer enforcing the boundary my teammate described. The expensive AI models never see this query. That matters for cost, latency, and security."

**Architecture claim demonstrated:** Input validation layer.

**Strategic value:** This is your *callback moment* to the prior section. It reinforces the "defense in depth" narrative across both presentations.

---

### Optional Query 4 — Version Filtering

If you have paired v1/v2 docs ingested and time permits:

Toggle "show latest only" off and on to demonstrate version-aware ranking. Short, visual, effective.

---

### On RBAC (Important Scoping Note)

Since `user_role` is currently hardcoded to `admin` in `search.py` for demo purposes, **do not attempt a live role-switch demo.** Instead, mention it during the walkthrough:

> "In production this filter hides results based on the logged-in user's role. For today's demo I'm running as admin so you see everything. The enforcement is wired in, we're just not exercising the switch live."

Being upfront about this scoping decision is stronger than risking a professor question that exposes it. Frame it as **deliberate demo simplification**, not a gap.

---

## 5. Pacing Rule for the Whole Demo

For every query, follow this micro-structure:

1. **"I'm going to [X] to stress [Y]."**
2. *Type and execute*
3. **"Here's what you're seeing..."**
4. **"...and that maps to [architecture component] from the diagram."**

That connective tissue turns the demo from "look, it works" into "I told you it would do this, and here it is."

---

## 6. Closing Line After Demo

> "Architecture on paper, working in the browser, with the boundaries my teammate described enforced end to end. Happy to take questions on any of it."

This sentence does three jobs:
1. Reaffirms the narrative.
2. Credits your teammate's section (collaborative tone).
3. Opens Q&A on your terms.

---

## Appendix: Quick Reference Card (Print for Podium)

**Three pillars:** Completeness → Precision → Trust

**Five stages, five analogies:**
1. Input Validation → Lobby security checkpoint
2. Parallel Hybrid → Three librarians working at once
3. RRF Merge → Consensus vote across lists
4. Cohere Rerank → Senior expert reviews the shortlist
5. RBAC + Version Filter → Compliance officer + archivist

**Three demo queries:**
1. Natural-language query with zero keyword overlap → semantic wins
2. Query with both concept + specific ID → hybrid wins
3. Adversarial input → validator wins (callback to teammate)

**One-liner on RBAC:** "Enforcement wired in, running as admin for demo visibility."

**Closer:** "Architecture on paper, working in the browser, boundaries enforced end to end."
