# Mini Strategic Plan

## AI-Driven Company-Wide Search Engine for Deloitte Resources

**Group Two:** Jesse Gabriel, Andrew Jung, Raven Levitt, Felix Tian, Sophia Turnbow, Matthew Voynovich

**ITWS 4100 — Information Technology Capstone — Spring 2026**

---

## 1. External Environment Analysis

### Industry Definition

This analysis positions the Deloitte AI Search Engine within the **Enterprise Search Software** industry. Enterprise search refers to platforms purpose-built to index, retrieve, and rank internal organizational content using advanced retrieval techniques such as semantic search, keyword matching, and neural reranking. The market was valued at $7.47 billion in 2026 and is projected to reach $11.66 billion by 2031, growing at a compound annual growth rate (CAGR) of 9.31% (Mordor Intelligence, 2026).

We deliberately exclude general-purpose productivity tools with embedded search features, such as Notion AI, Slack AI, and Microsoft 365 Copilot, from our competitive set. These tools are not enterprise search platforms. They are collaboration suites that added search as a secondary feature, and their technical capabilities confirm this distinction. Notion AI operates exclusively within its own workspace and cannot index external document repositories or enforce role-based access policies across heterogeneous file stores (Eesel AI, 2025). Slack AI is restricted to content within Slack and a narrow set of connected apps, meaning it works with only a fraction of a company's actual knowledge base (Question Base, 2026). Microsoft Copilot supports semantic retrieval on only six file extensions (.doc, .docx, .pptx, .pdf, .aspx, .one), cannot retrieve information from non-textual content such as images, charts, or tables in most formats, and does not support retrieval from tables in files other than .doc, .docx, and .pptx (Microsoft Learn, 2025). A Deloitte-scale organization with decades of documents in dozens of formats across multiple internal platforms requires a purpose-built retrieval system, not a feature grafted onto a collaboration suite. Enterprise search is a dedicated capability, not an add-on.

### Industry Attractiveness

The enterprise search market is attractive for two structural reasons. First, the demand driver is durable. Knowledge workers spend an average of 2.8 hours per week searching for information (APQC, 2021), and 29% of survey respondents report that extracting needed knowledge from document repositories is difficult or nearly impossible (Deloitte Insights, 2024). These inefficiencies persist regardless of economic cycles because they are rooted in organizational complexity, not market conditions. Second, the technology inflection point is real. The rapid adoption of Retrieval-Augmented Generation (RAG), vector embeddings, and generative AI is transforming enterprise search from a productivity add-on into foundational data infrastructure (Mordor Intelligence, 2026). This combination of persistent demand and technological disruption is what the textbook identifies as the ideal condition for above-average returns: an attractive industry environment matched with strategic capabilities (Hitt et al., Ch. 3, p. 79).

### Five Forces Analysis (Ch. 2, Ch. 5)

The Five Forces framework evaluates the structural attractiveness of an industry based on the competitive pressures that shape profitability. Applied to Enterprise Search Software:

**Threat of New Entrants: High.** The barriers to entry in enterprise search have dropped significantly. Open-source retrieval frameworks (Elasticsearch, pgvector, ParadeDB), pre-trained embedding models (Qwen3, BGE, E5), and cloud infrastructure have commoditized the foundational technology. A capable engineering team can build a functional search prototype with minimal capital investment. Our own project demonstrates this: a six-person student team built a hybrid retrieval system with semantic search, BM25 keyword search, and neural reranking using entirely open-source components. The low capital requirements and availability of open-source tooling make this industry accessible to new entrants, though building enterprise-grade integrations at scale remains a substantial barrier.

**Power of Suppliers: Low to Moderate.** The primary "suppliers" in this industry are cloud infrastructure providers (AWS, GCP, Azure) and AI model providers (OpenAI, Cohere, Anthropic). Cloud compute is commoditized with easy switching between providers. Embedding models are increasingly open-source, reducing dependence on proprietary APIs. Cohere's reranking API represents a notable exception where supplier power exists, though open-source cross-encoder rerankers on Hugging Face offer viable substitutes. Our prototype's architecture reflects this reality: the Cohere reranker is designed to gracefully degrade if unavailable, ensuring no single supplier holds critical leverage.

**Power of Buyers: High.** Enterprise buyers are sophisticated and cost-conscious. Procurement decisions involve lengthy evaluation cycles, security audits, and compliance reviews. Crucially, enterprises can build in-house solutions if vendor pricing becomes unreasonable. The availability of open-source alternatives gives buyers significant leverage. Large enterprises like Deloitte, with in-house AI/ML capabilities through the Deloitte AI Institute, have the engineering capacity to develop custom solutions rather than purchase commercial platforms. This buyer power constrains vendor pricing and forces commercial platforms to justify their value through integrations and support rather than core technology alone.

**Threat of Substitutes: Moderate.** The substitutes for dedicated enterprise search are the productivity tools discussed above: Slack AI, Notion AI, and Microsoft Copilot. While these tools are technically insufficient for comprehensive enterprise search (as argued in the industry definition), they satisfy the needs of organizations with simpler retrieval requirements. For companies that primarily work within a single ecosystem, such as all-Microsoft shops, Copilot may serve as "good enough." The threat is moderate because substitutes exist and are improving, yet they do not meet the requirements of knowledge-intensive enterprises that manage heterogeneous document repositories with strict access controls.

**Intensity of Rivalry: High.** The enterprise search market features well-funded competitors operating in a rapidly evolving technological landscape. Glean has established itself as the market leader with a $7.2 billion valuation, $765 million in total funding, and integrations across 100+ business applications (Glean, 2025). Elastic provides a flexible, open-source foundation with deep customization capabilities. Coveo dominates commerce and customer-facing search. The rapid adoption of generative AI and RAG is forcing all players to continuously innovate, intensifying rivalry further. Chapter 5 identifies this pattern as characteristic of a **fast-cycle market**, where "competitive advantages aren't shielded from imitation, and imitation is rapid and inexpensive" (Hitt et al., Ch. 5). In fast-cycle markets, firms must pursue continuous innovation rather than attempting to protect any single technological advantage.

### Competitor Analysis (Ch. 5)

Chapter 5 defines competitors as firms operating in the same market, offering similar products, and targeting similar customers. The framework uses **market commonality** (the number and importance of shared markets) and **resource similarity** (comparability of resource portfolios) to map the competitive landscape (Hitt et al., Ch. 5). The table below applies this framework to the major players in enterprise search:

| Competitor | Market Commonality | Resource Similarity | Positioning | Key Strength | Key Weakness |
|---|---|---|---|---|---|
| **Glean** | High | High | Full-stack AI enterprise search | 100+ app integrations, $100M+ ARR, knowledge graph personalization | Expensive ($20+/user/month), vendor lock-in |
| **Elastic** | Moderate | Moderate | Open-source search infrastructure | Highly customizable, strong developer ecosystem | Infrastructure, not product; requires significant engineering |
| **Coveo** | Low | Moderate | AI-powered search & recommendations | Strong in commerce and customer-facing search | Implementation complexity; 75% stock decline post-IPO |
| **Microsoft Search** | High | Low | Embedded in Microsoft 365 ecosystem | Zero marginal cost for existing Microsoft customers | Limited file type support, locked to Microsoft ecosystem |
| **Algolia** | Low | Low | Developer-first search API | Fast implementation, excellent documentation | Primarily keyword-based, limited semantic capabilities |

Glean and Microsoft Search represent the most direct competitive alternatives due to high market commonality. Both target the same buyer (large enterprises seeking internal knowledge retrieval), though their resource profiles differ substantially. Glean is a purpose-built search platform with deep AI capabilities. Microsoft Search is a bundled feature within a broader productivity suite. This distinction matters for competitive response prediction: Glean would likely respond aggressively to internal build initiatives because enterprise search is its entire business (high market dependence), while Microsoft has low dependence on search as a standalone revenue driver.

---

## 2. Internal Environment Analysis

### Organizational Profile

Deloitte is the largest professional services network in the world by revenue, reporting $70.5 billion in aggregate global revenue for FY2025 (fiscal year ended May 31, 2025), a 4.8% increase in local currency from FY2024 (Deloitte Global, 2025). The firm employs over 470,000 people across 700+ offices in more than 150 countries. Deloitte operates across four primary service lines: Audit & Assurance, Consulting, Financial Advisory, and Tax & Legal. The workforce is knowledge-intensive by nature: consultants, auditors, and advisors rely on internal documents, policies, methodologies, and past deliverables to serve clients effectively.

### Resources and Capabilities (Ch. 3)

Chapter 3 distinguishes between tangible resources (financial, organizational, physical, technological) and intangible resources (human, innovation, reputational) as the foundation for competitive advantage. The chapter emphasizes that "intangible resources are a superior source of capabilities and subsequently, core competencies" because they are less visible to competitors, harder to imitate, and can be leveraged without diminishing their value (Hitt et al., Ch. 3, p. 87). Applied to Deloitte's position in building an internal search engine:

**Tangible Resources:**

- *Financial*: $70.5 billion in annual revenue provides the investment capacity to fund custom internal tooling without external fundraising or venture capital dependencies
- *Technological*: Existing IT infrastructure with enterprise-grade cloud hosting and security certifications (SOC 2, ISO 27001, FedRAMP)
- *Physical*: Massive internal document corpus spanning decades of consulting engagements, audit reports, policy documents, slide decks, and training materials stored across distributed repositories

**Intangible Resources:**

- *Human*: Deep domain expertise in professional services workflows, which informs what "relevant search results" actually means for a consultant preparing a client deliverable versus an auditor checking compliance
- *Innovation*: The Deloitte AI Institute and Omnia AI platform represent sustained investment in AI research and deployment capabilities
- *Reputational*: Brand reputation that demands the highest standards of data security and compliance, particularly when handling confidential client materials; this reputation is itself a resource that constrains architecture decisions (no third-party data exposure)

**Capabilities:**

Capabilities emerge when "the firm combines individual tangible and intangible resources" to complete organizational tasks (Hitt et al., Ch. 3, p. 88). For the search engine initiative, three capabilities are particularly relevant:

1. In-house AI/ML engineering teams capable of building and maintaining custom retrieval models
2. Established data governance frameworks for classifying documents by sensitivity level (public, internal, confidential) and enforcing role-based access controls
3. Experience deploying enterprise-scale applications across a globally distributed workforce with diverse technology environments

### Value Chain Analysis (Ch. 3)

Chapter 3 introduces value chain analysis as a tool for identifying "the parts of its operations that create value and those that do not" (Hitt et al., Ch. 3, p. 93). For an internal search engine, the value chain is compressed: the "product" is information retrieval, and the "customer" is the Deloitte employee. The key value-creating activities are:

- **Operations** (Search Pipeline): Document ingestion, embedding generation, index maintenance, hybrid retrieval, reranking, and RBAC filtering. This is where the core technical value is created.
- **Distribution** (User Interface): The Next.js frontend delivers search results to employees. Speed, relevance ranking, and result presentation directly affect user adoption.
- **Follow-Up Service** (Feedback and Iteration): Query logging and relevance feedback allow continuous tuning of search quality over time.

The critical **support function** is **Management Information Systems (MIS)**, defined as obtaining and managing information and knowledge for strategic and operational decisions. The search engine is itself an MIS capability: it transforms scattered documents into retrievable, actionable knowledge. This dual nature — the search engine as both a product and a support function — reinforces why it should be built internally rather than purchased. Outsourcing a core MIS capability introduces dependency on an external supplier for a function that directly enables Deloitte's primary value-creating activities.

### VRIN Analysis (Ch. 3)

Chapter 3 identifies four criteria that determine whether a capability can serve as a source of sustainable competitive advantage: it must be Valuable, Rare, costly to Imitate, and Nonsubstitutable (Hitt et al., Ch. 3, pp. 90–92). The "Nonsubstitutable" criterion asks whether competitors can achieve the same strategic outcome through a different capability, which the textbook calls a "strategic equivalent" (p. 92).

| Resource/Capability | V | R | I | N | Competitive Consequence |
|---|---|---|---|---|---|
| Internal document corpus | Yes | Yes | Yes | Yes | **Sustainable competitive advantage** — decades of proprietary content that no competitor can access or replicate; no strategic equivalent exists |
| Domain expertise in professional services search | Yes | Yes | Moderate | No | **Temporary competitive advantage** — competitors could hire domain experts, and other professional services firms possess similar institutional knowledge |
| RBAC and compliance infrastructure | Yes | No | No | No | **Competitive parity** — standard enterprise security; multiple substitutes exist (LDAP, IAM platforms) |
| Hybrid search pipeline (semantic + BM25 + reranking) | Yes | No | No | No | **Competitive parity** — the technique is well-documented in academic literature and implemented by all major competitors |
| Open-source tech stack (Qwen3, pgvector, ParadeDB) | Yes | No | No | No | **Competitive parity** — available to all, though it strategically eliminates vendor dependency |

The VRIN analysis reveals a key insight: Deloitte's sustainable competitive advantage does not come from the search technology itself. It comes from the data the technology searches over. The internal document corpus satisfies all four criteria. It is valuable (enables faster, more relevant information retrieval). It is rare (no other organization possesses Deloitte's specific body of institutional knowledge). It is costly to imitate (built over decades of consulting engagements with unique historical conditions, one of the three sources of inimitability identified in Chapter 3). It is nonsubstitutable (there is no strategic equivalent to having direct access to the organization's own knowledge base). This distinction is critical for strategy formulation: the technology is the delivery mechanism, but the data is the moat.

---

## 3. Competitive Advantage Analysis

### Core Competencies

Building on the VRIN analysis, Deloitte's core competencies for the search engine initiative are:

1. **Proprietary data assets.** The internal document corpus is the engine's primary value driver. Search quality is ultimately bounded by content quality, and Deloitte's content is both extensive and domain-specific. Chapter 3 notes that intangible resources "can be leveraged" because "sharing knowledge among employees does not diminish its value for any one person" (p. 87). The search engine operationalizes this principle: it makes the same knowledge simultaneously available to 470,000 employees without reducing its value to any individual user.

2. **Data governance maturity.** Deloitte already classifies documents by sensitivity level and enforces access controls across its organization. This capability maps directly onto the RBAC filtering layer in the search pipeline, reducing implementation complexity compared to organizations that would need to build these controls from scratch. The textbook's discussion of capabilities notes that they emerge from combining tangible and intangible resources (p. 88). Deloitte's data governance capability combines tangible infrastructure (classification systems, access control lists) with intangible knowledge (understanding which documents require which access levels and why).

3. **Organizational readiness for AI adoption.** Deloitte has invested heavily in AI through its AI Institute and Omnia AI platform. The organizational culture and leadership support for AI-driven tools reduces the adoption risk that plagues many enterprise software deployments. Chapter 3 warns that core competencies can become "core rigidities" when environmental changes render previously valuable capabilities obsolete (p. 98). The Polaroid and Borders case studies illustrate this danger. Deloitte's AI readiness positions it to avoid this rigidity trap by proactively adopting AI-driven search rather than clinging to legacy keyword-only retrieval systems.

### Cost Advantage

The search engine achieves cost leadership relative to commercial alternatives through its open-source technology stack. The prototype uses Qwen3-Embedding-0.6B (Apache 2.0 licensed), PostgreSQL with pgvector and ParadeDB (no vector database licensing fees), and Docling for document parsing (MIT licensed). The only external paid service is Cohere's Rerank API, which gracefully degrades if unavailable. This eliminates the per-user licensing fees that commercial platforms charge. Glean, for example, charges $20+ per user per month. At Deloitte's scale of 470,000 employees, this would represent over $112 million annually — a cost that an internally built solution avoids entirely.

### Differentiation Advantage

The search engine differentiates from commercial alternatives in two ways.

First, it can be tuned for the specific vocabulary and information needs of professional services work. Generic enterprise search platforms optimize for broad applicability across industries. A custom solution can be optimized for Deloitte's specific document types (audit work papers, consulting frameworks, tax memoranda), organizational structure (service lines, practice areas, geographic offices), and user behavior patterns (how a senior consultant searches differently from an analyst). Chapter 4 describes differentiation as producing "goods or services that customers perceive as being different in ways that are important to them" (Hitt et al., Ch. 4, p. 122). Domain-specific retrieval relevance is the differentiating feature that matters most to Deloitte's internal users.

Second, it ensures complete data sovereignty. Sensitive client materials never leave Deloitte's infrastructure. No third-party vendor, regardless of contractual assurances, can match the level of control that an internally deployed system provides. For a firm that handles confidential financial data, pending M&A information, and privileged legal communications, data sovereignty is not merely a feature. It is a non-negotiable requirement.

### Sustainable Competitive Advantage

The sustainability of this competitive advantage depends on three factors identified in Chapter 3: "the rate of core competence obsolescence because of environmental changes, the availability of substitutes for the core competence, and the imitability of the core competence" (Hitt et al., Ch. 3, p. 79).

- **Obsolescence risk**: Low. The value of the internal document corpus grows over time as more documents are ingested. Unlike a technology advantage that can be leapfrogged, a data advantage compounds.
- **Substitute availability**: Low. No external platform can substitute for direct access to Deloitte's proprietary knowledge. External vendors can match or exceed the search technology, but they cannot replicate the data.
- **Imitability**: Low. The document corpus was built over decades of unique historical conditions (one of the three sources of costly-to-imitate capabilities identified in Chapter 3, p. 91). No competitor can retroactively create Deloitte's engagement histories, internal methodologies, or institutional knowledge.

---

## 4. Business-Level Strategy (Ch. 4)

### Strategy Selection

Chapter 4 defines five business-level strategies positioned along two dimensions: competitive scope (broad vs. narrow target market) and source of competitive advantage (lowest cost vs. distinctiveness) (Hitt et al., Ch. 4, p. 117). Deloitte's AI search engine should pursue a **focused differentiation strategy**.

The logic is straightforward. The search engine is not a product for the open market. It serves a single organization with a specific set of information retrieval needs. This is a narrow competitive scope by definition. Within that narrow scope, the primary value driver is not cost reduction (though costs are low due to the open-source stack) but the uniqueness of the search experience: domain-tuned relevance, proprietary content coverage, and enterprise-grade access controls that reflect Deloitte's specific organizational hierarchy. This combination points to focused differentiation.

Chapter 4 defines focused differentiation as "an integrated set of actions taken to produce goods or services that serve the needs of a particular competitive segment" through distinctiveness (p. 127). Deloitte's "competitive segment" is its own workforce of 470,000 professionals. The "distinctiveness" comes from three sources: (1) hybrid retrieval technology tuned to professional services vocabulary, (2) RBAC filtering aligned with Deloitte's organizational structure, and (3) exclusive access to a proprietary document corpus that no commercial alternative can index.

This strategy is preferable to the alternatives:

- **Cost leadership** (broad or focused) would prioritize minimizing search infrastructure costs over search quality. For a knowledge-intensive firm where billable utilization directly correlates with revenue, optimizing for cost at the expense of retrieval accuracy would be strategically misaligned. Professional services utilization averaged 68.9% in 2024, below the 70–75% optimal threshold (SPI Research, 2025). Even a modest improvement in search efficiency that recovers productive time translates directly into billable hours.

- **Broad differentiation** would require building a search platform applicable across industries and selling it to external customers. Deloitte is solving its own problem, not building a product for the market. A broad scope strategy introduces complexity (multi-tenant architecture, customer support, competitive pricing) that distracts from the core objective: helping Deloitte employees find information faster.

- **Integrated cost leadership/differentiation** is the closest alternative to our recommendation, as the open-source stack does provide meaningful cost advantages. However, the strategic emphasis is on differentiation. The cost savings are a byproduct of architectural choices made to avoid vendor dependency and ensure data sovereignty, not the primary strategic objective. Chapter 4 warns that integrated strategies carry the risk of becoming "stuck in the middle" — where the firm's cost structure is not low enough and its products are not sufficiently differentiated (p. 133). By committing to focused differentiation, Deloitte avoids this risk.

### Competitive Dynamics (Ch. 5)

Chapter 5 introduces **market commonality** (the number and importance of shared markets) and **resource similarity** (comparability of resource portfolios) as the two dimensions that predict competitive behavior between firms (Hitt et al., Ch. 5). Because Deloitte's search engine is an internal tool rather than a market-facing product, the competitive dynamics operate differently than in a traditional product market. Deloitte is not directly competing with Glean or Elastic for market share. Instead, it is making a **build-versus-buy decision**, which is fundamentally a strategic action rather than a competitive response.

Chapter 5 distinguishes between strategic actions (requiring significant resource commitments and difficult to reverse) and tactical actions (requiring fewer resources and easier to reverse). Building a custom search engine is a strategic action: it demands engineering investment, organizational commitment, and is difficult to reverse once integrated into workflows. Purchasing Glean would be a tactical action by comparison: easier to implement, easier to abandon. The textbook notes that "strategic actions elicit fewer total responses" but create more durable competitive positions (Ch. 5). This framing supports the build decision.

The competitive dynamics that matter most are **internal first-mover advantages**. Once the search engine is deployed and integrated into Deloitte's daily workflows — indexed on its data, tuned to its vocabulary, embedded in its user habits — switching to a commercial platform would require re-indexing, re-training, and re-establishing trust with users. This creates organizational switching costs that favor the internal solution, provided the initial deployment demonstrates clear value. Chapter 5 identifies first-mover benefits as including "the loyalty of customers who may become committed to the goods or services of the firm that first made them available" (Ch. 5). In this context, the "customers" are Deloitte employees, and the "loyalty" is workflow integration.

Finally, Chapter 5's market cycle framework places enterprise AI search in a **fast-cycle market** where "competitive advantages aren't shielded from imitation, and imitation is rapid and inexpensive." In such markets, firms must pursue continuous innovation rather than attempting to protect any single technological advantage. This reinforces the focused differentiation strategy: Deloitte's advantage is not the search algorithm (which can be imitated) but the proprietary data and organizational integration (which cannot). The technology must continuously evolve, but the underlying data moat is durable.

### Strategic Risks

Chapter 4 identifies three risks specific to focus strategies that Deloitte should monitor (Hitt et al., Ch. 4, pp. 128–129):

1. **Out-focusing.** A competitor could build an even more narrowly tailored search solution for a specific Deloitte service line (e.g., Audit-only search with compliance-specific retrieval logic) that outperforms the firm-wide tool within that segment. The mitigation is modular architecture: the search pipeline should support service-line-specific tuning without fragmenting into separate systems.

2. **Industry-wide competitor entry.** A major platform vendor such as Microsoft or Google could improve its embedded search capabilities to the point where a dedicated internal tool becomes redundant. Microsoft Copilot's current limitations (six supported file types, no table retrieval in most formats) make this unlikely in the near term, but the trajectory of improvement is rapid. Deloitte must continuously benchmark its internal solution against commercial alternatives to ensure it remains superior where it matters: retrieval relevance for professional services content.

3. **Segment needs converging with the broad market.** If Deloitte's information retrieval needs become sufficiently generic — for instance, if all documents migrate to a single cloud platform with native search — then the focused differentiation advantage erodes. The firm's document landscape is currently heterogeneous enough (multiple formats, repositories, sensitivity levels) that this convergence is unlikely in the medium term, but it should be monitored as cloud migration initiatives progress.

None of these risks invalidate the focused differentiation strategy. They define its boundary conditions and the ongoing investments required to sustain it.

---

## References

- Hitt, M. A., Ireland, R. D., & Hoskisson, R. E. (2017). *Strategic Management: Concepts and Cases: Competitiveness and Globalization* (12th ed.). Cengage Learning. Chapters 3, 4, and 5.
- Mordor Intelligence. (2026). Enterprise Search Market — 9%+ CAGR Forecast for 2026–2031. *GlobeNewswire*.
- Deloitte Global. (2025). Deloitte reports FY2025 revenue of $70.5 billion. *Deloitte Press Room*.
- Glean. (2025). Glean raises $150M Series F at $7.2B valuation. *Glean Press*.
- Microsoft Learn. (2025). Microsoft 365 Copilot Retrieval API Overview.
- Question Base. (2026). Enterprise Search vs. Slack AI: Key Differences.
- Eesel AI. (2025). Notion AI limitations & best practices: A 2025 guide.
- APQC. (2021). What Makes Deloitte Excellent at KM?
- Deloitte. (2024). The new organizational knowledge management. *Deloitte Insights*.
- SPI Research. (2025). Professional Services Maturity Benchmark Report.
