# Gap Categories — Closing Strategies Reference

Used in Phase 3 of the gap-closer pipeline.
Load this file when categorizing gaps and generating specific closing strategies.

## Table of Contents
1. [Technical Skills](#1-technical-skills)
2. [Domain Knowledge](#2-domain-knowledge)
3. [Portfolio Evidence](#3-portfolio-evidence)
4. [Credentials](#4-credentials)
5. [Cultural Signals](#5-cultural-signals)
6. [Experience Depth](#6-experience-depth)

---

## 1. Technical Skills

**Definition:** Missing a specific language, framework, tool, or platform the role requires.

**JD signals:** "Experience with X", "Proficiency in X", listed in hard requirements or tech stack section.

**Closing strategy priority:**
1. **Build something real** with the tool, using an existing project as the foundation. A project with the tool in a real context beats a Udemy certificate.
2. **Add to an existing project** — integrate the tool into the resume tailoring engine, networking pipeline, or another existing repo.
3. **Structured tutorial** — only if no existing project can absorb the tool.

**Candidate-specific bridges (check first before recommending):**

| Gap Tool | Candidate's Closest Existing Skill | Bridge Action |
|---|---|---|
| Kubernetes | Docker (implied by containerization work) | Deploy resume tailoring engine on K8s locally (minikube), write an architecture post |
| Snowflake | SQL (confirmed), data warehouse familiarity | Connect a free Snowflake trial to an existing dataset, run ETL queries, add to portfolio |
| LangChain / AutoGen | Google ADK (confirmed multi-agent work) | Port one NuOnc agent to LangChain, compare patterns, write a blog post |
| Vector DB (Pinecone, pgvector) | RAG-adjacent from LLM work | Add a semantic search layer to the networking pipeline using pgvector |
| dbt | SQL (confirmed), ETL methods | Rebuild the BC research ETL pipeline in dbt, publish the models to GitHub |
| TypeScript | JavaScript/Node.js (confirmed via resume_template.js) | Port the resume template script to TypeScript, add type safety |
| Power BI | Tableau (confirmed) | Replicate an existing Tableau dashboard in Power BI on a public dataset |
| Ray / Dask | Python (confirmed), batch processing | Parallelize the batch resume processing pipeline using Ray |
| FastAPI | REST APIs (confirmed), Python | Wrap grade_resume.py in a FastAPI endpoint, deploy on Railway or Render |
| React | JavaScript/Node.js (partial) | Build a simple frontend for the resume tailoring engine using React |

**Proof artifact:** Public GitHub repo with README explaining what the tool does and why it was chosen. Even a small, focused project counts more than a certificate.

**Time estimates:**
- Adding to existing project: 3-8 hours
- New focused project: 8-20 hours
- Full-stack integration: 15-30 hours

---

## 2. Domain Knowledge

**Definition:** Missing industry-specific knowledge, methodology, or business context the role expects.

**JD signals:** "Experience in [industry]", "Familiarity with [regulation/framework]", domain jargon in responsibilities section.

**Closing strategy priority:**
1. **Apply the knowledge to an existing project** — even a lightweight version demonstrates genuine engagement
2. **Annotate existing work with domain framing** — relabel achievements using domain vocabulary
3. **Write a focused post** synthesizing what you've learned and how it applies to your existing experience
4. **Read primary sources** — industry reports, regulatory docs, company 10-Ks (not just blog summaries)

**Candidate-specific examples:**

| Domain Gap | Action |
|---|---|
| Fintech / payments compliance | Ant Group experience already covers this. Reframe existing achievements with AML/BSA terminology in bullets. |
| Enterprise SaaS metrics | Apply ARR, NRR, churn concepts to ModyLife customer data. Write an analysis. |
| E-commerce fundamentals | Gedia and ModyLife experience covers D2C. Reframe with LTV/CAC/payback period language. |
| Healthcare AI regulations | Map NuOnc work to HIPAA considerations. Write a short post on "building responsible AI for healthcare." |
| Supply chain / logistics | Use the Marketplace Economics project as anchor. Extend with a logistics ROI case study. |

**Proof artifact:** A short written piece (blog post, LinkedIn article, GitHub README section) that demonstrates fluency, not just awareness.

**Time estimate:** 2-5 hours of reading + 2-3 hours writing = 4-8 hours total

---

## 3. Portfolio Evidence

**Definition:** The candidate HAS the skill but has no publicly demonstrable proof. The role requires seeing examples.

**JD signals:** "Portfolio required", "Show us your work", "GitHub link", "previous projects", implicit expectation of demos for technical roles.

**Closing strategy priority:**
1. **Publish existing private work** — clean up, document, and push to GitHub
2. **Record a demo video** — a 3-5 minute walkthrough of an existing project (Loom, YouTube unlisted)
3. **Write a technical post** — explain how you built something (the "how" matters more than the "what")
4. **Create a focused case study** — one project, one problem, one solution, one result

**Candidate-specific opportunities (already built, just needs publishing):**

| What Exists | Publication Action | Time |
|---|---|---|
| Resume Tailoring Engine (this project) | Already on GitHub ✓. Record a 5-min demo video walking through a real tailoring run. | 2-3 hrs |
| Networking Pipeline | Push to GitHub with a README explaining the MCP architecture + demo video | 4-6 hrs |
| BC Inflation ETL | Create a Jupyter notebook showing the pipeline and sample outputs, push to GitHub | 3-4 hrs |
| Ant Group risk analysis work | Cannot publish (NDA). Write a sanitized case study on "how to approach KYC fraud analysis" using public data as illustration | 3-4 hrs |
| Gedia/ModyLife analysis | Create a public portfolio piece using similar public data (e.g., Airbnb open data) to demonstrate the same analytical pattern | 4-6 hrs |

**Proof artifact:** Public URL (GitHub repo, YouTube video, personal site, Medium post). Must be linkable in a resume or cover letter.

**Time estimate:** 2-8 hours depending on how much cleaning/documentation is needed.

---

## 4. Credentials

**Definition:** The role explicitly values or requires a specific certification, course completion, or educational credential.

**JD signals:** "AWS certified preferred", "CFA a plus", "PMP or similar", certification names in requirements.

**Priority rule:** Only pursue credentials where the certificate itself signals something (AWS, GCP, Databricks, CFA, etc.). Do NOT pursue low-signal certificates (Udemy, Coursera completion certificates for generic topics). Time is better spent on portfolio evidence.

**High-signal credentials for this candidate's target roles:**

| Credential | Relevance | Time to Complete | Free? |
|---|---|---|---|
| Google Cloud Professional ML Engineer | Agentic AI, ML roles | 40-60 hrs study | No (~$200 exam) |
| AWS Certified Cloud Practitioner | AI/ML, data roles | 15-20 hrs | No (~$100 exam) |
| Databricks Lakehouse Fundamentals | Data analyst, ML roles | 6-8 hrs | Yes |
| Google Analytics Certification | Product analyst, growth | 4-6 hrs | Yes |
| Salesforce Trailhead badges | Operations, CRM roles | 4-8 hrs per badge | Yes |
| dbt Fundamentals (dbt Learn) | Data analyst, analytics eng | 4-6 hrs | Yes |
| DeepLearning.AI Short Courses | Agentic AI roles | 1-2 hrs each | Free (audit) |

**Strategy:** If a credential takes under 10 hours and is free, do it during Week 1. If it requires exam fees or 20+ hours of study, only pursue if it's a hard requirement.

**Proof artifact:** Certificate badge shared on LinkedIn + added to resume Skills section.

---

## 5. Cultural Signals

**Definition:** The role or company culture values participation in a community, ecosystem, or practice that the candidate hasn't demonstrated publicly.

**JD signals:** "Values open-source contributors", "active in the AI community", "technical blogger", "speaker experience", company culture sections mentioning transparency/community.

**Most common cultural gaps and specific actions:**

### Open-Source Contributions
The most common cultural signal for engineering roles. Does NOT require building a new tool from scratch.

**Low-friction entry points for this candidate:**

1. **Contribute to a framework already used** — Google ADK, docx-js, or openpyxl are frameworks already in the codebase. Find an open issue (bug, documentation, test, example), fix it, open a PR.
   - Start with `good first issue` labels on GitHub
   - Documentation PRs count and are merged faster than code PRs
   - Expected time: 3-6 hours for first PR

2. **Open-source the resume tailoring engine's components** — Already done (GitHub). Add a `CONTRIBUTING.md`, open a few `good-first-issue` issues, and invite contributions. This makes YOU the open-source project maintainer, which is higher signal than being a contributor.

3. **Publish a utility from the existing pipeline** — Extract `grade_resume.py` as a standalone CLI tool with a clean interface. Publish to PyPI. A published package is strong open-source signal.
   - Package name: `resume-grader` or similar
   - Expected time: 4-6 hours including packaging and publishing

4. **Release the grading rubric** — The `references/grading_rubric.yaml` is a standalone artifact. Open it as a community resource with a dedicated README explaining the methodology.

### Technical Writing
Companies value engineers who can explain their work clearly.

**Quick wins for this candidate:**
1. **"How I built X" post** about the resume tailoring engine — the architecture decisions, the instruction-driven design, the lessons learned. Publish on Medium, dev.to, or personal blog.
2. **LinkedIn technical post** (not full article) — 150-300 words explaining one specific technical insight from recent work. Post weekly during job search.
3. **GitHub README quality** — A great README IS technical writing. Audit the resume-tailoring-engine README for completeness and clarity.

### Community Presence
- Join relevant Discord servers (Latent Space, LangChain, LocalLLaMA) and ask/answer questions
- Comment thoughtfully on AI papers posted to Twitter/X or LinkedIn
- This takes 20-30 min/week and compounds over time

**Proof artifact for open-source:** GitHub profile showing merged PRs or maintained repos, PyPI package link.
**Proof artifact for writing:** Published URL (Medium, dev.to, personal site, LinkedIn article).

**Time estimate:** 3-10 hours for first contribution, 20-30 min/week ongoing for community.

---

## 6. Experience Depth

**Definition:** The candidate has exposure to a skill or domain but at a lower level of scope, scale, or seniority than the role expects.

**JD signals:** "5+ years required", "led a team of X", "owned the end-to-end architecture", "enterprise scale", "managed $XM budget".

**Closing strategies:**

1. **Reframe existing experience at full scope** — many candidates undersell scope. Audit the career ledger: are all the `reframe_ceiling` limits being used fully? Is the candidate claiming partial credit for things they can fully claim?

2. **Take on a stretch project** — use the next 30 days to do a project at the scale the role expects. For example, if a role expects "experience with production ML systems serving 1M+ users," the networking pipeline (300+ drafts/week) and resume engine (60+ generated) are real production artifacts — frame them appropriately.

3. **Fill the narrative gap** — Write a LinkedIn post or blog entry that explains a decision-making moment, a tradeoff you navigated, or a system design choice. This demonstrates senior thinking even without the title.

4. **Honest positioning** — If the gap is 3+ years of seniority for a true senior role, address this directly in cover letters: "I'm targeting this role as a growth opportunity with full intention to deliver senior-level output from day one, as demonstrated by [specific evidence]."

**What NOT to do:** Do not inflate scope, claim team leadership you didn't have, or fabricate enterprise scale. The `reframe_ceiling` in the career ledger exists exactly for this reason.

**Time estimate:** Reframing = 1-2 hours. Stretch project = 10-30 hours. Narrative writing = 2-4 hours.
