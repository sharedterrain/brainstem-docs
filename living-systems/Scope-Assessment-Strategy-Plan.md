# Magi × livingsystems.earth — Scope Assessment & Strategy Plan

> 📦 **Superseded by **[**CONTRACT (OpenClaw Deployment)**](https://www.notion.so/545a69a1ea2a41de9a5fb5edaaaa1ea5)** and **[**CONTRACT (livingsystems.earth)**](https://www.notion.so/35560bdc09cf4e78bdf4ea9466ea9f91) — This document is retained as a historical advisory reference. The contracts are the source of truth for all operational decisions, phases, and technology choices. The reasoning, cost analysis, risk tables, and technology evaluations below informed the contracts and remain useful context.

**Date:** 2026-02-27 **Author:** Claude (Magi Project Advisor) **Status:** Historical — superseded by contract **Context:** Defines Magi's first autonomous mission — building and maintaining [livingsystems.earth](http://livingsystems.earth/) as a research, news, and business presence site, using cost-effective models on OpenClaw. Magi's messaging channel (currently Slack) will be finalized during Phase 0.

---

## 1. Vision Statement

Magi builds, maintains, and evolves livingsystems.earth as an autonomous project. The site serves as:

- **Business presence** for Jedidiah's consulting work in AI, sustainable design, regenerative systems, traditional ecological knowledge, and Indigenous land stewardship

- **Research and news hub** aggregating and curating content relevant to ecological restoration, regenerative design, traditional ecological knowledge, Indigenous knowledge systems and their intersection with regenerative design, and the intersection of AI with living systems

- **Lead generation and product gateway** where lead funnels direct prospects toward a diversifying range of products and services — the site structure accommodates this commercial dimension from day one, with the full funnel architecture developing as offerings crystallize

- **Publishing destination** that Brain Stem's content pipeline eventually feeds into

- **Proof of concept** demonstrating agentic site building and maintenance — directly relevant to future consulting engagements with NGOs

The template is Wes Roth's model: an OpenClaw agent that researches, writes code, commits to Git, and deploys — running autonomously on scheduled cycles with human oversight via messaging channel approvals (currently Slack; channel selection finalized in Phase 0).

---

## 2. Feasibility Assessment

### 2.1 Model Support: Gemini 3.1 on OpenClaw

**Status: Supported as of v2026.2.21, but you're on v2026.2.19-2.**

OpenClaw added native Gemini 3.1 support in the February 21st release (`google/gemini-3.1-pro-preview`). Your current version (2026.2.19-2) predates this. An update to at least 2026.2.21 is required.

**Applying the "pin and wait" principle:** v2026.2.21 shipped February 21st. As of today (Feb 27), that's 6 days — past the 3-5 day waiting period. Check GitHub issues for regression reports before updating.

**Configuration path:**

- All models routed through **OpenRouter** as the unified gateway (see Model Routing below)

- OpenRouter provides provider flexibility — switch models without reconfiguring provider auth

- ~5.5% overhead on token costs accepted as worthwhile for this flexibility

- No separate Gemini API key configuration needed; OpenRouter handles provider auth for all models

- Gemini 3.1 Pro, Gemini Flash, Sonnet 4.5, and Haiku all accessed via OpenRouter

**Note on Gemini Pro subscription:** Jedidiah has a Gemini Pro retail subscription (paid through Oct 2026), but this does **not** include API access. API access requires a separate Google AI Studio account. The free tier (60 req/min, 1,000 req/day) may be sufficient for development phases but is not needed when routing through OpenRouter.

**Cost comparison (per 1M tokens):**

**All models accessed via OpenRouter.** Prices below include the ~5.5% OpenRouter markup.

| Model | Input | Output | Context |
| --- | --- | --- | --- |
| Gemini 3.1 Pro (via OpenRouter) | ~$2.11 | ~$12.66 | 1M tokens |
| Claude Sonnet 4.5 (via OpenRouter) | ~$3.17 | ~$15.83 | 200K tokens |
| Claude Opus 4.6 (via OpenRouter) | ~$15.83 | ~$79.13 | 200K tokens |
| Gemini 3 Flash (via OpenRouter) | ~$0.53 | ~$0.53 | 1M tokens |
| Haiku (via OpenRouter) | ~$0.26 | ~$1.32 | 200K tokens |

**Recommended model routing for Magi:**

**All models routed through OpenRouter as the unified gateway.**

| Task | Model (via OpenRouter) | Rationale |
| --- | --- | --- |
| Heartbeat | Haiku (default) | Cheapest; keep unless testing shows Flash more reliable through OpenRouter. Cost difference is negligible (fractions of a cent/day) — this is a pure cost-only decision since OpenRouter unifies provider access. |
| Site building (code gen) | Gemini 3.1 Pro | Best cost/reasoning ratio for generation tasks |
| Content research/drafting | Gemini 3.1 Pro | 1M context + web grounding; includes traditional ecological knowledge, Indigenous land stewardship, and regenerative design research |
| Routine cron maintenance | Gemini 3 Flash (thinking) | Ultra-cheap, surprisingly capable |
| Tool-use-heavy tasks (exec ops, approval workflows) | Sonnet 4.5 (preferred) | OpenClaw's tool-use layer was built for Anthropic models; Gemini integration is newer and tool compliance may be lower for exec operations |
| Complex architectural decisions | Sonnet 4.5 | First-class Anthropic support in OpenClaw's agent runtime |
| Perspective reset / unblocking | Opus 4.6 | High-level reasoning when other models are stuck; not for routine work. Cost justified only when cheaper models have failed to resolve the issue. |

**Key advantage:** Gemini 3.1's 1M token context window means Magi can hold an entire site codebase in context during development sessions — no chunking needed.

**Known limitations:** OpenClaw's agent runtime was optimized for Anthropic models. Community reports suggest Gemini works well for research and code generation but may need prompt tuning for tool use patterns — hence Sonnet 4.5 is preferred for tool-use-heavy tasks. The heartbeat model bleed bug (#22133) should be verified as resolved in 2026.2.21. All models are accessed via OpenRouter (~5.5% markup), which is accepted as worthwhile for provider flexibility and simplified configuration.

### 2.2 OpenClaw Tooling for Site Building

**Can Magi actually build and deploy a website?** Yes. The required capabilities all exist:

| Capability | OpenClaw Tool | Status |
| --- | --- | --- |
| Write code files | `exec` (shell) + `apply_patch` | Available now |
| Run build commands | `exec` | Available now |
| Git operations | `exec` (git CLI) | Available now |
| Web research | Web search/fetch | Available now |
| Browser testing | Browser tool (CDP) | Available, needs Chrome |
| File system operations | Native workspace tools | Available now |
| Scheduled builds | Cron | Available now |
| Deploy notifications | Messaging channel (currently Slack) | Available now |

**The workflow loop (modeled on Wes Roth's approach):**

1. Magi receives task (via cron trigger or messaging channel command)

1. Magi researches (web search for content, reads source material)

1. Magi writes/edits code in workspace

1. Magi runs build locally to verify

1. Magi commits and pushes to GitHub

1. Hosting provider pulls from GitHub (webhook or polling) and deploys

1. Magi reports status to messaging channel

**Gap analysis:**

- **Chrome/Chromium for browser tool:** May not be installed on Metacarcinus. Needed for visual testing. Can be deferred — CLI-based build verification works for initial phases.

- **GitHub SSH keys:** Metacarcinus needs SSH access to a GitHub repo. Straightforward to configure.

- **Build toolchain:** Node.js already present (OpenClaw dependency). Static site generator will need to be installed.

### 2.3 Hosting: Canadian, Green, Agent-Compatible

**Your situation:** Domains already parked at WHC (Web Hosting Canada). WHC itself offers green hosting powered by BC and Quebec hydroelectricity.

**Evaluation of Canadian green hosting options:**

**WHC (Web Hosting Canada) — Recommended**

- Already your registrar (simplest path)

- 100% renewable energy (BC + Quebec hydro)

- Data centers in Montreal and Vancouver (West Coast = lower latency for Victoria)

- Shared hosting from C$3.89/month, bills in CAD

- Git deployment support via SSH/SFTP

- Green Business Bureau certified

- SSD storage, water cooling

**PlanetHoster**

- Canadian data center on 100% hydro power

- Ecological air cooling system

- Shared hosting available, bills in CAD

- Good reputation in Canadian market

**GreenGeeks (.ca)**

- 300% renewable energy match via Bonneville Environmental Foundation

- Canadian data center option

- Slightly more marketing-heavy, US-headquartered

- From $2.95 USD/month

**EthicalHost**

- Toronto-based, Bullfrog Power (wind + renewable)

- Smaller operation, more niche

- Good values alignment with your work

**Recommendation:** WHC. You're already there, the green credentials are strong and verifiable (actual hydro power, not just offsets), Vancouver data center gives you local latency, CAD billing avoids exchange rate pain, and it's the simplest migration path. Shared hosting is sufficient for a static site.

### 2.4 Architecture for Transferability

**The "future-looking and nimble" requirement demands these principles:**

1. **Content as flat files (Markdown).** Your content should never be locked in a database or proprietary CMS. Markdown files in a Git repo can be consumed by any static site generator, any CMS, any future AI system.

1. **Static site generator, not a CMS.** WordPress, Ghost, and similar systems create hosting dependencies and attack surfaces. A static site generator produces plain HTML/CSS/JS that runs anywhere.

1. **Git as the single source of truth.** Every change tracked, every version recoverable, portable to any hosting provider by changing a deploy target.

1. **Standard deployment (SSH/SFTP or Git hooks).** No vendor-specific CI/CD. WHC supports SSH access; Magi pushes built files directly or via Git.

1. **No JavaScript framework lock-in for content pages.** React/Vue sites create maintenance burden and framework churn. Content pages should be HTML + minimal JS. Interactive features (if needed later) can be islands.

---

## 3. Recommended Technology Stack

### 3.1 Static Site Generator: Hugo

**Why Hugo over alternatives:**

| Factor | Hugo | Eleventy | Astro |
| --- | --- | --- | --- |
| Build speed | Milliseconds (Go binary) | Seconds (Node.js) | Seconds (Node.js) |
| Dependencies | Single binary, zero deps | Node.js + npm packages | Node.js + npm packages |
| M1 native | Yes (arm64 binary) | Yes (via Node) | Yes (via Node) |
| Agent-friendly | Very — file-based, predictable | Good | More complex |
| Content model | Markdown + YAML frontmatter | Flexible | Flexible |
| Transferability | Markdown content works anywhere | Same | Component-tied |
| Learning curve for AI | Low — templates are Go HTML | Medium | Higher |
| Multilingual | Built-in | Plugin | Plugin |
| Image processing | Built-in | Plugin | Built-in |

**Hugo wins on three fronts that matter for Magi:**

1. **Zero Node.js dependency sprawl.** Hugo is a single Go binary. No `node_modules`, no dependency vulnerabilities, no npm update churn. On an 8GB M1 Air, this matters.

1. **Deterministic builds.** Same input always produces same output. Critical for an autonomous agent — fewer "it worked last time" failures.

1. **Speed.** A full site rebuild in under a second means Magi can build-test-iterate rapidly without burning tokens waiting for builds.

**Hugo is confirmed as the SSG for this project.** It is the boring-reliable choice, which is exactly what you want for an agent's first autonomous project. If interactive component needs arise later, Hugo's partial/shortcode system and JS islands approach can accommodate them without a framework migration.

### 3.2 Hosting Configuration

```plain text
livingsystems.earth (domain at WHC)
    → WHC shared hosting (Vancouver DC)
    → Deploy via: Magi builds locally → rsync/SFTP to WHC
    → OR: GitHub repo → WHC Git deploy (if supported on plan)
    → Backup: GitHub repo is the canonical source; redeployable anywhere
```

**Estimated hosting cost:** C$3.89–7.89/month (shared hosting tier, annual billing saves ~15%).

**Scaling path:** The architecture supports migration to Vercel, Netlify, or Cloudflare Pages when traffic or commercial scaling demands it. Hugo's static output deploys to any of these with minimal configuration changes (update `deploy.sh` or add a CI config). This is a planned scaling path, not a current need — WHC shared hosting is confirmed for Phase 1.

### 3.3 Repository Structure

```plain text
livingsystems.earth/
├── content/              # Markdown content (the valuable asset)
│   ├── _index.md         # Homepage
│   ├── about/
│   ├── research/         # Research articles and curations
│   ├── news/             # News aggregation and commentary
│   ├── services/         # Consulting offerings
│   ├── products/         # Products and offerings (structure from day one)
│   └── projects/         # Portfolio / case studies
├── themes/
│   └── livingsystems/    # Custom theme (owned, not third-party)
├── static/               # Images, assets
├── config.toml           # Hugo configuration
├── deploy.sh             # Deployment script (rsync to WHC)
└── .github/              # Optional: GitHub Actions for backup builds
```

**Content is king.** The `content/` directory is the irreplaceable asset. Everything else (theme, config, tooling) is replaceable. If Hugo dies tomorrow, those Markdown files work with Eleventy, Astro, or any future tool. If WHC goes away, the Git repo deploys to any host.

### 3.4 Design Approach

Start with a clean, professional Hugo theme that reflects the values of the work — ecological, thoughtful, not corporate-generic. The site should feel like a living document, not a brochure.

Phase 1 ships with a modified open-source Hugo theme (several excellent ones exist for this aesthetic). Phase 2 evolves into a custom theme as Magi gains proficiency. This avoids blocking launch on design perfection.

---

## 4. Implementation Phases

### Phase 0: Infrastructure (Week 1)

**Prerequisites — before Magi builds anything:**

- [ ] Update OpenClaw to v2026.2.21+ (verify no regressions first)

- [ ] Install Chrome/Chromium on Metacarcinus (required for browser tool / visual testing)

- [ ] Set up Git for Magi — separate repo for [livingsystems.earth](http://livingsystems.earth/) under shared terrain (confirmed — see CONTRACT (OpenClaw Deployment) §3.1)

- [ ] Configure SSH keys on Metacarcinus for GitHub push access

- [ ] Install Hugo on Metacarcinus (`brew install hugo`)

- [ ] Configure OpenRouter as unified model gateway (all models routed through OpenRouter)

- [ ] Verify Gemini 3.1 Pro and Sonnet 4.5 work for interactive tasks via messaging channel

- [ ] Complete Priority 3 (exec approvals with messaging channel forwarding)

- [ ] Select messaging channel for Magi command interface (Slack, Telegram, Discord, or other OpenClaw-supported channel)

- [ ] Provision or confirm WHC hosting plan with SSH/SFTP access

- [ ] Configure deploy credentials (SSH key or SFTP) on Metacarcinus

**Estimated effort:** 1 session of configuration work with Magi verification.

### Phase 1: Scaffold + Ship (Weeks 2–3)

**Goal:** A live site at livingsystems.earth with foundational pages.

Magi's tasks:

- Initialize Hugo project in workspace

- Select and customize a base theme

- Create foundational content pages (About, Services, Contact, initial Research page)

- Configure Hugo build pipeline

- Write and test deployment script

- Deploy to WHC

- Set up cron job for periodic link-check and build verification

- Report deployment status to messaging channel

- Implement email capture mechanism (newsletter signup) — the lead funnel foundation

**Content Jedidiah provides:**

- Bio and professional narrative

- Service offerings and descriptions

- Initial vision statement for the site

- Brand preferences (colors, tone, reference sites)

**Note:** The full lead funnel architecture develops in later phases as offerings crystallize, but the site structure (including `products/` content section and email capture) must accommodate this commercial dimension from day one.

**Deliverable:** Live, functional site with email capture. Simple but professional. Proves the autonomous build-deploy loop works.

### Phase 2: Content Engine (Weeks 4–8)

**Goal:** Magi autonomously researches and publishes content.

- Implement a content cron job: Magi researches topics in regenerative systems, ecological restoration, traditional ecological knowledge, Indigenous land stewardship, Indigenous knowledge systems and their intersection with regenerative design, and AI + sustainability

- Draft articles as Markdown in the content pipeline

- Human review gate: Magi posts draft summaries to messaging channel, Jedidiah approves/requests edits before publish

- Approved content gets committed, built, and deployed

- Build a rolling research digest (weekly or bi-weekly)

- Add RSS feed for syndication

**This is the Wes Roth model applied:** scheduled research → content generation → Git commit → deploy → notification.

### Phase 3: Brain Stem Integration (Weeks 8–12)

**Goal:** Connect existing Brain Stem outputs to the site.

- Map Airtable content workspace outputs to Hugo-compatible Markdown

- Build a Make webhook (or direct script) that exports Brain Stem content to the Git repo

- Magi processes incoming content: formats, tags, categorizes, builds, deploys

- Establish the full loop: Capture (Slack/Brain Stem) → Process (Airtable/Make) → Publish (Magi/Hugo/WHC)

**This phase answers your cost concern about Brain Stem:** if the site becomes the publishing destination, Brain Stem's value proposition clarifies — it's the intake funnel, the site is the output. Pieces that don't justify their cost become visible.

### Phase 4: Autonomous Maintenance (Ongoing)

**Goal:** Magi independently maintains and improves the site.

- Scheduled security scans (dependency checks, link validation)

- Performance monitoring (build times, deploy success rates)

- Content freshness checks (flag stale pages)

- Theme and design iteration based on analytics

- Gradual expansion of autonomous permissions as trust builds

---

## 5. Cost Projection

### Monthly Operational Costs

| Item | Estimated Cost | Notes |
| --- | --- | --- |
| WHC hosting | C$4–8/month | Shared hosting, annual billing |
| OpenRouter — Gemini 3.1 Pro (research, code gen, drafting) | $5–16 USD/month | Primary model; includes ~5.5% OpenRouter markup |
| OpenRouter — Sonnet 4.5 (tool-use, exec ops, approvals) | $2–6 USD/month | Preferred for tool-heavy tasks; includes markup |
| OpenRouter — Gemini Flash (cron tasks) | $1–3 USD/month | Cheap background work; includes markup |
| OpenRouter — Haiku (heartbeat) | &lt;$0.10 USD/month | Fractions of a cent/day |
| GitHub | $0 | Free for public/private repos |
| Domain renewal | ~C$15–20/year | Already at WHC |

**Estimated total: C$15–40/month** (depending on content generation volume; includes ~5.5% OpenRouter markup across all models)

**Note:** Jedidiah's Gemini Pro retail subscription (paid through Oct 2026) does not offset these API costs — the subscription does not include API access. All API usage is billed through OpenRouter.

**Compared to current Brain Stem costs:** This should be substantially cheaper than Airtable + Make + Perplexity + multiple model API calls. The exact comparison depends on your current monthly spend, but the architecture is designed to minimize ongoing costs.

### One-Time Setup Costs

| Item | Cost |
| --- | --- |
| OpenClaw update + config | $0 (time only) |
| OpenRouter configuration | $0 (existing account) |
| Hugo installation | $0 |
| WHC hosting setup | C$0–50 (depending on plan) |
| GitHub repo | $0 |

---

## 6. Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Gemini 3.1 underperforms on code gen vs Anthropic models | Medium | Medium | Sonnet fallback configured; test during Phase 0 |
| OpenClaw update breaks existing setup | Low-Medium | High | Pin and wait; test in isolated session first |
| WHC SSH/deploy limitations on shared hosting | Low | Medium | Test deploy path before building content |
| Metacarcinus thermal issues under sustained agent work | Low | Medium | Thermal monitoring (Priority 9); Hugo builds are light |
| Content quality from autonomous generation | Medium | Medium | Human review gate in Phase 2; never auto-publish |

### Strategic Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Scope creep — site becomes endless project | Medium | High | Ship Phase 1 minimal; iterate in defined phases |
| Model landscape shifts (Gemini 3.2, new players) | High | Low | Architecture is model-agnostic; swap providers trivially |
| Hugo falls out of favor | Low | Low | Content is Markdown; migration to any SSG is straightforward |
| WHC service changes | Low | Low | Git repo is canonical; redeploy anywhere |

---

## 7. Success Criteria

### Phase 0 Complete When:

- OpenClaw updated and Gemini 3.1 verified working via OpenRouter

- Full deploy pipeline tested (local build → WHC)

- Exec approvals operational via selected messaging channel

- Messaging channel selected and configured

- Chrome/Chromium installed and browser tool verified

### Phase 1 Complete When:

- livingsystems.earth resolves to a live Hugo site

- At least 4 content pages published

- Email capture mechanism (newsletter signup) functional

- Magi can build and deploy via messaging channel command or cron

- Deployment succeeds 3 consecutive times without intervention

### Phase 2 Complete When:

- Magi has autonomously researched and drafted 5+ articles

- Human review → approve → publish loop working via messaging channel

- Content publishing cadence established (weekly minimum)

### Overall Project Success:

- livingsystems.earth is live, professional, and regularly updated

- Monthly operational cost under C$35

- Magi operates with minimal daily oversight

- Site demonstrates capability for consulting prospects

- Architecture documented well enough that technology components can be swapped without content loss

---

## 8. Decision Points for Jedidiah

Status of decisions as of Feb 27 advisory session:

1. ✅ **WHC confirmed as host.** Codified in CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §4.1. Scaling path in §4.3.

1. ✅ **Hugo confirmed as SSG.** Codified in CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §3.1.

1. **Site scope for Phase 1** — business presence only, or include research/news from launch? *(Still open — not yet codified in contract)*

1. **Content voice and brand** — Magi will need guidance on tone, visual identity, and the narrative arc of the site. What reference sites feel right? *(Still open — not yet codified in contract)*

1. ✅ **OpenRouter confirmed as unified model gateway.** Codified in CONTRACT (OpenClaw Deployment) §4.1. Routing table in §4.2 (including Opus 4.6 for perspective resets).

1. ⏳ **Messaging channel selection** — deferred to Phase 0. Channel-agnostic principle codified in CONTRACT (OpenClaw Deployment) §5.1. Current default: Slack.

1. **GitHub repository visibility** — public or private? *(Still open — not yet codified in contract)*

1. ✅ **Git repo strategy** — separate repos under shared terrain. Codified in CONTRACT (OpenClaw Deployment) §3.1 and CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §3.3.

---

## 9. Relationship to Existing Architecture

This plan has been codified into a contract hierarchy:

**CONTRACT (Hub)** → **CONTRACT (OpenClaw Deployment)** → **CONTRACT (**[**livingsystems.earth**](http://livingsystems.earth/)**)**

- **CONTRACT (Hub)** — workspace-wide governance, invariants, edit privileges, change control

- **CONTRACT (OpenClaw Deployment)** — platform-level rules: open service stack architecture, model routing (including Opus 4.6), OpenRouter gateway, channel-agnostic messaging, exec approvals, scaling philosophy, design values, security posture

- **CONTRACT (**[**livingsystems.earth**](http://livingsystems.earth/)**)** — project-level rules: Hugo + flat files, WHC green hosting, content strategy, human review gate, lead funnel, Brain Stem integration, phase boundaries, cost targets

The open service stack architecture — where Magi connects to replaceable services through open protocols (MCP, REST, webhooks, CLI, CDP) — is codified in CONTRACT (OpenClaw Deployment) §2. The site is a downstream output channel, not a governance disruption.

---

## 10. Next Steps

1. ✅ ~~Create Notion project page for ~~[~~livingsystems.earth~~](http://livingsystems.earth/) — created as [Livingsystems.earth](http://livingsystems.earth/) Web Deployment

1. ✅ ~~Create CONTRACT (OpenClaw Deployment)~~ — v0.1.0, 13 sections, codifies platform rules

1. ✅ ~~Create CONTRACT (~~[~~livingsystems.earth~~](http://livingsystems.earth/)~~)~~ — v0.1.0, 13 sections, codifies project rules

1. **Begin Phase 0 infrastructure work** in next Magi session — Phase 0 criteria defined in CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §9

1. **Jedidiah provides initial content brief** (bio, services, brand direction) — required for Phase 1 per CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §5.4

1. **Resolve remaining open decisions:** Phase 1 content scope, brand voice, GitHub repo visibility (see §8 above)
