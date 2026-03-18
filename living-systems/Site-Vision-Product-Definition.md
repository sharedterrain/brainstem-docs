# livingsystems.earth — Site Vision & Product Definition

## What It Is

[livingsystems.earth](http://livingsystems.earth/) is a Hugo-based static site serving three functions:

- **Business presence** for Jedidiah's consulting work in regenerative systems, AI applications in ecology, traditional ecological knowledge (TEK), and Indigenous land stewardship

- **Research and editorial hub** curating and publishing content at the intersection of ecological restoration, regenerative design, AI + living systems, and speculative futures

- **Product gateway** housing the LCA Database (a public-facing Life Cycle Assessment data explorer) and future tools — the site structure accommodates commercial offerings from day one, with the funnel architecture developing as offerings crystallize

The site is also a **proof of concept** for agentic site building and maintenance — directly relevant to future consulting engagements. Magi researches, drafts, builds, commits, and deploys. The entire pipeline runs autonomously with human oversight.

## Who Reads It

**Primary audiences:**

- **Practitioners** — designers, architects, procurement teams, sustainability consultants looking for actionable ecological data and regenerative design guidance

- **Students and researchers** — people studying ecological restoration, TEK, or AI applications in environmental science

- **Consulting prospects** — organizations considering regenerative transitions who find the site through content or the LCA tool

- **General public** — sustainability-curious people who arrive via the LCA Database (the freemium lead-generation engine) and discover the broader content

The site speaks to people who are already interested in these domains or adjacent to them. It doesn't need to convert skeptics — it needs to be the best resource for people who are already looking.

## Content Domains

- Ecological restoration and regenerative systems

- Traditional ecological knowledge and Indigenous knowledge systems

- AI applications in living systems and ecological monitoring

- Life Cycle Assessment data and methodology (via the LCA Database)

- Regenerative design principles and case studies

- Speculative futures — where ecology, technology, and culture converge

## Editorial Model

**Magi researches and drafts. Jedidiah approves before anything publishes.**

The content pipeline works like this:

1. **Research** — Magi (via Perplexity tool calls and web search) identifies topics, gathers sources, and synthesizes research in the content domains above

1. **Draft** — Magi writes articles as Markdown in the Hugo content directory, following editorial voice guidelines

1. **Review gate** — Magi posts draft summaries to the messaging channel. Jedidiah reviews, approves, requests edits, or rejects. Nothing publishes without explicit human approval.

1. **Publish** — Approved content is committed to Git, built by Hugo, and deployed to Cloudflare Pages

1. **Brain Stem integration (Phase 3+)** — Brain Stem captures eventually feed into the content pipeline, with Magi processing incoming ideas into publishable content

**Jedidiah also publishes directly** — original writing, commentary, and consulting-related content authored by Jedidiah, formatted and deployed by Magi through the same Git → build → deploy pipeline.

The editorial voice is informed, serious, and accessible — not academic, not corporate. It treats readers as intelligent adults who don't need jargon decoded but do appreciate clarity.

## What v1 Looks Like Shipped

A visitor to [livingsystems.earth](http://livingsystems.earth/) sees:

- **Homepage** — clear articulation of what the site is, who Jedidiah is, and what's available

- **About** — professional narrative, philosophy, and the intersection of AI + ecological work

- **Services** — consulting offerings in regenerative systems and AI implementation

- **Field Notes** — research articles, curations, and commentary (minimum 4 pages at launch, growing via content engine)

- **LCA Database** — search, browse, and compare environmental impact data for materials and processes. Public datasets (USLCI, USDA LCA Digital Commons, TRACI). The LCA tool ships in parallel with site content, not deferred.

- **Email capture** — newsletter signup as the lead funnel foundation

- **RSS feed** — for syndication (added during content engine phase)

The site is clean, professional, and reflects the values of the work — ecological, thoughtful, not corporate-generic. It feels like a living document, not a brochure. Phase 1 ships with a custom Hugo theme (Forest Layer palette, Jost + Cormorant Garamond fonts, Tailwind CSS v4). The design evolves iteratively as the content matures.

## What's Decided

These are codified in contracts and are not open questions:

- **Hugo** as static site generator — CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §3.1

- **Cloudflare Pages** as host (free tier, CDN distribution, Git-native deploy) — CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) §4.1

- **Content as flat Markdown files in Git** — no CMS, no framework lock-in

- **Human approval gate on all publishing** — Magi drafts, Jedidiah approves via messaging channel

- **LCA Database as a feature module** — JS islands pattern, API-first, governed by child contract

- **Custom Hugo theme** — Forest Layer palette, Jost + Cormorant Garamond fonts, Tailwind CSS v4

- **Open service stack architecture** — providers are configuration, interfaces are architecture

- **Phase boundaries** — 0 (infrastructure) → 1 (scaffold + ship) → 2 (content engine + LCA pipeline) → 3 (LCA live + Brain Stem integration) → 4 (autonomous maintenance)

## Open Decisions

These need resolution before or during Phase 1:

- **Phase 1 content scope** — business presence only at launch, or include initial research/news content?

- **Content voice and brand** — tone partially resolved (Forest Layer palette, Jost + Cormorant Garamond fonts confirmed). Branding direction still open: three options generated (Mycelial, Topographic, Botanical Circuit) — not yet chosen.

- **GitHub repository visibility** — public or private?

- **LCA infrastructure platform** — where the API/data layer runs (flagged for a dedicated decision session)

## How It Fits in the Stack

[livingsystems.earth](http://livingsystems.earth/) is a downstream output of the Magi system:

- **Governed by** CONTRACT ([livingsystems.earth](http://livingsystems.earth/)) v0.3.0, which inherits from CONTRACT (OpenClaw Deployment)

- **Built by** Magi — the Sonnet coordinator handles site development directly, with Haiku executors for volume tasks (LCA data pipeline, bulk content transforms)

- **Fed by** Brain Stem (Phase 3+) — Brain Stem captures ideas and research topics that Magi processes into publishable content

- **Deployed to** Cloudflare Pages via Git push → auto-build → CDN distribution

The site is Magi's first shipped product. It proves the architecture works and establishes the consulting presence that justifies the broader system investment.
