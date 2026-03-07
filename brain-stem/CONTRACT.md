# CONTRACT (Brain Stem)

```yaml
---
doc_id: "contract_brain_stem"
last_updated: "2026-03-07"
contract_version: "0.4.0"
parent_contract: "contract_hub"
---
```

**Status:** Live

### Metadata (operational)

- **Owner:** Jedidiah Duyf

- **Notion source:** [Brain Stem Contracts](https://www.notion.so/3f24933e570a4de58ee0c55c6be56775)

- **Mirror repo:** brainstem-docs

- **Implementation state:** phase_2

- **Last mirror sync:** 

- **Last QA run:** 

- **Last known good commit:** 

- **Last change:** v0.4.0 — §2 added Supabase/Open Brain as external dependency. §3b added Semantic Memory provider row. §3.5 added Memory Interface definition. §13 updated Phase 1 and Phase 2 implementation state to reflect Open Brain HTTP modules. Reconciliation of as-built Open Brain write path across 12 Make modules.

---

## 1. Purpose

Brain Stem is a **capture, classification, and publishing system** that transforms Slack messages into structured records across multiple Airtable tables (People, Projects, Ideas, Admin, Events), enriches content via research APIs, synthesizes drafts, and publishes to multiple platforms.

**Core capability:** Touchless transformation from thought → structured data → published content.

---

## 2. Scope & Boundaries

**In scope:**

- Slack message capture (#brain-stem channel)

- Prefix-based routing (PRO, BD, CAL, R, fix)

- Claude-based classification and extraction

- Airtable record management

- Research enrichment via Perplexity

- Content synthesis and publishing

- Semantic memory write path (Open Brain via Supabase Edge Function)

**Out of scope:**

- Account provisioning

- User authentication (uses existing Slack workspace)

- Direct database access (all via Airtable API)

- Real-time collaboration

**External dependencies:**

- Slack (ingress)

- [Make.com](http://make.com/) (orchestration)

- Claude API (intelligence)

- Perplexity API (research)

- Airtable (storage)

- Supabase + Open Brain (semantic memory — write path via Edge Function)

---

## 3. System Architecture

### 3a. Functional Pipeline

Brain Stem processes information through six abstract stages. Each stage defines *what* happens, not *how* or *who* provides it.

- **Capture** — Accepts unstructured input from a messaging source and produces a raw event record.

- **Classification** — Analyzes raw input text to determine destination entity and confidence score.

- **Extraction** — Derives structured fields from input text for the target entity type.

- **Enrichment** — Augments stored records with external research and contextual data.

- **Synthesis** — Combines captured records and research into publication-ready drafts.

- **Publishing** — Formats and delivers content to one or more output platforms.

- **Metrics** — Collects engagement and performance data from published outputs.

**Pipeline flow (provider-agnostic):**

```javascript
Capture → Classification → Extraction → Storage → Enrichment → Synthesis → Publishing → Metrics
```

*Note: Classification and Extraction may be performed in a single invocation. The pipeline stages are logical, not necessarily separate calls.*

### 3b. Current Provider Mapping

The following table maps each functional stage to its current provider. This mapping is **configuration, not architecture** — providers are swappable at each boundary.

| **Functional Stage** | **Current Provider** | **Auth Method** |
| --- | --- | --- |
| Capture | Slack | Webhook + signing secret |
| Orchestration | [Make.com](http://make.com/) | Scenario runner (internal) |
| Intelligence (Classification + Extraction) | Claude API | API key |
| Research (Enrichment) | Perplexity API | API key |
| Storage | Airtable | Personal Access Token |
| Publishing | TBD per platform | TBD |
| Metrics | TBD per platform | TBD |
| Semantic Memory | Supabase Edge Function (Open Brain) | x-brain-key header |

**Trust boundaries (provider-specific):**

- Slack → [Make.com](http://make.com/): webhook + signing secret verification

- [Make.com](http://make.com/) → Claude / Perplexity: API key authentication

- [Make.com](http://make.com/) → Airtable: Personal Access Token

- Publishing channels: TBD per platform

- [Make.com](http://make.com/) → Supabase Edge Function: x-brain-key header (fire-and-forget)

---

## 3.5 Interface Definitions

Each boundary in the pipeline has a named interface that defines the data shape crossing it. These definitions are **provider-agnostic** — they describe what crosses the boundary, not which service implements it. For route-specific details and full LLM output schemas, see §7 (Route Semantics) and §8 (LLM Contracts).

### Capture Interface

**Boundary:** External messaging source → Pipeline entry

**Input (from capture source):**

- `text` (string, non-empty after trim) — raw message content

- `timestamp` (string) — source-native timestamp

- `channel` (string) — source channel or context identifier

- `user` (string) — source user identifier

- `thread_id` (string, optional) — thread or reply context

**Output (to Classification):**

- `original_text` (string) — preserved verbatim, immutable after capture

- `clean_text` (string) — prefix stripped, whitespace trimmed

- `detected_prefix` (string | null) — one of PRO, BD, CAL, R, fix, or null

- `captured_at` (ISO-8601 datetime)

- `source_metadata` (object) — channel, user, timestamp, thread_id

### Classification Interface

**Boundary:** Capture output → Intelligence layer

**Input:**

- `clean_text` (string) — prefix-stripped input

**Output:**

- `destination` (string) — one of: people, projects, ideas, admin, events, needs_review

- `confidence` (number, 0.0–1.0)

- `data` (object) — structured fields for the destination entity (see §8 for per-route schemas)

- `reason` (string) — explanation of classification decision

**Gating rule:** confidence ≥ 0.60 → auto-file; confidence < 0.60 → route to needs_review.

*Note: For prefix-routed messages (e.g., PRO:), destination is predetermined and classification is skipped. The Extraction Interface is used directly.*

### Extraction Interface

**Boundary:** Capture output → Intelligence layer (when destination is known)

**Input:**

- `clean_text` (string) — prefix-stripped input

- `destination` (string) — predetermined target entity type

**Output:**

- Structured fields matching the destination entity schema (see §8 for per-route output schemas)

- `reason` (string) — explanation of extraction decisions

*Note: Classification and Extraction may be performed in a single invocation. The BD route combines both; the PRO route uses Extraction only. These are logical interfaces, not necessarily separate calls.*

### Storage Interface

**Boundary:** Intelligence layer output → Persistent storage

**Input:**

- `destination` (string) — target table name

- `fields` (object) — structured fields matching the destination entity schema (see §9 for table definitions)

- `inbox_log_data` (object) — original_text, confidence, status, source_metadata, AI output raw

**Output:**

- `record_url` (URL) — link to the created or updated record

- `record_id` (string) — storage-native record identifier

- `status` (string) — resulting status (Filed, Needs Review, Error)

**Invariant:** Every invocation of the Storage Interface must produce exactly one Inbox Log record (see §10).

### Enrichment Interface *(scaffolded — Phase 3+)*

**Boundary:** Stored records → Research layer

**Input:**

- `record_url` (URL) — reference to the record to enrich

- `query` (string) — research query derived from record content

**Output:**

- `results` (array of objects) — research findings with source, summary, relevance score

- `enriched_fields` (object) — additional fields to merge into the record

### Publishing Interface *(scaffolded — Phase 5+)*

**Boundary:** Synthesized content → Output platforms

**Input:**

- `content` (object) — draft with body text, metadata, and formatting hints

- `platform` (string) — target platform identifier

- `format_rules` (object) — platform-specific formatting constraints

**Output:**

- `publication_url` (URL) — link to the published content

- `platform_id` (string) — platform-native identifier

- `published_at` (ISO-8601 datetime)

### Memory Interface

**Boundary:** Pipeline destination routes → Semantic memory layer

**Trigger:** Fire-and-forget POST after each successful record creation (all destination routes including fix and PRO bypass).

**Input (to memory layer):**

- `text` (string) — concatenated fields relevant to the destination (e.g., name + context for People; name + next_action + notes for Projects)

- `source` (string) — `"brain_stem"` (primary/PRO routes) or `"brain_stem_fix"` (fix routes)

- `destination` (string) — target entity type (people, projects, ideas, admin, events, needs_review)

- `confidence` (number, 0.0–1.0) — classification confidence (1.0 for PRO and fix routes)

- `classified_name` (string) — the name/title assigned by the classifier

- `record_id` (string, optional) — Airtable record ID of the created/updated record (absent for needs_review)

**Output:** None (fire-and-forget; response not parsed).

**Current provider:** Supabase Edge Function (`ingest-thought`)

**Auth:** `x-brain-key` header with MCP access key

**Endpoint:** `https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-thought`

**Note:** Backup/fallback array modules will be cloned from primary once primary routes are tuned and hardened.

---

## 4. Canonical Entities & Definitions

### Core Entities

**Inbox Log**

Audit record for every capture. Tracks original text, destination, confidence, status, AI output.

**Projects**

Active work with type (Digital/Physical/Hybrid), status, next action.

**People**

Relationship context, follow-ups, last touched.

**Ideas**

Concepts without immediate action, one-liner, notes.

**Admin**

Tasks with deadlines, to-do items.

**Events**

Meetings, appointments, calendar items.

### Prefixes

- **PRO:** — Guarantees destination=Projects with confidence 1.0; still calls Claude for field extraction

- **BD:** — Brain dump, routes to classification

- **CAL:** — Calendar/Events (scaffolded, Phase 4)

- **R:** — Research request (scaffolded, Phase 3)

- **fix:** — Correction/refile (scaffolded, Phase 2)

### Status Values

**Inbox Log statuses:**

- Processing

- Filed

- Needs Review

- Error

- Fixed

**Project statuses:**

- Active

- Waiting

- Blocked

- Someday

- Done

---

## 5. Input Contracts

### Slack Event Payload

**Required fields:**

- `event.text` (string, non-empty after trim)

- `event.ts` (string, Slack timestamp)

- [`event.channel`](http://event.channel/) (string, channel ID)

- `event.user` (string, user ID)

**Optional fields:**

- `event.thread_ts` (string, if threaded reply)

**Validation:**

- Reject empty text after trimming

- Reject missing required fields

---

## 6. Normalization Contracts

### Derived Fields

**clean_text**

- Strip prefix (PRO:, BD:, CAL:, R:, fix:)

- Trim whitespace

- Never mutates original `event.text`

**Timestamps**

- `Captured At`: ISO-8601 timestamp when Inbox Log created

- `Last Touched`: Auto-set by [Make.com](http://make.com/) on record creation/update

---

## 7. Route Semantics

### Route Decision Logic

1. **Prefix match** → Determines route

1. **Confidence gating** → Auto-file (≥0.60) vs Needs Review (<0.60)

1. **Fallback** → No prefix or BD: prefix → Classification route

### PRO Route (Projects Extraction)

Trigger: Message starts with PRO: Destination: Projects table Confidence: 1.0 (fixed) Intelligence: Claude extraction-only for structured fields (no classification needed) Implementation: Phase 1

Note: PRO runs extraction-only (no classification), then auto-files to Projects with confidence 1.0.

### BD Route (Classification)

- **Trigger:** Message starts with `BD:` OR no recognized prefix

- **Destination:** Determined by Claude (People/Projects/Ideas/Admin/Events/Needs Review)

- **Confidence:** Returned by Claude (0.0-1.0)

- **Intelligence:** Claude classification + extraction

- **Implementation:** Phase 1

### CAL Route (Events)

- **Trigger:** Message starts with `CAL:`

- **Destination:** Events table

- **Implementation:** Scaffolded (Phase 4)

### R Route (Research)

- **Trigger:** Message starts with `R:`

- **Destination:** Research Jobs table

- **Implementation:** Scaffolded (Phase 3)

### fix Route (Corrections)

- **Trigger:** Threaded reply starts with `fix:`

- **Destination:** Updates original Inbox Log + refiling

- **Implementation:** ✅ Live (Phase 2) — fix: handler operational across all 5 destination routes with original record deletion, re-extraction via Claude, Inbox Log update, linked record management, and Slack confirmation. Conditional typed-field PATCHes on main and fix routes.

---

## 8. LLM Contracts

### PRO Route: Projects Extraction

**Prompt ID:** `projects_extract_v1`

**Input schema:**

- `clean_text` (string, prefix stripped)

**Output schema (JSON only, no markdown):**

```json
{
  "name": "string|null",
  "type": "digital|physical|hybrid|null",
  "status": "active|waiting|blocked|someday|done|null",
  "next_action": "string|null",
  "notes": "string|null",
  "tags": ["string"],
  "reason": "string"
}
```

**Error modes:**

- Empty message → Return nulls + reason

- Ambiguous type → Default to "digital"

- Missing fields → Use null + explain in reason

### BD Route: Classification + Extraction

**Prompt ID:** `brain_dump_classifier_v1`

**Input schema:**

- `clean_text` (string, prefix stripped) — injected via `21.clean_text` Make pill

- `now` — Make pill resolving to current date/time (used for relative date conversion)

**System prompt (authoritative — module 48):**

```plain text
You are a classification assistant for a creative professional's Brain Stem system.

**CONTEXT:**
The user is a multimedia creator working across print, video, presentations, and physical installations. Their work focuses on:
- AI and creativity
- Sustainable design and regenerative systems
- Human-AI collaboration
- Traditional ecological knowledge integrated with modern technology
- Speculative futures

They publish on LinkedIn (thought leadership), Substack (long-form essays), personal blog (portfolio/process), and create physical exhibition documentation.

**YOUR TASK:**
Classify the following brain dump into ONE of these categories:

1. **PEOPLE** - Mentions a person by name, includes contact info, describes relationship context, or notes follow-up actions with someone
2. **PROJECTS** - Active work with status, executable next action, blocked/waiting dependencies, or project-specific notes
   - **Digital projects:** Keywords like 'article', 'video edit', 'website', 'script', 'blog post', 'social media'
   - **Physical projects:** Keywords like 'installation', 'exhibition', 'fabrication', 'gallery', 'sculpture', 'build'
   - **Hybrid projects:** Contains both digital and physical keywords
3. **IDEAS** - Concepts without immediate action, brainstorms, inspiration, "someday/maybe" thoughts, creative directions
4. **ADMIN** - Tasks with deadlines, administrative to-dos, one-time action items, personal errands
5. **EVENTS** - Meetings, appointments, deadlines with time, calendar-based reminders, scheduled gatherings

**EDGE CASES:**
- **Empty message or only whitespace:** Set destination to "needs_review", confidence 0.0, reason "Empty message"
- **Non-English message:** Attempt classification, but if uncertain, set destination to "needs_review", confidence below 0.60, reason "Non-English content requires manual review"
- **Image/attachment only (no text):** Set destination to "needs_review", confidence 0.0, reason "No text content to classify"
- **Multiple distinct items:** Set destination to "needs_review", confidence below 0.60, reason "Contains multiple topics requiring separate captures"

**OUTPUT FORMAT (raw JSON with no code block formatting):**

{"destination": "people|projects|ideas|admin|events|needs_review", "confidence": 0.85, "data": {"name": "Clear, descriptive title", "context": "For PEOPLE: relationship and interaction notes", "follow_ups": "For PEOPLE: specific next actions with this person", "status": "For PROJECTS: active|waiting|blocked|someday|done", "next_action": "For PROJECTS: Specific executable action", "notes": "For PROJECTS/IDEAS/EVENTS: Additional context", "one_liner": "For IDEAS: Core insight in one sentence", "due_date": "For ADMIN/EVENTS: YYYY-MM-DD or null", "start_time": "For EVENTS: YYYY-MM-DDTHH:MM:SS.000Z UTC, infer timezone as America/Vancouver today's date is now and convert, or null", "end_time": "For EVENTS: YYYY-MM-DDTHH:MM:SS.000Z UTC, infer timezone as America/Vancouver today's date is now and convert, or null", "attendees": "For EVENTS: comma-separated names or null", "location": "For EVENTS: location name or null", "tags": ["relevant", "tags"], "project_type": "digital|physical|hybrid (based on keywords above)"}, "reason": "Brief explanation of why this classification and confidence score"}

**CONFIDENCE SCORING RULES:**
- 0.85-1.0: Very clear classification, all key info present
- 0.70-0.84: Clear classification, some ambiguity or missing details
- 0.60-0.69: Reasonable classification, notable uncertainty
- Below 0.60: Route to "needs_review" - too ambiguous or contains multiple distinct items

**BRAIN DUMP TO CLASSIFY:**
21.clean_text
```

**Output schema (JSON only, no code fences):**

```json
{
  "destination": "people|projects|ideas|admin|events|needs_review",
  "confidence": 0.85,
  "data": {
    "name": "string",
    "context": "string (for People)",
    "follow_ups": "string (for People)",
    "status": "string (for Projects)",
    "next_action": "string (for Projects)",
    "notes": "string",
    "one_liner": "string (for Ideas)",
    "due_date": "YYYY-MM-DD|null (for Admin/Events)",
    "start_time": "YYYY-MM-DDTHH:MM:SS.000Z|null (for Events, UTC)",
    "end_time": "YYYY-MM-DDTHH:MM:SS.000Z|null (for Events, UTC)",
    "attendees": "string|null (for Events, comma-separated)",
    "location": "string|null (for Events)",
    "tags": ["string"],
    "project_type": "digital|physical|hybrid"
  },
  "reason": "string"
}
```

**Edge case handling (built into prompt):**

- Empty/whitespace → `needs_review`, confidence 0.0

- Non-English → attempt classification, `needs_review` if confidence < 0.60

- Image/attachment only → `needs_review`, confidence 0.0

- Multiple distinct items → `needs_review`, confidence < 0.60

**Confidence rules:**

- 0.85-1.0: Very clear, all key info present

- 0.70-0.84: Clear, some ambiguity or missing details

- 0.60-0.69: Reasonable, notable uncertainty

- <0.60: Route to `needs_review`

**Make pills:** `21.clean_text` (prefix-stripped input), `now` (current datetime for relative date resolution)

---

## 9. Data Contracts

### Inbox Log Table

**Fields:**

- Original Text (Long text)

- Filed To (Single line text)

- Confidence (Number, 0.0-1.0)

- Status (Single select: Processing, Filed, Needs Review, Error, Fixed)

- Slack Channel (Single line text)

- Slack Message TS (Single line text)

- Slack Thread TS (Single line text)

- Captured At (Date)

- Destination Name (Single line text)

- Destination URL (URL)

- AI Output Raw (Long text)

- Error Details (Long text)

### Projects Table

**Fields:**

- Name (Single line text)

- Type (Single select: Digital, Physical, Hybrid)

- Status (Single select: Active, Waiting, Blocked, Someday, Done)

- Next Action (Long text)

- Notes (Long text)

- Last Touched (Date)

- Tags (Multiple select)

### People Table

**Fields:**

- Name (Single line text)

- Context (Long text)

- Follow-ups (Long text)

- Last Touched (Date)

- Tags (Multiple select)

### Ideas Table

**Fields:**

- Name (Single line text)

- One-Liner (Long text)

- Notes (Long text)

- Last Touched (Date)

- Tags (Multiple select)

### Admin Table

**Fields:**

- Name (Single line text)

- Due Date (Date)

- Status (Single select: Todo, In Progress, Done)

- Notes (Long text)

- Created (Date)

### Events Table

**Fields:**

- Title (Single line text)

- Start Time (Date)

- End Time (Date)

- Attendees (Long text)

- Location (Single line text)

- Event Type (Single select: Meeting, Deadline, Appointment)

- Notes (Long text)

- Created (Date)

---

## 10. Invariants & Validation Rules

*See: Invariants & Checks (Brain Stem)*

---

## 11. Security & Redaction Rules

**Never publish in Git mirror or public docs:**

- Slack webhook URLs (inbound endpoints)

- API keys, tokens, credentials

- Airtable Base IDs, Table IDs (treat as sensitive metadata)

- Slack signing secrets

- Personal identifiers

**Placeholder format:** `<<PLACEHOLDER_NAME>>`

**Registry:** Every placeholder must be documented in Security & Placeholders page.

---

## 12. Observability & Error Handling

### Logging Requirements

- Every capture creates Inbox Log record

- Status transitions tracked (Processing → Filed/Needs Review/Error)

- AI Output Raw stored for debugging

- Error Details captured on failures

### Error Handling

- Claude API failure → Update Inbox Log with Error status, alert in Slack

- Airtable write failure → Log error, preserve original message

- Empty message → Route to Needs Review with confidence 0.0

---

## 13. Implementation State

**Phase 0:** Setup & Configuration — *Complete*

- [Slack] Webhook configured (§5 Input Contracts)

- [Airtable] Tables created (§9 Data Contracts)

- [[Make.com](http://make.com/)] Connections established (§3b Current Provider Mapping)

- [Claude] API integration configured (§3b)

- [Perplexity] API integration configured (§3b)

**Phase 1:** Brain Dump Capture — *Complete*

- [[Make.com](http://make.com/)] PRO route: Extraction working — guarantees Projects destination, Claude extracts fields (§7 PRO Route, §3.5 Extraction Interface)

- [[Make.com](http://make.com/)] BD route: Classification + extraction working (§7 BD Route, §3.5 Classification Interface)

- [Airtable] Inbox Log and all destination table writes operational (§9, §10, §3.5 Storage Interface)

- [Supabase] Open Brain write path: 7 fire-and-forget HTTP POST modules to `ingest-thought` Edge Function on primary BD routes (People, Projects, Ideas, Admin, Events, Needs Review off router 30) and PRO bypass route (§3.5 Memory Interface)

**Phase 2:** Classification & Routing — *Live as of Feb 26, 2026*

- [[Make.com](http://make.com/)] fix: handler operational across all 5 destination routes (People, Projects, Ideas, Admin, Events)

- Original record deletion, re-extraction via Claude, Inbox Log update (Status=Fixed), linked record management, Slack confirmation

- Conditional typed-field PATCHes on main BD routes and fix routes (dates, single selects)

- Unfurl prevention on all Slack reply modules

- Classifier prompt updated with date resolution (`now` pill)

- [Supabase] Open Brain write path: 5 fire-and-forget HTTP POST modules to `ingest-thought` Edge Function on fix routes (fix: People, fix: Projects, fix: Ideas, fix: Admin, fix: Events) (§3.5 Memory Interface)

- CAL, R routes: Still scaffolded (§7 Route Semantics)

- Deferred: Few-shot calibration, weekly misclassification digest, OpenRouter fallback, error handling on fix route

**Phase 3–9:** Not yet implemented

---

## 14. Deviation Log

*Tracks significant deviations, decisions, and rationale that led to contract changes. Not every patch-level edit needs an entry — only changes where the "why" matters for future reference.*

| **Version** | **Date** | **Description** |
| --- | --- | --- |
| 0.4.0 | 2026-03-07 | §2 added Supabase/Open Brain as external dependency (semantic memory write path). §3b added Semantic Memory provider row. §3.5 added Memory Interface definition (fire-and-forget POST to ingest-thought). §13 updated Phase 1 and Phase 2 with Open Brain module counts. Trust boundaries updated. Reconciliation of 12 as-built Make HTTP modules (7 primary/PRO + 5 fix routes). Minor version bump — new interface, additive only, no breaking changes. |
| 0.3.1 | 2026-03-05 | §8 BD classifier prompt reconciled to live module 48 — full prompt text now authoritative in contract (context block, edge cases, Events fields: start_time, end_time, attendees, location). §9 Events table schema updated to match as-built (Title not Name, added Start Time, End Time, Attendees, Location). Patch bump — no interface changes, documentation reconciliation only. |
| 0.3.0 | 2026-03-03 | §13 updated to as-built: Phase 1 marked Complete, Phase 2 marked Live (fix: handler, typed-field guards, unfurl prevention). §7 fix route updated from Scaffolded to Live. Minor version bump — no interface changes, additive status update only. |
| 0.2.0 | 2026-02-22 | §3 split into Functional Pipeline (§3a) + Provider Mapping (§3b). §3.5 Interface Definitions added. §15 Change Control expanded with version bump rules and downstream sync deadline. Formerly MOD-005. |
| 0.1.0 | 2026-02-18 | Initial contract. Pipeline architecture, route semantics, data contracts, LLM contracts, invariants. Adopted v0.2.0 structural standard (YAML headers, §-numbering). Formerly MOD-001. |

---

## 15. Change Control Protocol

**Rule:** Contract defines *what must be true everywhere*. Phase docs define *how it's done here*.

### 15.1 Version Bump Rules

The `contract_version` field in the YAML header follows semantic versioning:

- **Patch (0.0.x):** Clarifications, typo fixes, no interface changes. Downstream docs are unaffected.

- **Minor (0.x.0):** New route, new field, new interface added — backward compatible. Existing interfaces unchanged; downstream docs may need additive updates.

- **Major (x.0.0):** Interface shape change, removed field, breaking change to downstream docs. All downstream docs in the impact radius must be updated or marked stale.

### 15.2 Change Tracking

This contract is its own source of truth for change history. The `contract_version` in the YAML header tracks the current version. Notion's page version history provides the full diff timeline. Significant deviations and decisions are logged in §14 (Deviation Log).

### 15.3 Impact Radius

Every CONTRACT or spec change must consider which downstream documents are affected.

**Downstream docs for this contract:** contracts/spec, Phase docs, Invariants & Checks, Architecture & Flows.

### 15.4 Forward Path (Design → Implementation)

1. Bump `contract_version` and `last_updated` in YAML header

1. Update CONTRACT + spec.yaml

1. Update affected Phase docs (per impact radius)

1. Implement in Make/Airtable

1. Add/update invariants

1. Mark implementation state in CONTRACT §13

1. Log entry in §14 Deviation Log if the change is significant

### 15.5 Reverse Path (Discovery → Reconcile)

1. Document deviation in §14 Deviation Log

1. Decide if contract-worthy

1. If yes: bump version, update CONTRACT + spec.yaml, then reconcile Phase docs per impact radius

### 15.6 Downstream Sync Deadline

After a CONTRACT or spec change is applied, all downstream docs in the impact radius must be updated **in the same work session**.

If a downstream doc cannot be updated in the same session, add this banner at the top of the affected page:

`⚠️ STALE — see [version]`

**Rules:**

- The banner must reference the contract version that triggered the staleness.

- Staleness banners are removed **only** when the doc is reconciled with the current `contract_version`.

---

## 16. Appendix

### Related Documents

- contracts/spec (Brain Stem)

- Invariants & Checks (Brain Stem)

- [Phase 0: Setup & Configuration](https://www.notion.so/ed998ca8e6464de188987fbf06e30568)

- [Phase 1: Brain Dump Capture](https://www.notion.so/0538979e023a46528fb1a70b60ccd4ef)

- [Phase 2: Classification & Routing](https://www.notion.so/548d362076b243f1ad33df72fd6617a1)

- [Brain Stem Architecture & Flows](https://www.notion.so/8d45305a868d4e73a6555b9e96d53a18)

- [📊 Brain Stem Master Roadmap](https://www.notion.so/8806dfbe864f478bb2cce258073ac2d3)
