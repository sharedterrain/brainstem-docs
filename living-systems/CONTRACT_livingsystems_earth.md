# CONTRACT (livingsystems.earth)

```yaml
---
doc_id: "contract_livingsystems_earth"
contract_version: "0.2.1"
parent_contract: "contract_openclaw_deployment"
last_updated: "2026-03-14"
owner: "Jedidiah Duyf"
created: "2026-02-27"
---
```

**Status:** Draft

---

## §1 Purpose & Scope

This contract governs [**livingsystems.earth**](http://livingsystems.earth/) — a website project executed by Magi as a downstream consumer of the OpenClaw deployment platform. It defines the durable rules, invariants, and boundaries for the site's architecture, content strategy, hosting, and commercial structure.

**What this contract governs:**

- Site architecture, technology stack, and hosting

- Content strategy, publishing workflow, and editorial boundaries

- Lead funnel and commercial structure

- Design principles and transferability requirements

- Integration points with Brain Stem and other systems

- Phase boundaries and success criteria

**What this contract does NOT govern:**

- OpenClaw runtime, model routing, or exec approval policies (governed by CONTRACT (OpenClaw Deployment))

- Brain Stem pipeline architecture (governed by CONTRACT (Brain Stem))

- Workspace-wide governance (governed by CONTRACT (Hub))

**Relationship to parent contract:** This contract inherits all platform-level rules from CONTRACT (OpenClaw Deployment) — model routing, update discipline, messaging channel, exec approvals, and security posture. Where this contract is silent on a platform concern, the parent contract governs.

---

## §2 Site Identity & Vision

[livingsystems.earth](http://livingsystems.earth/) serves as:

1. **Business presence** for consulting work in AI, sustainable design, regenerative systems, traditional ecological knowledge, and Indigenous land stewardship

1. **Research and news hub** curating content in ecological restoration, regenerative design, traditional ecological knowledge, Indigenous knowledge systems, and the intersection of AI with living systems

1. **Lead generation and product gateway** where lead funnels direct prospects toward a diversifying range of products and services — the site structure accommodates this commercial dimension from day one

1. **Publishing destination** that Brain Stem's content pipeline eventually feeds into

1. **Proof of concept** demonstrating agentic site building and maintenance — directly relevant to future consulting engagements

1. **LCA Database host** — a public-facing Life Cycle Assessment data tool embedded within the site as a dynamic feature module. The LCA Database makes environmental impact data accessible to non-specialists (designers, procurement teams, students, sustainability-curious consumers), drives organic traffic, demonstrates analytical capability, and serves as the freemium lead-generation engine for future B2B offerings. Governed by its own child contract: CONTRACT (LCA Database) v0.1.0, subordinate to this contract.

**Invariant:** The site is a living document, not a brochure. It evolves continuously through autonomous research, content generation, and Magi-driven maintenance cycles.

---

## §3 Technology Stack

### §3.1 Static Site Generator

**Invariant:** The site is built with **Hugo** as the static site generator. Hugo was selected for zero-dependency builds (single Go binary), deterministic output, millisecond build times, and agent-friendly file-based architecture.

**Invariant:** Content pages use no JavaScript framework. HTML + minimal JS only. Interactive features (if needed later) use Hugo shortcodes or JS islands, not a framework migration.

### §3.2 Content as Flat Files

**Invariant:** All site content lives as **Markdown files with YAML frontmatter** in a Git repository. Content is never locked in a database, CMS, or proprietary format. The `content/` directory is the irreplaceable asset — everything else (theme, config, tooling) is replaceable.

### §3.3 Repository Structure

**Invariant:** The [livingsystems.earth](http://livingsystems.earth/) repo is a **separate Git repository** under shared terrain on Metacarcinus. It is distinct from the Notion doc mirroring repo and any other project repos.

**Required top-level structure:**

```plain text
livingsystems.earth/
├── content/              # Markdown content (the valuable asset)
│   ├── _index.md         # Homepage
│   ├── about/
│   ├── research/         # Research articles and curations
│   ├── news/             # News aggregation and commentary
│   ├── services/         # Consulting offerings
│   ├── products/         # Products and offerings (from day one)
│   └── projects/         # Portfolio / case studies
├── themes/
│   └── livingsystems/    # Custom theme (owned, not third-party)
├── static/               # Images, assets
├── config.toml           # Hugo configuration
├── deploy.sh             # Deployment script
└── .github/              # Optional: GitHub Actions for backup builds
```

**Invariant:** The `products/` content section exists from launch. The full funnel architecture develops as offerings crystallize, but the structural accommodation is present from day one.

### §3.5 LCA Database — Dynamic Data Component

The LCA Database feature introduces a dynamic data component beyond Hugo's static output. This is architecturally accommodated via the **JS islands pattern** already established in §3.1 — Hugo generates the site shell and all content pages; one or more pages mount the LCA application component as an interactive island.

**Invariant:** The LCA application is a consumer of a **versioned REST API** (API-first architecture). The frontend component and the data-serving backend are independently deployable and independently replaceable. No tight coupling between the Hugo site and the LCA data layer.

**Invariant:** The LCA data layer must remain **modular and portable** — no vendor lock-in on the infrastructure platform. The specific platform where the API and data store run (serverless functions, lightweight server, managed database, etc.) is an open architectural decision governed by CONTRACT (LCA Database) and subject to a dedicated planning session.

**Invariant:** The LCA feature ships with **open, publicly available datasets only** for v1 (USLCI, USDA LCA Digital Commons, TRACI). Licensed datasets (ecoinvent, GaBi) are deferred until B2B revenue justifies them. See CONTRACT (LCA Database) for the full data source registry and pipeline specification.

**Data pipeline:** Magi crawls public data sources → parses and normalizes to common schema → deduplicates → stores in backend → serves through API → LCA island component renders results. Human review checkpoints apply at data validation stages.

### §3.6 Deployment Pipeline

**Invariant:** Deployment follows a deterministic pipeline: Magi builds locally → verifies build → commits to Git → deploys to hosting via rsync/SFTP or Git hooks → reports status to messaging channel.

**Invariant:** The Git repository is the canonical source. The site is redeployable to any host from the repo alone.

---

## §4 Hosting & Infrastructure

### §4.1 Current Configuration

| **Component** | **Current Value** | **Notes** |
| --- | --- | --- |
| Domain registrar | WHC (Web Hosting Canada) | Domain already parked |
| Hosting provider | Cloudflare Pages | Free tier. CDN-level distribution. |
| Deploy method | Git push to sharedterrain/livingsystems-earth (private) | Cloudflare Pages connected to repo. Auto-builds on push. |
| Build command | `hugo --gc --minify` | Output dir: public |
| Custom domain | [livingsystems.earth](http://livingsystems.earth/) | Verified and green as of 2026-03-13 |
| SSL | Cloudflare-provided | HTTPS active |

### §4.2 Green Hosting Principle

**Invariant:** Hosting must use verified renewable energy sources (actual generation, not just carbon offsets). WHC's BC and Quebec hydroelectricity meets this standard. Any future hosting migration must maintain equivalent or better green credentials.

### §4.3 Scaling Path

Cloudflare Pages free tier (current) → Cloudflare Pages Pro or equivalent edge platform (Vercel, Netlify) when traffic or commercial scaling demands it. Hugo's static output deploys to any of these with minimal configuration changes.

**Scaling triggers** (any one is sufficient):

- Shared hosting bandwidth or performance limits interfere with user experience

- A commercial engagement requires CDN-level distribution or edge deployment

- WHC service changes make the hosting untenable

---

## §5 Content Strategy

### §5.1 Content Domains

The site covers these interconnected domains:

- Ecological restoration and regenerative design

- Traditional ecological knowledge and Indigenous knowledge systems

- Indigenous land stewardship and its intersection with regenerative design

- AI applications in living systems and sustainability

- Consulting services in the above areas

### §5.2 Content Types

- **Research articles** — curated and original content on core domains

- **News commentary** — aggregation and analysis of developments in the field

- **Service pages** — consulting offerings and engagement descriptions

- **Product pages** — offerings as they crystallize

- **Project portfolio** — case studies and demonstrations

- **Rolling research digest** — weekly or bi-weekly curated roundup

### §5.3 Publishing Workflow

**Invariant:** No content auto-publishes to the live site without human approval. Magi researches, drafts, and proposes — Jedidiah reviews and approves via messaging channel before publish.

**Workflow:**

1. Magi researches topics (web search, source material)

1. Magi drafts content as Markdown in the repo

1. Magi posts draft summary to messaging channel for review

1. Jedidiah approves, requests edits, or rejects

1. Approved content is committed, built, and deployed

1. Magi reports deployment status to messaging channel

### §5.4 Content Jedidiah Provides

The following content requires human authorship — Magi cannot generate these autonomously:

- Bio and professional narrative

- Service offerings and descriptions

- Vision statement and brand voice guidance

- Brand preferences (colors, tone, reference sites)

---

## §6 Lead Funnel & Commercial Structure

**Invariant:** Email capture (newsletter signup) is present from Phase 1 launch. This is the lead funnel foundation.

**Invariant:** The site structure accommodates commercial growth from day one. The `products/` and `services/` content sections exist at launch even if initially sparse. The full funnel architecture develops as offerings crystallize.

**Commercial evolution:** The site starts as a presence and research hub. As consulting engagements develop and product offerings solidify, the commercial infrastructure expands within the existing structure — no architectural migration required.

---

## §7 Design Principles

These principles govern architectural trade-offs for the website:

1. **Transferability above all.** Content in Markdown, builds to static HTML, deployed via standard protocols. If Hugo dies, the content works with any SSG. If WHC goes away, the Git repo deploys anywhere. No vendor lock-in at any layer.

1. **Flat files over databases.** No WordPress, no Ghost, no CMS that creates hosting dependencies or attack surfaces. Content as files in Git.

1. **No framework lock-in for content pages.** No React, Vue, or framework churn. Content pages are HTML + minimal JS. Interactive features use islands, not full frameworks.

1. **Ship minimal, iterate in phases.** Phase 1 ships with a modified open-source Hugo theme. Design perfection does not block launch. Custom theme evolves as Magi gains proficiency.

1. **Green credentials are non-negotiable.** Hosting must use verified renewable energy. This aligns with the site's subject matter and values.

---

## §8 Integration Points

### §8.1 Brain Stem Integration (Phase 3)

Brain Stem content outputs map to Hugo-compatible Markdown via Make webhook or direct script. The integration creates the full loop: Capture (Slack/Brain Stem) → Process (Airtable/Make) → Publish (Magi/Hugo/WHC).

**Invariant:** Brain Stem integration does not alter the site's publishing workflow. Brain Stem content enters the same draft → review → approve → publish pipeline as Magi-generated content.

### §8.2 LCA Database (Phase 2–3)

The LCA Database is a major feature module of this site, governed by CONTRACT (LCA Database) v0.1.0 (subordinate to this contract). It introduces a dynamic data component into the static site architecture.

**Data flow:** Magi crawls public LCA data sources (USLCI, USDA, TRACI) → normalizes to common schema → stores in data backend → serves through versioned REST API → LCA island component on the site renders search, browse, and compare interfaces.

**Invariant:** The LCA feature follows the same human approval gate as all site content. The LCA data pipeline outputs and the feature going live on the site both require Jedidiah's review and approval via messaging channel.

**Invariant:** The LCA data layer is independently deployable from the Hugo site. The site mounts the LCA frontend as a JS island; the backend API is a separate service. Either can be updated without rebuilding the other.

**Contract reference:** All LCA-specific architectural decisions (data sources, schema, API specification, infrastructure platform, evolution path to LCA Pro B2B) are governed by CONTRACT (LCA Database). This contract governs only the integration surface: how the LCA feature fits within the site's architecture, publishing workflow, and phase boundaries.

### §8.3 RSS & Syndication

RSS feed is implemented in Phase 2. Hugo has built-in RSS support. The feed enables syndication and future integration with external platforms.

---

## §9 Phase Boundaries

### Phase 0: Infrastructure

**Complete when:**

- Full deploy pipeline tested (local build → WHC)

- Hugo installed and configured on Metacarcinus

- Git repo initialized with required structure

- WHC hosting provisioned with SSH/SFTP access

- Deploy credentials configured on Metacarcinus

### Phase 1: Scaffold + Ship

**Complete when:**

- [livingsystems.earth](http://livingsystems.earth/) resolves to a live Hugo site

- At least 4 content pages published (About, Services, Contact, initial Research)

- Email capture mechanism functional

- Magi can build and deploy via messaging channel command or cron

- Deployment succeeds 3 consecutive times without intervention

### Phase 2: Content Engine + LCA Data Pipeline

**Complete when:**

- Magi has autonomously researched and drafted 5+ articles

- Human review → approve → publish loop working via messaging channel

- Content publishing cadence established (weekly minimum)

- RSS feed operational

- LCA data pipeline operational: Magi crawls MVP datasets (USLCI, USDA, TRACI), normalizes to common schema, and stores in data backend

- LCA data validated at human review checkpoints

- LCA infrastructure platform decision made and documented (dedicated planning session)

### Phase 2.5: LCA Feature Live

**Complete when:**

- LCA search/browse/compare interface mounted on the site as JS island

- LCA API serving normalized data from MVP datasets

- A user can search for a material or process and see environmental impact scores

- LCA feature approved by Jedidiah and deployed to production

- LCA informational content pages published (methodology explainers, dataset descriptions)

### Phase 3: Brain Stem Integration

**Complete when:**

- Brain Stem content outputs map to Hugo Markdown and enter the publishing pipeline

- Full loop operational: Capture → Process → Publish

- At least 3 Brain Stem–sourced articles published through the pipeline

### Phase 4: Autonomous Maintenance

**Ongoing — complete when self-sustaining:**

- Scheduled security scans and link validation

- Content freshness checks flag stale pages

- Monthly operational cost under C$35

- Magi operates with minimal daily oversight

---

## §10 Cost Boundaries

**Target monthly cost:** Under C$35/month total (hosting + API usage through OpenRouter).

**Cost tracking:** API costs are tracked through OpenRouter's dashboard. Hosting costs are tracked through WHC billing. No separate cost tracking infrastructure required.

**Cost escalation trigger:** If monthly costs exceed C$50 for two consecutive months, review model routing and content generation volume. This is an investigation trigger, not a hard cap.

---

## §11 Change Control

**Version bump rules:**

- **Patch (0.0.x):** Configuration updates (hosting details, current values), clarifications

- **Minor (0.x.0):** New sections, new content domains, new integration points

- **Major (x.0.0):** Changes to design principles, technology stack decisions, invariants

**Change tracking:** This contract is its own source of truth for change history. The `contract_version` in the YAML header tracks the current version. Notion's page version history provides the full diff timeline. Significant deviations or decisions are logged in §12 below.

**Downstream reconciliation:** Per CONTRACT (Hub) §2, when this contract is updated, downstream documents in the impact radius must be reconciled in the same work session or carry a staleness banner: `⚠️ STALE — see [version]`.

---

## §12 Deviation Log

*Tracks significant deviations, decisions, and rationale that led to contract changes. Not every patch-level edit needs an entry — only changes where the "why" matters for future reference.*

| **Version** | **Date** | **Description** |
| --- | --- | --- |
| 0.1.0 | 2026-02-27 | Initial draft. Codifies Hugo + WHC + flat-file architecture, content strategy, publishing workflow with human review gate, lead funnel from day one, green hosting requirement, and phase boundaries. Derived from Feb 27 Strategy Plan and advisory session. |
| 0.2.0 | 2026-03-10 | LCA Database integration. Added LCA as core feature in §2 Site Identity. Added §3.5 (LCA dynamic data component — JS islands, API-first, modular/portable, open datasets only for v1). Added §8.2 (LCA integration point with data flow and contract reference). Updated §9 phase boundaries: Phase 2 expanded to include LCA data pipeline, new Phase 2.5 for LCA feature going live. Renumbered deployment pipeline (§3.6) and RSS (§8.3). Reflects architectural decision that LCA Database is a feature of [livingsystems.earth](http://livingsystems.earth/), not a separate project. |
| 0.2.1 | 2026-03-13 | Phase 0 deployed to Cloudflare Pages (free tier) rather than WHC shared hosting. WHC retained as domain registrar only. Cloudflare Pages selected for CDN distribution, zero-config SSL, and Git-native deploy pipeline. §4 updated to reflect current state. |

---

## §13 Related Documents

- [CONTRACT (Open-Claw Deployment)](https://www.notion.so/545a69a1ea2a41de9a5fb5edaaaa1ea5) — parent contract (platform rules)
[https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/magi/CONTRACT.md](https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/magi/CONTRACT.md)

- [CONTRACT (Hub)](https://www.notion.so/c18af9cbec3b4c388c3561036a4871f1) — workspace-wide governance
[https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/hub/CONTRACT-Hub.md](https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/hub/CONTRACT-Hub.md)

- [Magi × livingsystems.earth — Scope Assessment & Strategy Plan](https://www.notion.so/31470cff90fc8061a462e56881c2d4e8) — full strategy plan and feasibility assessment
[https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/living-systems/Scope-Assessment-Strategy-Plan.md](https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/living-systems/Scope-Assessment-Strategy-Plan.md)

- [CONTRACT (Brain-Stem)](https://www.notion.so/cb5393105c784cc3969571a898b4f81e) — Brain Stem pipeline (Phase 3 integration source)

- [CONTRACT (LCA Database)](https://www.notion.so/0042bf99ca59458b80e1725b0b381ec5) — LCA feature module (child contract, subordinate to this contract)
[https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/brain-stem/CONTRACT.md](https://raw.githubusercontent.com/sharedterrain/Notion-Mirror/refs/heads/main/brain-stem/CONTRACT.md)
---

**End of CONTRACT (**[**livingsystems.earth**](http://livingsystems.earth/)**) v0.2.1**
