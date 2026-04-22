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

## 2. Slide-by-Slide Script

Four slides for Section 06, then straight into the demo. Total target: ~4–5 minutes.

| # | Slide | Purpose | ~Time |
|---|-------|---------|-------|
| 1 | "Magic" (real sequence diagram with cover box) | Disarming hook, set expectations | 25 sec |
| 2 | Hero diagram | The whole section's argument | 2:30 |
| 3 | Real sequence diagram (uncovered) | Rigor proof for the professor | 50 sec |
| 4 | Component diagram | Deployment footprint, glance | 25 sec |
| → | Transition into demo | Hand off | 15 sec |

---

### Slide 1 — The "Magic" Slide (~25 sec)

Your teammate has just finished. You take the mic. Slide 1 appears: the full sequence diagram with a giant "MAGIC" box covering most of the components.

**Narration:**
> "My teammate just showed you how we prevent bad inputs from reaching our system. I'll show you how the rest of the architecture enforces correctness *after* a good input arrives. This is what our backend actually looks like [gesture at slide]. If I tried to walk you through every arrow we'd be here until Friday, so for the next few minutes I'm replacing the 'magic' in the middle with a diagram you can actually reason about, and then we go straight to a live demo."

**What this slide does:**
- Disarms the audience. Everyone knows AI systems look overwhelming; acknowledging it first earns trust.
- For the professor: signals you understand the real complexity and chose to abstract *deliberately*, as a communication choice.
- For the consultants: a friendly wink that says "you're not expected to decode this, that's the point."
- Sets up the hero diagram as the *answer*, not a shortcut.

**Do not:**
- Apologize ("sorry this is complicated"). The joke is confident, not defensive.
- Explain any box on slide 1. They're not for reading, they're for scale.
- Linger. One breath after your last word, advance.

---

### Slide 2 — The Hero Diagram (~2:30, the bulk of the section)

This is the heart of Section 06. Every sentence earns its place because it ties a visible box to a business risk.

**Anchor metaphor (deliver once, then walk the diagram):**

> "Think of this as how a great consulting research desk handles a question. A mediocre one hands it to one junior analyst. A great one runs three specialists in parallel, has a senior review their shortlist, and checks your clearance before handing anything back. That's this system. Five stages, color-coded by pillar, left to right."

Then trace the flow left-to-right. For each stage: **business hook first, one precise technical detail for the professor.**

#### Lobby Checkpoint (Input Validator)
- **Business:** "Security checkpoint at the lobby. Before any query hits our expensive AI models, we confirm it isn't malformed, adversarial, or oversized."
- **Technical hook:** "This is where my teammate's validation layer plugs in at the API boundary. On the diagram it's the amber box, the one gate between the outside world and anything that costs us money or data."

#### Parallel Hybrid Retrieval (Three Specialists)
- **Business:** "Three specialists working simultaneously. The diagram labels them *Meaning*, *Exact-Match*, and *Intent*. Meaning handles paraphrasing, Exact-Match catches literal strings and IDs, Intent weighs the document title. In parallel, so thoroughness doesn't cost latency."
- **Technical hook:** "Meaning uses HNSW on 1024-dimensional Qwen3 embeddings. Exact-Match uses ParadeDB's BM25, which extends Postgres with Tantivy, so we keep a single-database deployment instead of running a separate vector store. Intent reuses the embedding index on a dedicated title-embeddings table."
- **Why it matters:** "Pure semantic misses exact SKUs and acronyms. Pure keyword misses paraphrasing. Pure title ignores the body. You need all three running together, which is what the blue layer on the diagram shows."

#### Consensus Vote (RRF Merge)
- **Business:** "Consensus vote across the three specialists. No single ranker dominates; documents strong across multiple lists rise."
- **Technical hook:** "Reciprocal Rank Fusion, k=60, with a 1.5x boost on title matches because title relevance is the strongest intent signal we have. Those parameters are deliberately *not* on the hero diagram. Say them aloud for the professor, skip them for the consultants."

#### Senior Expert Review (Cohere Rerank v3.5)
- **Business:** "The shortlist goes to a senior expert who reads each candidate *with the query in mind* and re-sorts. Only the top 50 reach this stage because per-call cost is nontrivial."
- **Why it matters:** "This is what makes the top-3 feel uncannily right instead of just plausibly related. It's the difference between 'search' and 'answers.' On the diagram it's the green box. The entire precision pillar lives in that one stage."

#### Compliance Filter (RBAC + Version)
- **Business:** "Compliance officer and archivist in one step. Before results reach the user, we strip out unauthorized content and hide superseded document versions. The diagram collapses them into one red box because they're enforced together, but verbally I call out both jobs so each enforcement point is vivid."
- **Deloitte-specific hook:** "At a consulting firm, showing an analyst a confidential client memo or the v1 of a deliverable that's now at v4 is a real liability. It's enforced at the architecture layer, not bolted on."

**Delivery technique while on this slide:**

The hero diagram stays on screen the whole time as a visual anchor. Trace a single query's path through it left-to-right with a pointer or cursor. Don't read boxes.
- The professor sees you understand the flow.
- The business consultant sees a story.
- The colors do the middle work: amber (gate) → blue (gather) → green (refine) → red (enforce) → dark (deliver). If anyone asks about the color scheme, each color is exactly one of the three pillars plus the endpoints.

---

### Slide 3 — Real Sequence Diagram, Uncovered (~50 sec)

The "magic" box from slide 1 with the cover removed. This is your rigor moment for the professor.

**Narration:**
> "Here's the magic box, with the cover off. Same five stages I just walked, now with the database calls, the embedding service hop, the rerank API, and the error paths. I won't read this. The point is that every analogy I just used maps to a concrete call. No hand-waving. If anyone wants to dig into where RBAC actually enforces, or where the parallel calls fan out, we can go deeper after the demo."

**What this slide does:**
- Satisfies the professor: *you actually know the implementation; the hero diagram was a communication choice, not a knowledge gap.*
- Gives the semi-technical consultant a credibility anchor if their AI familiarity is kicking in.
- Pays off the "magic" joke from slide 1. Callbacks always land.
- Earns the right to move past it.

**Do not:**
- Re-narrate stages. You just spent two minutes on them.
- Invite questions here. Forward momentum matters; questions after the demo land better.
- Apologize for the density. It's *supposed* to look dense, that's why slide 1 exists.

---

### Slide 4 — Component Diagram (~25 sec, glance)

**Narration:**
> "Last technical slide before I show it working. This is the deployment, four Docker services: database, embedding model, backend, and frontend. One Postgres instance handles both vector and keyword search, which is how we keep the operational footprint small. Cohere rerank and the embedding model are the two external dependencies. Everything else runs locally. That's the whole thing."

**What this slide does:**
- Signals deployment maturity without drifting into DevOps.
- Quietly answers the "is this a toy or a product" question.
- Earns the right to say "let me show you."

**Do not:**
- Explain Docker, pgvector, or ParadeDB from scratch. If slide 2 landed, those terms are already familiar.
- Stay longer than 30 seconds.

---

### Why This Four-Slide Sequence Works

1. **Slide 1 buys permission to simplify.** By showing the real thing first, you preempt the "is this oversimplified?" suspicion before it forms.
2. **Slide 2 delivers the argument.** The professor gets one precise technical term per stage (HNSW, Tantivy, RRF k=60, 1.5x title). The consultants get Deloitte-specific framing ("confidential client memo," "v1 vs v4 deliverable") that makes abstract architecture feel directly relevant to their day job.
3. **Slide 3 cashes the check.** You promised the "magic" was just abstraction; here's the proof. The callback to slide 1 closes the loop without requiring you to re-explain anything.
4. **Slide 4 is the handshake.** It's not an argument, it's a closing gesture: "this is a real system, now watch it run."

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

**Four slides, four jobs:**
1. "Magic" slide (~25 sec) → disarming hook, permission to simplify
2. Hero diagram (~2:30) → the whole argument
3. Real sequence uncovered (~50 sec) → rigor proof, callback to slide 1
4. Component diagram (~25 sec) → deployment footprint, glance only

**Three pillars:** Completeness → Precision → Trust

**Five stages, five analogies** (labels match the hero diagram exactly):
1. **Lobby Checkpoint** (amber) → security at the lobby, before any AI model sees the query
2. **Three Specialists** (blue) → Meaning + Exact-Match + Intent, working in parallel
3. **Consensus Vote** (blue) → RRF merge of the three specialist lists
4. **Senior Expert Review** (green) → Cohere rerank reads each candidate with the query in mind
5. **Compliance Filter** (red) → RBAC + version enforcement before hand-off

**Technical details to say aloud but keep off the slide:** RRF k=60, title boost 1.5x, HNSW index on 1024-dim Qwen3 embeddings, ParadeDB/Tantivy for BM25, top-50 into rerank, top-10 out.

**Three demo queries:**
1. Natural-language query with zero keyword overlap → semantic wins
2. Query with both concept + specific ID → hybrid wins
3. Adversarial input → validator wins (callback to teammate)

**One-liner on RBAC:** "Enforcement wired in, running as admin for demo visibility."

**Closer:** "Architecture on paper, working in the browser, boundaries enforced end to end."
