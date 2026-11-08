# **CAPSTONE PROJECT PROPOSAL**

## AI CAREERGUIDE: Personalized Major Guidance for Vietnamese High School Students

**DUY TAN UNIVERSITY \- INTERNATIONAL SCHOOL**  
**Course Code:** CMU-SE 450 – C1SE.71  
**Academic Unit:** Faculty of Information Technology / International School

## **PROJECT INFORMATION**

| Field | Details |
| :---- | :---- |
| **Project Title** | AI CareerGuide: Personalized Major Guidance for Vietnamese High School Students |
| **Project Acronym** | AI CareerGuide |
| **Project Type** | Responsive web application, AI-assisted decision-support system, grounded guidance platform |
| **Course Code** | CMU-SE 450 – Capstone Project 1 (Group C1SE.71) |
| **Academic Unit** | Faculty of Information Technology / International School, Duy Tan University |
| **Execution Window** | July 28, 2026 – December 26, 2026 (15-Week Implementation) |
| **Academic Supervisor** | MSc. Son, Phan Van |

## **DOCUMENT APPROVALS**

| Role | Name | Signature | Date |
| :---- | :---- | :---- | :---- |
| **Academic Mentor** | MSc. Son, Phan Van | Approved | Oct 20, 2026 |
| **Project Leader** | Duy, Nguyen Tan | Signed | Oct 20, 2026 |
| **Quality Assurance** | Cuong, Nguyen Tu | Signed | Oct 20, 2026 |

## **REVISION HISTORY**

| Version | Date | Key Modifications / Major Deliverables | Authors |
| :---- | :---- | :---- | :---- |
| **v1.0** | Aug 18, 2026 | Initial proposal draft and domain concept outline. | C1SE.71 Team |
| **v1.1–v1.5** | Aug–Sept 2026 | Incremental refinement of project scope, entity relationships, and architectural modules. | C1SE.71 Team |
| **v1.6** | Sept 05, 2026 | Pre-review baseline version for faculty submission. | C1SE.71 Team |
| **v1.7** | Sept 05, 2026 | Formal project proposal submission for defense panel evaluation. | C1SE.71 Team |
| **v1.8** | Oct 23, 2026 | **Major Revision:** 1\. Refined system scope to pure vocational career guidance, removing tuition and geographic filtering. 2\. Grounded system components in established theoretical models (RIASEC, Multiple Intelligences, MBTI dimensions, Phoenix Ho Career Tree). 3\. Formulated explicit scoring algorithms (Cosine Similarity, Z-score, 3-pillar weighted hybrid model). 4\. Finalized technology stack with Argon2id password hashing, LlamaIndex RAG orchestration, Tavily Search API, OpenAI Embeddings, and PostgreSQL (`JSONB` \+ `pgvector`). 5\. Established a two-stream knowledge architecture: official MOET circular ingestion for core major profiles and automated, major-code-cached roadmap discovery with Human-in-the-Loop staging to optimize token consumption and response latency. | C1SE.71 Team |

## **TABLE OF CONTENTS**

1\. Project Title  
2\. Team Members  
3\. Supervisor(s)  
4\. Problem Statement  
5\. Survey / Existing Solutions  
6\. Objectives and Scope  
7\. Key Features & Requirements  
8\. Constraints and Assumptions  
9\. Target Users / Stakeholders  
10\. Technology Stack  
11\. Methodology & Development Plan  
12\. System Architecture Overview  
13\. Potential Risks and Mitigation Strategies  
14\. Expected Outcomes / Deliverables  
15\. References

## **LIST OF TABLES**

**Table 1:** Team Members & Roles  
**Table 2:** Academic Supervisors  
**Table 3:** Existing Solution Comparison Matrix  
**Table 4:** System Functional Modules  
**Table 5:** Non-Functional Requirements Summary  
**Table 6:** Component Responsibility & Boundary Isolation Matrix  
**Table 7:** System Constraints Register  
**Table 8:** Target User Profiles & Roles  
**Table 9:** Technology Stack Architecture  
**Table 10:** 15-Week Agile Development Roadmap  
**Table 11:** Primary Data Flow Definitions  
**Table 12:** System Risk Matrix & Mitigation Strategies  
**Table 13:** Project Deliverables Catalog

## **LIST OF FIGURES**

**Figure 1:** Functional Module Flow Diagram  
**Figure 2:** Theoretical Framework Mapping Across 7 Student Journey Steps  
**Figure 3:** Two-Stream Knowledge Ingestion & Reusable Roadmap Pipeline (Human-in-the-Loop)  
**Figure 4:** 3-Tier System Architecture Diagram

## **1\. Project Title**

**AI CareerGuide: Personalized Major Guidance for Vietnamese High School Students**  
AI CareerGuide is a responsive, web-based decision-support platform designed to assist Vietnamese high school students in discovering suitable university majors and career paths. By synthesizing vocational interest assessments, cognitive learning preferences, and standardized academic performance across national subject combinations, the platform provides explainable major recommendations and structured, self-directed study roadmaps grounded in official Vietnamese higher education data and verified academic resources.

## **2\. Team Members**

The project is executed by a cross-functional engineering team of five students from Duy Tan University. Table 1 outlines the team composition and designated responsibility breakdown.  
**Table 1: Team Members & Roles**

| Full Name | Student ID | Project Role | Primary Responsibilities |
| :---- | :---- | :---- | :---- |
| **Duy, Nguyen Tan** | 29211142148 | Project Leader / Backend Engineer | Coordinates sprint backlogs, manages API integration, implements Argon2id authentication protocols, sets up CI/CD pipelines, maintains infrastructure. |
| **Trung, Nguyen Tam** | 29212736855 | System Architect / Full-Stack | Designs software architecture, database schemas, manages data migrations, enforces security specifications, builds deterministic business logic. |
| **Cuong, Nguyen Tu** | 29214360592 | Business Analyst / QA Engineer | Defines requirements, writes user stories, acceptance criteria, authors automated test suites, validates staging data consistency. |
| **Hieu, Nguyen Thai Hoang** | 29219030682 | Frontend / UI/UX Specialist | Develops responsive Web interfaces, ensures Web content accessibility (WCAG), builds evaluation flows, designs interactive dashboards. |
| **Hien, Nguyen Thanh Long** | 29219065409 | AI & Data Engineer | Constructs recommendation engine, implements mathematical scoring models, configures PostgreSQL `pgvector` integration, builds LlamaIndex Dual RAG pipelines. |

## **3\. Supervisor(s)**

Academic guidance and project supervision are provided by the faculty mentor detailed in Table 2\.  
**Table 2: Academic Supervisors**

| Supervisor Name | Academic Unit / Department | Contact Email |
| :---- | :---- | :---- |
| **MSc. Son, Phan Van** | Faculty of Information Technology / International School, Duy Tan University | sonpvs@duytan.edu.vn |

## **4\. Problem Statement**

High school students in Vietnam, particularly those in Grades 11 and 12, face critical university major decisions with limited understanding of their intrinsic interests, academic aptitudes, and future career environments. Career choices are frequently influenced by peer trends, family expectations, or isolated admission cut-off scores from prior years.  
Existing digital tools tend to present fragmented experiences:  
**Generic Personality Testing:** Online quizzes yield general career categories without contextualizing results within local academic frameworks or admission subject blocks.  
**Raw Admission Portals:** Official listing sites publish dense tables of historic admission benchmarks without providing personalized guidance or actionable self-study plans.  
**Premature Filtering:** Tools that filter choices prematurely by geographic location or tuition fees often discourage students from pursuing majors that match their genuine potential, ignoring available financial aid, academic scholarships, or national student support programs.  
AI CareerGuide functions as a dedicated, pure career guidance platform. It focuses entirely on evaluating three core student dimensions: (1) vocational interests, (2) cognitive learning preferences, and (3) academic readiness across standardized subject combinations. Built on Explainable AI (XAI) principles, the system presents ranked major recommendations alongside explicit compatibility metrics, identifies specific competency gaps, links majors to career roles, and generates actionable self-directed study plans backed by reusable, verified learning resources.

## **5\. Survey / Existing Solutions**

### **5.1 Overview of International Platforms**

International career guidance solutions such as MBTI Online and O\*NET Interest Profiler provide standardized vocational taxonomy frameworks. However, they lack native integration with Vietnamese university admission subject combinations (e.g., A00, A01, D01) and MOET major classification codes.

### **5.2 Overview of Domestic Solutions**

Domestic tools and university portals publish raw cutoff scores and program listings. They lack automated, multi-factor compatibility modeling, offering zero explainable guidance based on standardized academic grade normalization.

### **5.3 Limitations of Existing Tools**

Existing products either lack objective grade evaluations or introduce socio-economic bias by prematurely filtering majors by tuition and geography, rather than focusing purely on student aptitude and career fit. Furthermore, static portals do not bridge the gap between choosing a major and knowing which prerequisite skills to self-study before entering university.

### **5.4 Comparative Matrix**

**Table 3: Existing Solution Comparison Matrix**

| Platform / Approach | Strengths | Identified Limitations | AI CareerGuide Differentiation |
| :---- | :---- | :---- | :---- |
| **Official MBTI Assessments** | Evaluates personality traits and interpersonal preferences. | Lacks mapping to Vietnamese subject blocks; expensive licensing; omits grade evaluation. | Uses transparent preference indicators alongside objective grade analysis. |
| **Holland RIASEC / O\*NET Profiler** | Industry-standard vocational taxonomy connecting interests to work environments. | Designed for Western labor markets; lacks native integration with MOET codes. | Adopts RIASEC as core vector and maps scores directly to official MOET major classifications. |
| **16Personalities / CareerExplorer** | Engaging consumer UX and structured visual reporting. | Disconnected from national curricula and official subject block definitions (A00, A01, D01). | Binds profile assessments to national curriculum standards and verified MOET program structures. |
| **MOET Admission Portals** | Authoritative data source for institutional codes and circulars. | Strictly a public registry; offers zero personalized decision support or compatibility scoring. | Ingests official MOET circulars for major catalogs while adding multi-pillar scoring and cached AI study roadmaps. |

## **6\. Objectives and Scope**

### **6.1 General Objective**

To design, implement, and evaluate an explainable, web-based software platform that assists Vietnamese Grade 11–12 students in assessing their vocational interests, evaluating their academic readiness across national subject combinations, exploring well-matched university majors, and executing structured self-study plans without incurring high recurring AI token costs or unverified generative hallucinations.

### **6.2 Specific and Measurable Objectives**

**Complete Platform Delivery:** Deliver a functional web application covering profile setup, vocational testing, grade entry, major recommendation, career role exploration, and study roadmap execution within a 15-week development window.  
**Deterministic Evaluation Engine:** Implement deterministic scoring workflows for RIASEC and cognitive preferences supported by $100\%$ unit test coverage across mathematical calculations.  
**Explainable Recommendation System:** Develop a 3-pillar hybrid recommendation model that ranks target majors accompanied by detailed scoring breakdowns, top supporting factors, and competency gap analyses.  
**Structured Knowledge Base:** Construct a seed database containing at least 80 major profiles mapped to official MOET Level-IV codes extracted from MOET circulars, associated career paths, prerequisite knowledge, and target skill taxonomies.  
**Two-Stream Ingestion & Reusable Caching Pipeline:** Deploy (1) a semi-automated document processing pipeline for extracting official MOET major catalogs from regulatory PDFs/Excels, and (2) an automated/semi-automated roadmap discovery pipeline (using LlamaIndex and Tavily Search API) that retrieves verified study roadmaps from whitelisted sources, stages them for Human-in-the-Loop admin review, and caches approved roadmaps by `major_code` in PostgreSQL (`JSONB` and `pgvector`) for multi-student reuse.  
**Grounded Dual RAG System:** Configure LlamaIndex with OpenAI Embeddings and PostgreSQL `pgvector` to support document ingestion verification and provide grounded, token-efficient self-study guidance.  
**System Evaluation:** Conduct end-to-end usability and relevance testing with a target cohort of at least 20 students and academic mentors, aiming for average usability and recommendation satisfaction scores of $\ge 3.5 / 5.0$.

### **6.3 In Scope (MVP)**

Responsive web interface functional across desktop and mobile screens ($\ge 360\text{px}$ viewport width).  
User account management with Argon2id password security and age-appropriate privacy consent tracking.  
Standardized RIASEC assessment flow and cognitive preference evaluation questionnaire.  
Academic grade entry module supporting Z-score normalization, optional diagnostic skill checks, and subject-block alignment (e.g., A00, A01, D01, C00).  
Pure career guidance recommendation engine operating on interest fit, academic readiness, and cognitive preferences across at least 80 MOET major profiles.  
Exploration interfaces for university majors, career pathways, prerequisite knowledge, and target skill sets.  
Tiered self-study roadmap generation: detailed, personalized AI study roadmaps for skill domains with verified knowledge-base coverage (reused via `major_code` lookup), and verified general reference guidelines or fallback templates for majors awaiting detailed curriculum curation.  
Administrative portal featuring Human-in-the-Loop staging review for both uploaded MOET circulars and AI-collected learning roadmaps.  
Dual Retrieval-Augmented Generation (RAG) capabilities orchestrated via LlamaIndex and PostgreSQL `pgvector`.  
Exportable PDF summary reports detailing individual career guidance results.

### **6.4 Out of Scope (MVP)**

Native mobile applications (iOS/Android).  
Unconstrained live web scrapers targeting arbitrary, unverified external websites (roadmap collection is strictly restricted to whitelisted academic and authoritative educational domains via controlled search APIs).  
Manual authoring of bespoke curriculums by the development team for all 80 majors from scratch (addressed via automated resource discovery, normalization, and reuse).  
Payment gateway integration or monetized subscription systems.  
Filtering or ranking adjustments based on tuition fees or geographical locations (deliberately excluded to eliminate socio-economic bias).  
Black-box, non-deterministic neural networks for direct recommendation ranking.  
Formal clinical psychological diagnostic tools.

## **7\. Key Features & Requirements**

### **7.1 Functional Requirements**

**Figure 1: Functional Module Flow Diagram**  
\[FR01 Account & Consent\] $\rightarrow$ \[FR02 Vocational Assessment\] $\rightarrow$ \[FR03 Academic Grade Standardization\] $\rightarrow$ \[FR04 Explainable Recommender\] $\rightarrow$ \[FR05 Career Pathway Exploration\] & \[FR06 Study Roadmap / Guidance RAG\]. Administrative operations and knowledge curation governed by \[FR07 Ingestion, Caching & Governance\].  
**Table 4: System Functional Modules**

| Module ID | Module Name | Functional Description & Scope |
| :---- | :---- | :---- |
| **FR01** | Account & Consent | Manages student registration with Argon2id hashing, explicit privacy consent tracking under Vietnamese data protection regulations, and user profile maintenance. |
| **FR02** | Vocational Assessment | Administers validated RIASEC and cognitive preference questionnaires, calculates raw sub-scores, and tracks assessment history over time. |
| **FR03** | Grade Standardization | Captures multi-semester subject grades and optional diagnostic test results, validates inputs, normalizes performance via national Z-score parameters, and computes subject-block aptitudes. |
| **FR04** | Explainable Recommender | Computes overall major compatibility across 80+ majors using a deterministic 3-pillar model, presenting ranked results alongside component score breakdowns and gap analyses. |
| **FR05** | Career Exploration | Provides detailed major profiles linking official MOET Level-IV codes to real-world job titles, prerequisite skills, target competencies, and industry outlooks. |
| **FR06** | Roadmap & AI Guidance | Identifies student competency gaps in the backend, retrieves verified roadmaps cached by `major_code` from PostgreSQL/`pgvector` via LlamaIndex, and uses the AI API to personalize study schedules and tasks. Provides verified general guidance or fallback templates if a major lacks detailed data. |
| **FR07** | Admin Ingestion & Governance | Offers admin tools to (1) upload MOET circulars for core major profiles, and (2) trigger/review AI-discovered study roadmaps from whitelisted sources in a staging table (checking deduplication, source citations, and prerequisites) before publishing to the reusable knowledge base. |

### **7.2 Non-Functional Requirements**

**Table 5: Non-Functional Requirements Summary**

| NFR ID | Category | Specification Standard & Evaluation Metric |
| :---- | :---- | :---- |
| **NFR01** | Performance | Core API responses $\le 3\text{s}$; scoring loop $\le 2\text{s}$; cached roadmap lookup $\le 1\text{s}$; personalized RAG explanations $\le 8\text{s}$ with static fallback templates on timeout. |
| **NFR02** | Security & Privacy | Compliance with Vietnamese Personal Data Protection Law (Law No. 91/2025/QH15) and OWASP ASVS Level 2; TLS encryption, **Argon2id** password hashing, RBAC. |
| **NFR03** | Usability & Accessibility | Responsive UI for viewports $\ge 360\text{px}$; WCAG 2.1 AA text contrast ratio compliance ($\ge 4.5:1$ for normal text). |
| **NFR04** | Determinism & XAI | Identical inputs guarantee identical rankings; ranking math and prerequisite checks are strictly decoupled from non-deterministic LLM generation. |
| **NFR05** | Reliability & Cost Efficiency | $99\%$ operational availability during testing; write-once/read-many roadmap caching by `major_code` minimizes redundant external search and LLM token costs; system remains functional during LLM API outages via fallback templates. |

## **7.3 Recommendation Logic and Evaluation Framework**

### **7.3.1 Theoretical Framework Mapping Across Student Journey**

**Figure 2: Theoretical Framework Mapping Across 7 Student Journey Steps**  
Step 1 (Onboarding): Privacy & Agency Frameworks $\rightarrow$ Step 2 (Academic Readiness): Gardner's Multiple Intelligences Theory $\rightarrow$ Step 3 (Vocational Fit): Holland's RIASEC & MBTI Cognitive Dimensions $\rightarrow$ Step 4 (Major Recommendation): Person-Environment Fit & XAI $\rightarrow$ Step 5 (Taxonomy Link): Phoenix Ho Career Tree Model $\rightarrow$ Step 6 (Guidance Plan): Goal-Setting Theory & Self-Directed Learning $\rightarrow$ Step 7 (Evaluation): Continuous Feedback & Recalibration Loops.

### **7.3.2 Recommendation Scoring Algorithms**

**1\. Vocational Interest Score (Holland RIASEC via Cosine Similarity)**  
Student response vector $V_{\text{Student}} = [R_s, I_s, A_s, S_s, E_s, C_s]$ and target major vector $V_{\text{Major}} = [R_m, I_m, A_m, S_m, E_m, C_m]$ are evaluated using Cosine Similarity:  
$$\text{Score}_{\text{RIASEC}} = \frac{V_{\text{Student}} \cdot V_{\text{Major}}}{\|V_{\text{Student}}\| \times \|V_{\text{Major}}\|}$$

**2\. Academic Readiness Score (Z-Score Normalization)**  
Raw grades ($X$) for required admission subject blocks (e.g., A00) are standardized against national reference parameters ($\mu$, $\sigma$):  
$$Z = \frac{X - \mu}{\sigma}$$
$$\text{Score}_{\text{Academic}} = \text{Clamp}\left(\text{Average}(\text{CDF}(Z_s)), 0.0, 1.0\right)$$

**3\. Cognitive Preference Score (Rule-Based Mapping)**  
Cognitive preference dimensions are mapped to major learning environments via deterministic matching:  
$$\text{Score}_{\text{Preference}} = \frac{1}{K} \sum_{k=1}^{K} \text{Match}(\text{Trait}_k, \text{MajorAttr}_k)$$

**4\. Holistic 3-Pillar Weighted Hybrid Model**  
The overall compatibility score for a major is computed as:  
$$\text{Score}_{\text{Major}} = w_{\text{RIASEC}} \cdot \text{Score}_{\text{RIASEC}} + w_{\text{Academic}} \cdot \text{Score}_{\text{Academic}} + w_{\text{Preference}} \cdot \text{Score}_{\text{Preference}}$$  
Where baseline weights are set to $w_{\text{RIASEC}} = 0.45$, $w_{\text{Academic}} = 0.35$, $w_{\text{Preference}} = 0.20$ (constrained to $w_{\text{RIASEC}} + w_{\text{Academic}} + w_{\text{Preference}} = 1.0$).

### **7.3.3 Two-Stream Knowledge Ingestion & Reusable Roadmap Pipeline (Human-in-the-Loop)**

To solve the challenge of scaling across 80+ majors without requiring the project team to manually author domain-specific curriculums or paying recurring AI search costs for every student request, the system separates **Core Major Ingestion** from **Study Roadmap Discovery & Caching**:

*   **Stream A – Core Major Profiles (Official MOET Circulars):** Administrators upload official MOET regulatory PDFs/Excels (e.g., Circular 09/2022/TT-BGDĐT). The system parses Level-IV `major_code` identifiers, major names, and admission subject blocks into the Staging Database for admin verification.
*   **Stream B – 5-Step Automated Roadmap Discovery & Reusable Caching:**
    1.  **Document & Resource Collection:** When a `major_code` requires study roadmap enrichment, the system uses **Tavily Search API** and **Jina Reader** to discover and fetch syllabi, learning roadmaps, and study guides strictly from whitelisted authoritative domains (e.g., university curriculum portals, open courseware, recognized educational repositories).
    2.  **Extraction & Normalization:** **LlamaIndex** readers automatically parse PDF/HTML documents, chunk content, and use **Pydantic v2** structured output schemas with **OpenAI (`gpt-4o-mini`)** to extract prerequisite knowledge, target skills, step-by-step learning milestones, and reference materials.
    3.  **Staging Storage:** Extracted roadmap payloads and vector chunks are written to a PostgreSQL staging table (`status = PENDING`), preserving full provenance metadata (source title, original URL, page number, retrieval timestamp).
    4.  **Verification & Publication:** Backend validation routines check for duplicate entries, source validity, and prerequisite consistency. Administrators review and approve the staged roadmap via the Human-in-the-Loop UI (`status = APPROVED`), publishing the structured roadmap (`JSONB`) and vector embeddings (`pgvector`) indexed directly by `major_code`.
    5.  **Major-Code Reuse & Personalization:** Once published in PostgreSQL, the roadmap is reused across all future students interested in that `major_code`. When a student requests study guidance, the system retrieves the verified roadmap by `major_code` in milliseconds via SQL/vector lookup—avoiding repeated web searches—and uses the AI API only to tailor study schedules and tasks to the student's specific skill gaps. Documents are re-processed only when underlying source materials are updated.

**Figure 3: Two-Stream Knowledge Ingestion & Reusable Roadmap Pipeline (Human-in-the-Loop)**  
\[Stream A: MOET Circulars (PDF/Excel)\] & \[Stream B: Whitelisted Web Sources via Tavily API\] $\rightarrow$ \[LlamaIndex Parsing, Chunking & Pydantic Extraction\] $\rightarrow$ \[Staging DB (`status: PENDING`, Source URL, Page Citation, Deduplication Check)\] $\rightarrow$ \[Admin Interactive Review UI\] $\rightarrow$ \[Approved PostgreSQL (`JSONB` Roadmap by `major_code`) \+ `pgvector` Embeddings\] $\rightarrow$ \[Fast Retrieval & Student Personalization\].

### **7.3.4 Dual RAG System & Component Responsibility Boundaries**

The system employs **LlamaIndex** to orchestrate two distinct RAG pipelines backed by **PostgreSQL `pgvector`** and **OpenAI Embeddings (`text-embedding-3-small`)**:  
1.  **Ingestion RAG:** Assists platform administrators and automated collectors during document parsing by extracting structured skill prerequisites, detecting duplicates, and binding exact page/URL citations for staging approval.  
2.  **Guidance RAG:** Queries verified roadmaps and syllabi indexed in `pgvector` (filtered by `major_code` and missing skills) to generate personalized self-study tasks and learning explanations for students.

To ensure system trustworthiness and prevent AI hallucinations, strict architectural boundaries are enforced across five core components as defined in Table 6.

**Table 6: Component Responsibility & Boundary Isolation Matrix**

| System Component | Designated Technical Responsibilities | Strict Prohibitions & Guardrails |
| :---- | :---- | :---- |
| **Backend (FastAPI)** | Calculates 3-pillar compatibility scores; identifies missing skills (gap analysis); validates prerequisites and diagnostic test results; validates LLM outputs; tracks learning progress; serves static fallback roadmaps if data is insufficient or AI API fails. | Never delegates mathematical scoring or prerequisite logic to external LLMs. |
| **PostgreSQL (Relational + `JSONB`)** | Stores the 80+ official MOET major profiles, skill taxonomies, normalized roadmap structures (`JSONB` keyed by `major_code`), source citations/URLs, moderation statuses, and student progress records. | Never exposes unapproved (`PENDING`) staging records to student-facing endpoints. |
| **`pgvector` + LlamaIndex** | Manages document chunking, vector indexing, metadata filtering (by `major_code` and skill ID), and semantic retrieval strictly from the approved knowledge base. | Never retrieves from unverified external web sources during live student ranking flows. |
| **AI API (`gpt-4o-mini`) + Tavily Search** | Assists in initial resource discovery from whitelisted domains (Ingestion phase); explains academic concepts, personalizes study schedules, and formats actionable self-study tasks based on retrieved context. | **Prohibited** from treating unverified documents as fact, fabricating citations, generating detailed roadmaps without grounded data, or altering major rankings. |
| **Administrator** | Audits staged major records and AI-collected roadmaps, verifies source credibility and prerequisite links, and approves content before publication to the official knowledge base. | Does not manually author full curriculums for all 80 majors from scratch. |

## **8\. Constraints and Assumptions**

### **8.1 Constraints**

**Table 7: System Constraints Register**

| Constraint Domain | Type | Description & Operational Impact |
| :---- | :---- | :---- |
| **Pure Guidance Scope** | Functional Constraint | Tuition fees and geographical location filters are strictly excluded to avoid socio-economic bias. |
| **Data-Dependent Roadmap Depth** | Content Constraint | Detailed AI self-study roadmaps are generated only for majors/skill groups with verified data in the knowledge base; majors with insufficient data default to general verified guidelines. |
| **Regulatory Privacy** | Legal Constraint | Must strictly adhere to Vietnamese Data Protection Law (Law No. 91/2025/QH15). |
| **Development Window** | Schedule Constraint | Must complete end-to-end implementation within a strict 15-week Capstone execution timeframe. |
| **Deterministic Ranking** | Architectural Constraint | Recommendation scores must remain $100\%$ deterministic and reproducible via standard math formulas. |

### **8.2 Assumptions**

High school students have access to web browsers on mobile or desktop devices with internet connectivity.  
Official MOET admission circulars and subject block definitions remain publicly accessible for admin upload.  
Authoritative university syllabi and educational roadmap repositories remain accessible via whitelisted search APIs for initial knowledge ingestion.  
Standardized national Z-score parameters effectively represent grading distributions across high schools.

## **9\. Target Users / Stakeholders**

Table 8 defines the primary users and key stakeholder groups served by the AI CareerGuide platform.  
**Table 8: Target User Profiles & Roles**

| User Role | Target Audience | Primary Platform Interaction & Value Proposition |
| :---- | :---- | :---- |
| **Primary Users** | Grade 11 & 12 Students | Takes assessments, inputs grades and optional diagnostic checks, explores major fit, views gap analyses, and executes personalized self-study roadmaps. |
| **Secondary Beneficiaries** | Parents & Educators | Reviews exported PDF career guidance reports and verified source citations to provide informed academic and career coaching. |
| **Platform Administrators** | Data Managers & Admins | Uploads MOET regulatory documents, triggers automated roadmap collection for specific major codes, reviews and approves staged records in the Human-in-the-Loop UI. |

## **10\. Technology Stack**

The system is built on a modern, unified technology stack designed to minimize operational complexity and maximize token efficiency.  
**Table 9: Technology Stack Architecture**

| Architecture Layer | Selected Technology | Rationale & Architectural Role |
| :---- | :---- | :---- |
| **Frontend Framework** | React 18, TypeScript, Vite, Tailwind CSS | Delivers accessible, high-performance responsive user interface down to $360\text{px}$ screen width. |
| **Backend REST API & Security** | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, **Argon2id** (`argon2-cffi`) | Asynchronous API execution, strict schema validation for structured AI outputs, deterministic gap/prerequisite logic, and OWASP-recommended **Argon2id** password hashing. |
| **Database, Cache & Vectors** | PostgreSQL 16 + `pgvector` extension + `JSONB` | Unified storage for relational major profiles, reusable `major_code`-indexed study roadmaps (`JSONB`), and vector embeddings (`pgvector`) without requiring a separate vector DB infrastructure. |
| **RAG Framework** | **LlamaIndex** | Single unified framework for document parsing (PDF/HTML), semantic chunking, vector indexing, metadata-filtered retrieval, and managing both Ingestion RAG and Guidance RAG pipelines. |
| **LLM & Search Services** | OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`), **Tavily Search API**, Jina Reader | Generates 1536-dimensional vector embeddings, performs whitelisted web discovery for initial roadmap curation (Tavily/Jina), and personalizes student study plans from cached DB context. |
| **DevOps & Testing** | Docker, GitHub Actions, Pytest, Playwright | Containerized deployment, automated continuous integration pipelines, $100\%$ unit test verification on scoring math, and end-to-end UI testing. |

## **11\. Methodology & Development Plan**

### **11.1 Agile Development Methodology**

The project adopts the Agile Scrum framework, executed across seven 2-week development sprints followed by final deployment and evaluation.

### **11.2 Sprint Execution Plan**

**Table 10: 15-Week Agile Development Roadmap**

| Sprint Phase | Timeframe | Key Deliverables & Technical Objectives |
| :---- | :---- | :---- |
| **Sprint 0** | Wk 1–2 | System modeling, architecture design, PostgreSQL + `pgvector` schema definition, UI wireframing. |
| **Sprint 1** | Wk 3–4 | FR01 Authentication with **Argon2id**, user consent tracking, profile management, base CI/CD setup. |
| **Sprint 2** | Wk 5–6 | FR02 RIASEC & preference assessment questionnaires, deterministic scoring implementation. |
| **Sprint 3** | Wk 7–8 | FR03 Grade entry, Z-score standardization, FR04 3-pillar recommendation scoring engine. |
| **Sprint 4** | Wk 9–10 | FR07 Two-stream ingestion pipeline (MOET PDF upload + Tavily/LlamaIndex roadmap discovery), staging DB deduplication, Human-in-the-Loop admin review UI. |
| **Sprint 5** | Wk 11–12 | FR05 Major exploration (80+ profiles), FR06 backend skill-gap/prerequisite engine, reusable `major_code` roadmap lookup & Guidance RAG personalization. |
| **Sprint 6** | Wk 13–14 | System integration, security hardening, fallback template verification, performance tuning, end-to-end usability testing. |
| **Release** | Wk 15 | Final production deployment, handover documentation, capstone defense presentation. |

### **11.3 Quality Gates**

Each sprint requires $100\%$ unit test coverage for mathematical scoring and prerequisite validation modules, successful static code analysis pass, and QA acceptance sign-off prior to merging.

## **12\. System Architecture Overview**

### **12.1 Architecture Description**

**Figure 4: 3-Tier System Architecture Diagram**  
Tier 1 (Presentation): React 18 SPA $\rightarrow$ Tier 2 (Application): FastAPI Modular Services (Identity \[Argon2id\], Assessment, Recommender, Taxonomy, Gap & Roadmap Engine, LlamaIndex Dual RAG Orchestrator) $\rightarrow$ Tier 3 (Persistence & External AI): Unified PostgreSQL 16 DB (`Relational` + `JSONB` Roadmap Cache + `pgvector`) & External APIs (OpenAI API, Tavily Search API for Staging Ingestion).

### **12.2 System Context**

The system connects students and platform admins with underlying backend services. External Search and LLM APIs are strictly isolated: web discovery (Tavily) is invoked only when populating or updating the knowledge base for a `major_code`, while student-facing roadmap requests read directly from verified PostgreSQL/`pgvector` records and use OpenAI strictly to tailor schedules and explanations.

### **12.3 Data Flows**

**Table 11: Primary Data Flow Definitions**

| Flow ID | Source | Destination | Data Payload & Description |
| :---- | :---- | :---- | :---- |
| **DF01** | Student Interface | Assessment Engine | Raw RIASEC/preference responses, subject grades, and optional diagnostic check inputs. |
| **DF02** | Assessment Engine | Recommender Core | Normalized RIASEC vector, Z-scores, cognitive preference traits; outputs deterministic major rankings and skill gaps. |
| **DF03** | Admin Portal / Tavily API | LlamaIndex Ingestion Pipeline | Uploaded MOET regulatory PDFs/Excels (core majors) and whitelisted academic web/PDF documents (study roadmaps). |
| **DF04** | Ingestion Pipeline | Staging DB | Normalized JSON major records, extracted skills/prerequisites, source URLs/page citations (`status: PENDING`). |
| **DF05** | Admin Review UI | Primary PostgreSQL & `pgvector` | Admin-approved major profiles, reusable `major_code` roadmap structures (`JSONB`), and OpenAI vector embeddings (`status: APPROVED`). |
| **DF06** | Guidance RAG & Backend | Student Interface | Retrieved verified roadmap for target `major_code` + backend skill gap analysis $\rightarrow$ AI-personalized study schedule (or static fallback template). |

### **12.4 Security & Privacy Architecture**

Features TLS 1.3 transport encryption, **Argon2id** memory-hard password hashing (aligned with NFR02 and OWASP ASVS Level 2), Role-Based Access Control (RBAC) separating students from staging reviewers, and strict Personal Identifiable Information (PII) sanitization before sending contextual prompts to external OpenAI endpoints.

## **13\. Potential Risks and Mitigation Strategies**

Table 12 summarizes identified project risks along with severity ratings and mitigation strategies.  
**Table 12: System Risk Matrix & Mitigation Strategies**

| Identified Risk Domain | Severity / Impact | Risk Mitigation Strategy |
| :---- | :---- | :---- |
| **PDF & Web Extraction Errors** | High Impact / High Likelihood | LlamaIndex Pydantic structured extraction combined with a mandatory Human-in-the-Loop staging UI requiring admin verification before publishing. |
| **LLM Generative Hallucinations** | High Impact / Medium Likelihood | Restrict LLMs to synthesizing verified source text in `pgvector`; enforce strict citation binding; provide general verified guidelines if a major lacks detailed data; exclude LLMs from ranking math. |
| **High AI Token & Search Latency Costs** | Medium Impact / High Likelihood | Cache verified roadmaps and embeddings in PostgreSQL (`JSONB` + `pgvector`) indexed by `major_code` (write-once, reuse-many); only re-index when source documents change. |
| **External API Outages** | Medium Impact / Medium Likelihood | Implement deterministic backend fallback templates and serve pre-cached `JSONB` roadmaps directly from PostgreSQL when OpenAI APIs time out. |
| **User Assessment Dropout** | Medium Impact / High Likelihood | Intuitive step-by-step UI with auto-save progress indicators and estimated completion times. |

## **14\. Expected Outcomes / Deliverables**

Table 13 lists all major physical and digital deliverables produced during the project.  
**Table 13: Project Deliverables Catalog**

| ID | Deliverable Name | Detailed Content & Format |
| :---- | :---- | :---- |
| **D1** | Production Application | Deployed responsive web application for AI CareerGuide platform. |
| **D2** | Recommender Package | Verified scoring module implementing RIASEC cosine similarity, Z-score normalization, and 3-pillar hybrid model. |
| **D3** | Knowledge Base & Roadmap Cache | PostgreSQL database containing 80+ MOET Level-IV major profiles, skill taxonomies, and reusable `major_code`-indexed study roadmaps with `pgvector` embeddings. |
| **D4** | Codebase & Test Suite | Managed source repository with automated unit, integration, and end-to-end test suites. |
| **D5** | Engineering Docs | Complete engineering documentation set including SRS, Architecture Design, Test Results. |
| **D6** | Operations Manuals | User Manual for students and Administration & Ingestion Guide for platform operators. |
| **D7** | Capstone Assets | Project Evaluation Report, demonstration media, and presentation slide deck. |

## **15\. References**

\[1\] National Center for O\*NET Development, "O\*NET Interest Profiler," O\*NET Resource Center, 2026\.  
\[2\] J. L. Holland, "Making Vocational Choices: A Theory of Vocational Personalities and Work Environments," Psychological Assessment Resources, Odessa, FL, 1997\.  
\[3\] H. Gardner, "Frames of Mind: The Theory of Multiple Intelligences," Basic Books, New York, 1983\.  
\[4\] P. Ho, "Dung Ngoi Cho Co Hoi Den (Career Tree Guidance Framework)," Tre Publishing House, Ho Chi Minh City, 2020\.  
\[5\] Ministry of Education and Training of Vietnam, "Circular 09/2022/TT-BGDĐT: List of Higher Education Training Programs," MOET, Hanoi, 2022\.  
\[6\] National Assembly of Vietnam, "Law No. 91/2025/QH15 on Personal Data Protection," Hanoi, 2025\.  
\[7\] OWASP Foundation, "Application Security Verification Standard (ASVS) 5.0," OWASP, 2025\.  
\[8\] ISO/IEC 25010:2023, "Systems and Software Quality Requirements and Evaluation (SQuaRE)," ISO, 2023\.  
\[9\] K. Schwaber and J. Sutherland, "The Scrum Guide," 2020\.  
\[10\] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," Advances in Neural Information Processing Systems, 2020\.  
\[11\] E. A. Locke and G. P. Latham, "Building a Practically Useful Theory of Goal Setting and Task Motivation," American Psychologist, 2002\.  
\[12\] J. R. Hackman and G. R. Oldham, "Motivation through the Design of Work: Test of a Theory," Organizational Behavior and Human Performance, 1976\.  
\[13\] PostgreSQL Global Development Group, "pgvector: Open-source Vector Similarity Search for PostgreSQL," 2026\.  
\[14\] J. Liu, "LlamaIndex: Data Framework for LLM Applications," 2026\.