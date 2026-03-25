# CONTRACT (Brain-Stem)

```yaml
---
doc_id: "contract_brain_stem"
last_updated: "2026-03-25"
contract_version: "0.7.0"
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

- **Last change:** v0.7.0 — §10 and §11 consolidated as single source of truth. Invariant definitions (INV-001–013) and validation checklist folded into §10. Security rules, scan patterns, and pre-publish checklist folded into §11. Child pages tombstoned.

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

- Supabase + Open Brain (semantic memory + research memory — write paths via Edge Functions; Research Brain is a table + dedicated Edge Function within the same Supabase project)

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
| Research Memory | Research Brain (`research_returns` table + `ingest-research` Edge Function within Open Brain Supabase project) | x-brain-key header — same credentials as Open Brain |

**Trust boundaries (provider-specific):**

- Slack → [Make.com](http://make.com/): webhook + signing secret verification

- [Make.com](http://make.com/) → Claude / Perplexity: API key authentication

- [Make.com](http://make.com/) → Airtable: Personal Access Token

- Publishing channels: TBD per platform

- [Make.com](http://make.com/) → Supabase Edge Functions (Open Brain `ingest-thought` + Research Brain `ingest-research`): x-brain-key header (fire-and-forget, same project, same credentials)

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

### Memory Interface (Open Brain)

**Scope:** This interface definition covers Open Brain writes from Make only (table: `thoughts`, function: `ingest-thought`). Research Brain uses a separate table and Edge Function within the same Supabase project (see Research Brain Memory Interface below).

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

**Note:** 24 total Make routes exist (12 live write modules + fix-delete routes + parked backup array). Backup/fallback array modules will be cloned from primary once primary routes are tuned and hardened.

### Research Brain Memory Interface

**Boundary:** Scenario B research runner → Research Brain semantic memory layer

**Trigger:** Fire-and-forget POST after each Article record creation in Scenario B (both sweep and job modes).

**Input (to Research Brain):**

- `text` (string) — Title + snippet from search result

- `url` (string) — Article URL from search result

- `source_domain` (string) — Parsed from URL

- `digest_run_id` (string) — Scenario B execution ID for traceability

- `research_job_id` (string) — Airtable Research Job or Domain record ID

- `published_date` (string) — From search result

- `source_tag` (string) — `"research_digest"` default

**Output:** None (fire-and-forget; response not parsed).

**Current provider:** Supabase Edge Function (`ingest-research`) — same Supabase project as Open Brain, dedicated Edge Function and table (`research_returns`)

**Auth:** `x-brain-key` header with same `MCP_ACCESS_KEY` as Open Brain

**Endpoint:** `https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-research`

**Dedup:** Partial unique index on `url + published_date` (WHERE NOT NULL). INSERT uses `ON CONFLICT DO NOTHING`. Duplicate = empty result set (not null id).

**Note:** Research Brain receives unfiltered volume from all research runs. Open Brain receives only deliberately promoted content (Phase 4-5). Both share the same Supabase project and credentials but use separate tables (`research_returns` vs `thoughts`) and separate Edge Functions (`ingest-research` vs `ingest-thought`). No semantic bleed risk — data isolation is at the table level.

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

- **R:** — Research request → Research Jobs table, fires Scenario B immediately (Phase 3)

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

- **Intelligence:** Perplexity (research provider, not Claude — no classification or extraction)

- **Behavior:** Creates Research Job record → Inbox Log record (INV-001) → fires Scenario B webhook (`mode: "job"`, record ID) → Slack in-thread confirmation. Scenario B runs the single job immediately, enriches articles via Claude end-of-run call, flags top 3 as Morning Pick.

- **Implementation:** Phase 3

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

{"destination": "people|projects|ideas|admin|events|needs_review", "confidence": 0.85, "data": {"name": "Clear, descriptive title", "context": "For PEOPLE: relationship and interaction notes", "follow_ups": "For PEOPLE: specific next actions with this person", "status": "For PROJECTS: active|waiting|blocked|someday|done", "next_action": "For PROJECTS: Specific executable action", "notes": "For PROJECTS/IDEAS/EVENTS: Additional context", "one_liner": "For IDEAS: Core insight in one sentence", "due_date": "For ADMIN/EVENTS: YYYY-MM-DD or null", "start_time": "For EVENTS: YYYY-MM-DDTHH:MM:SS.000Z UTC, infer timezone as America/Vancouver today's date is now and convert, or null", "end_time": "For EVENTS: YYYY-MM-DDTHH:MM:SS.000Z UTC, infer timezone as America/Vancouver today's date is now and convert, or null", "attendees": "For EVENTS: comma-separated names or null", "location": "For EVENTS: location name or null", "tags": ["relevant", "tags"], "project_type": "digital|physical|hybrid (based on keywords above)", "entity_type": "person|organization (for PEOPLE, omit for others)"}, "reason": "Brief explanation of why this classification and confidence score"}

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
    "project_type": "digital|physical|hybrid",
    "entity_type": "person|organization (for People)"
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

- Filed To (Single select: People, Projects, Ideas, Admin, Events)

- Destination Name (Single line text)

- Destination URL (URL)

- Confidence (Number, 0.0-1.0)

- Status (Single select: Processing, Filed, Needs Review, Error, Fixed)

- Slack Channel (Single line text)

- Slack Message TS (Single line text)

- Slack Thread TS (Single line text)

- Created (Created time, auto)

- AI Output Raw (Long text)

- Error Details (Long text)

- Linked People (Linked record → People)

- Linked Projects (Linked record → Projects)

- Linked Ideas (Linked record → Ideas)

- Linked Admin (Linked record → Admin)

- Destination Record ID (Single line text)

- Source (Single select: Slack)

- Source Link (URL)

### People Table

**Fields:**

- Name (Single line text)

- Context (Long text)

- Follow-Ups (Long text)

- Tags (Long text)

- Last Touched (Date)

- Source (Single select: Slack, Manual, Research)

- Source Link (URL)

- Inbox Router Log (Linked record → Inbox Log)

- Drafts (Linked record → Drafts)

- Events (Linked record → Events)

- Entity Type (Single select: Person, Organization)

### Projects Table

**Fields:**

- Name (Single line text)

- Type (Single select: Digital, Physical, Hybrid)

- Status (Single select: Active, Waiting, Blocked, Someday, Done)

- Next Action (Long text)

- Notes (Long text)

- Tags (Long text)

- Last Touched (Date)

- Source (Single select: Slack, Manual, Research)

- Source Link (URL)

- Inbox Router Log (Linked record → Inbox Log)

- Drafts (Linked record → Drafts)

### Ideas Table

**Fields:**

- Name (Single line text)

- One-Liner (Long text)

- Notes (Long text)

- Tags (Long text)

- Last Touched (Date)

- Source (Single select: Slack, Manual, Research)

- Source Link (URL)

- Inbox Router Log (Linked record → Inbox Log)

- Drafts (Linked record → Drafts)

### Admin Table

**Fields:**

- Name (Single line text)

- Due Date (Date)

- Status (Single select: Todo, Done)

- Notes (Long text)

- Tags (Long text)

- Created (Created time, auto)

- Source (Single select: Slack, Manual, Research)

- Source Link (URL)

- Inbox Router Log (Linked record → Inbox Log)

- Drafts (Linked record → Drafts)

### Events Table

**Fields:**

- Title (Single line text)

- Event Type (Single select: Meeting, Appointment, Deadline, Volunteering, Workshop)

- Start Time (Date)

- End Time (Date)

- Attendees (Long text)

- Location (Long text)

- Notes (Long text)

- Tags (Long text)

- Calendar Source (Single select: Google Calendar, Manual Entry, Slack)

- Source Link (URL)

- Calendar Sync Status (Single select: Synced, Pending, Failed, Not Synced)

- Inbox Log (Linked record → Inbox Log)

### Research Lens Table

**Fields:**

- Entry (Long text)

- Created (Date, auto)

- Active (Checkbox)

### Domains Table

**Fields:**

- Domain Name (Single line text)

- Prompt (Long text)

- Recency Window (Single select: 1d, 7d, 30d)

- Active (Checkbox)

- Last Run (Date)

- Next Run (Date)

- Last Run Summary (Long text)

### Research Jobs Table

**Fields:**

- Job Name (Single line text)

- Query (Long text)

- Active (Checkbox)

- Frequency (Single select: Custom, Daily)

- Recency Window (Single select: 1d, 7d, 30d — default 30d)

- Relevance Threshold (Number — inert Phase 3, future use)

- Include Domains (Long text)

- Exclude Domains (Long text — inert Phase 3, Perplexity allowlist only)

- Language/Region (Single line text)

- Run Now (Checkbox)

- Next Run (Date)

- Last Run (Date)

- Last Run Summary (Long text)

- Articles (Linked record → Articles)

### Articles Table

**Fields:**

- Title (Single line text)

- URL (Single line text)

- Source Domain (Single line text)

- Published Date (Date)

- Thumbnail (URL — deferred)

- Summary (Long text)

- Key Points (Long text)

- Category (Single select)

- Tags (Long text)

- Relevance Score (Number, 0.0–1.0)

- Why It Matters (Long text)

- Status (Single select: New, Reviewed, Saved, Dismissed, Use)

- Full Text (Long text)

- Citations (Long text — deferred)

- Dedup Key (Formula: URL + Published Date)

- Research Job (Linked record → Research Jobs)

- Domain (Linked record → Domains)

- Run ID (Single line text)

- Morning Pick (Checkbox)

- Drafts (Linked record → Drafts — Phase 4-5)

---

## 10. Invariants & Validation Rules

System invariants that must always hold true. This section is the **single source of truth** for all invariant definitions. Violations indicate drift between contract and implementation.

### INV-001: Inbox Log Singleton — Critical

**Rule:** Every capture yields exactly one Inbox Log record with matching `(SlackChannel, SlackMessageTS)`.

**Applies to:** Scenario A — all routes (BD, PRO, fix, R).

**Evidence:** Query Inbox Log for duplicate `(SlackChannel, SlackMessageTS)` keys.

**Note:** The R: handler creates an Inbox Log record at module ~304 in Scenario A (Status=Filed, Filed To=Research Jobs, Source Link=Slack permalink).

### INV-002: PRO Route Confidence — Warning

**Rule:** PRO route must set confidence to 1.0.

**Applies to:** PRO route.

**Evidence:** Query Inbox Log where `FiledTo = "Projects"` and `OriginalText` starts with `PRO:`.

### INV-003: Filed Status Has Destination — Critical

**Rule:** Inbox Log with Status=Filed must have non-empty DestinationName and DestinationURL.

**Applies to:** Scenario A — all routes.

**Evidence:** Query where `Status = "Filed"` and (`DestinationName` is empty OR `DestinationURL` is empty).

### INV-004: Confidence Range — Critical

**Rule:** Confidence must be between 0.0 and 1.0.

**Applies to:** BD route.

**Evidence:** Query Inbox Log where Confidence outside 0.0–1.0 range.

### INV-005: Original Text Immutable — Critical

**Rule:** OriginalText in Inbox Log must never be modified after creation.

**Applies to:** Scenario A — all routes.

**Evidence:** Version history audit (manual review).

### INV-006: Clean Text Derivation — Warning

**Rule:** `clean_text` variable must be derived from OriginalText via `replace()`, never from direct user input.

**Applies to:** Scenario A — all routes.

**Evidence:** Review Make module configuration for clean_text variable formula.

### INV-007: Slack Thread TS Consistency — Warning

**Rule:** If message is not threaded, SlackThreadTS should equal SlackMessageTS.

**Applies to:** Scenario A — capture.

**Evidence:** Verify capture module sets `SlackThreadTS = event.thread_ts` if present, else `event.ts`.

### INV-008: Auto-File Threshold — Warning

**Rule:** Messages with confidence >= 0.60 must auto-file; below 0.60 must route to Needs Review.

**Applies to:** BD route.

**Evidence:** Query Inbox Log for mismatches between Confidence and Status.

### INV-009: LLM Output JSON Only — Critical

**Rule:** LLM must return raw JSON without markdown code fences.

**Applies to:** BD, PRO, fix routes.

**Evidence:** Review AIOutputRaw in Inbox Log for markdown wrappers.

### INV-010: Projects Type Enum — Warning

**Rule:** Projects.Type must be one of: Digital, Physical, Hybrid.

**Applies to:** PRO, BD routes.

**Evidence:** Query Projects table for Type values not in the enum.

### INV-011: R: Route Inbox Log Before Scenario B — Critical

**Rule:** R: route must create Inbox Log record before triggering Scenario B webhook.

**Applies to:** R route.

**Evidence:** Module execution order in Scenario A R: branch (~304 before ~305).

### INV-012: Memory Push Fire-and-Forget — Warning

**Rule:** Memory push (Open Brain / Research Brain) is fire-and-forget — failure must not block primary pipeline.

**Applies to:** Scenario A, Scenario B.

**Evidence:** Verify HTTP modules have "Parse response: No" and no downstream error routes.

### INV-013: Domain/ResearchJob Mutual Exclusivity — Warning

**Rule:** Domain and ResearchJob links on Articles are mutually exclusive per record.

**Applies to:** Scenario B.

**Evidence:** Query Articles for records with both Domain and Research Job populated.

### Validation Checklist

**Manual checks (run before each phase completion):**

- [ ] Query Inbox Log for duplicate `(SlackChannel, SlackMessageTS)` keys (INV-001)

- [ ] Verify PRO route captures show Confidence = 1.0 (INV-002)

- [ ] Check Filed records have non-empty DestinationName and DestinationURL (INV-003)

- [ ] Validate all Confidence values are in 0.0–1.0 range (INV-004)

- [ ] Review Make modules: clean_text uses replace() on OriginalText (INV-006)

- [ ] Verify router filters use >= 0.60 for auto-file threshold (INV-008)

- [ ] Spot-check AIOutputRaw for markdown code fence wrappers (INV-009)

- [ ] Query Projects for Type values outside the enum (INV-010)

**Automated checks (future):**

- SQL queries against Airtable via API

- Contract drift detection (spec.yaml vs actual table schemas)

- Prompt version tracking (compare prompt IDs in spec vs deployed prompts)

---

## 11. Security & Redaction Rules

### Never Publish

The following must **never** appear in Git mirror or public documentation:

- **API keys, tokens, credentials** — Claude (`sk-ant-...`), Airtable (`pat...`), Perplexity (`pplx-...`), Notion (`secret_...`), OpenRouter, Supabase service role keys, MCP access keys

- **Inbound webhook URLs** — [Make.com](http://make.com/) (`hook.us2.make.com/...`), any endpoint callable without authentication

- **Signing secrets** — Slack signing secret, HMAC keys, verification tokens

- **Personal identifiers** — email addresses, phone numbers, physical addresses

- **Database identifiers** (sensitive metadata) — Airtable Base IDs (`app...`), Table IDs (`tbl...`), View IDs (`viw...`)

- **Connection strings** — database URLs, service endpoints with embedded authentication

### Placeholder Format

**Standard:** `<<PLACEHOLDER_NAME>>` — all caps, underscores, descriptive name. Self-documenting where they appear. No separate registry — the placeholder convention plus the scan patterns below are the enforcement layer.

### Automated Scan Patterns

Patterns that must trigger publish failure in the Git mirror pipeline:

```javascript
hook.make.com
hook.us1.make.com
hook.us2.make.com
Authorization: Bearer
sk-ant-
sk-
pat[0-9A-Za-z]{10,}
secret_
xoxb-
xoxp-
api.airtable.com/v0/app
app[A-Za-z0-9]{14}
tbl[A-Za-z0-9]{14}
viw[A-Za-z0-9]{14}
pplx-
BEGIN PRIVATE KEY
-----BEGIN
```

If any match found: block export, report match location, require manual review.

### Pre-Publish Checklist

- All tokens replaced with `<<PLACEHOLDER>>` pattern

- All inbound webhook URLs replaced with `<<MAKE_WEBHOOK_URL>>`

- No personal identifiers present

- All Airtable IDs replaced with appropriate placeholders

- Run automated pattern scan

- Manual skim for "looks like a secret" strings (long alphanumeric, base64-like)

- No "disable verification" or "skip authentication" instructions

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

### Operational: Supabase Edge Function Secret Caching

Supabase Edge Functions cache secrets at deploy time. This creates two failure modes for the Make → Supabase boundary:

1. **Secret rotation without redeploy** — After `supabase secrets set` (e.g. rotating `MCP_ACCESS_KEY`), all existing Edge Functions continue using the stale cached value. They must be explicitly redeployed to pick up the new secret.

1. **New deployment invalidates siblings** — Deploying anything new (a new Edge Function, a table migration, `supabase db push`, `supabase functions deploy`) refreshes secrets only for the function being deployed. If a secret was rotated between existing functions' last deploy and now, they silently break.

**Affected functions:** `ingest-thought`, `open-brain-mcp`, `ingest-research`, and Magi Brain equivalents.

**Symptom:** 401 Unauthorized on previously-working endpoints. Fire-and-forget pushes from Make fail silently (no error handling by design — §3.5 Memory Interface).

**Mitigation:** After any secret rotation or new function deployment, redeploy all Edge Functions in the affected Supabase project.

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

- CAL route: Still scaffolded (§7 Route Semantics)

- Deferred: Few-shot calibration, weekly misclassification digest, OpenRouter fallback, error handling on fix route

**Phase 3:** Research Pipeline — *Draft, pre-implementation*

- [Airtable] Domains table (standing domain configs), Research Lens table (free-text context for dynamic domain generation), Research Jobs table (ad-hoc R: queries)

- [Airtable] Articles table additions: Domain (linked → Domains), Run ID, Morning Pick

- [Supabase] Research Brain: `research_returns` table + `ingest-research` Edge Function within Open Brain Supabase project (same credentials), fire-and-forget write from Scenario B (§3.5 Research Brain Memory Interface)

- [[Make.com](http://make.com/)] Scenario B: webhook-triggered research runner. Supports two modes — sweep (all active Domains + Claude-generated slots 4–5 from Research Lens) and job (single Research Job, triggered by R: route or future consumers). The mode flag pattern is architecturally significant — a single scenario handles both scheduled and ad-hoc research via payload-driven branching.

- [[Make.com](http://make.com/)] Scenario C: daily cron (Schedule → webhook POST to Scenario B with `mode: "sweep"`)

- [[Make.com](http://make.com/)] R: prefix handler in Scenario A: creates Research Job → Inbox Log → fires Scenario B webhook (`mode: "job"`) → Slack confirmation (§7 R Route)

- [Claude] End-of-run enrichment: reviews all articles per run, populates Summary, Key Points, Why It Matters, Category, Tags, Relevance Score, Morning Pick (top 3)

- [Perplexity] Research provider: `sonar` model, `search_results[]` as iterator source, If-else/Merge provider routing for future additions

- Morning Pick flag on Articles = Phase 3 ↔ Phase 4-5 interface (Phase 3 sets, Phase 4-5 reads)

**Phase 4–9:** Not yet implemented

---

## 14. Deviation Log

*Tracks significant deviations, decisions, and rationale that led to contract changes. Not every patch-level edit needs an entry — only changes where the "why" matters for future reference.*

| **Version** | **Date** | **Description** |
| --- | --- | --- |
| 0.7.0 | 2026-03-25 | §10 and §11 consolidated as single source of truth. Full invariant definitions (INV-001–013) moved into §10 with validation checklist. Security rules, never-publish categories, and scan patterns moved into §11; placeholder registry table dropped. Both child pages (Invariants & Checks, Security & Placeholders) tombstoned. contracts/spec invariants renumbered (former INV-006–008 → INV-011–013) and converted to reference-only. Minor version bump — new invariants, structural consolidation, no interface changes. |
| 0.6.1 | 2026-03-25 | Research Brain as-built reconciliation. Spec called for a separate Supabase instance; implemented as a dedicated table (`research_returns`) + Edge Function (`ingest-research`) within the existing Open Brain Supabase project. Rationale: free tier limits 2 projects, no semantic bleed risk from separate table, same credential chain simplifies Make configuration. §3.5 endpoint corrected (`ingest-research` not `ingest-thought`, `<<SUPABASE_PROJECT_REF>>` not `<<RESEARCH_BRAIN_PROJECT_REF>>`). §11 removed two obsolete placeholders. §2, §3b, §13 updated throughout. Patch bump — no interface shape change, documentation reconciliation only. |
| 0.6.0 | 2026-03-24 | Phase 3 Research Pipeline additions. §9 added Domains, Research Lens, Research Jobs, Articles table schemas. §3.5 added Research Brain Memory Interface (separate write path from Open Brain — different payload schema, separate Supabase instance). §3b added Research Memory provider row. §7 R: route updated from scaffolded to Phase 3 implementation (Perplexity provider, not Claude). §10 INV-001 coverage explicitly extended to R: route. §11 added 7 security placeholders (Perplexity key, Research Brain credentials, 4 Airtable table IDs). §13 added Phase 3 scope definition including Scenario B mode flag pattern (sweep/job). Minor version bump — new tables, new memory instance, new route implementation, all additive. |
| 0.5.0 | 2026-03-19 | §9 Data Contracts reconciled to as-built Airtable schemas via column-level screenshot audit. Changes: Tags field corrected from Multiple select → Long text (all destination tables). Source (Single select) and Source Link (URL) added to all tables. Linked record fields added (Inbox Log ↔ destination tables, Drafts, Events on People). People: Follow-ups → Follow-Ups, added Entity Type (Person/Organization). Projects: no structural change beyond shared fields. Ideas: no structural change beyond shared fields. Admin: Status simplified to Todo/Done, added Tags. Events: Event Type expanded (added Volunteering, Workshop), Calendar Source replaces Source (Google Calendar/Manual Entry/Slack), added Calendar Sync Status, Location changed to Long text. Inbox Log: Filed To changed from text → Single select, Captured At → Created (auto), added Linked People/Projects/Ideas/Admin, Destination Record ID, Source, Source Link. Minor version bump — additive fields + type corrections, no interface shape changes. |
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

**Downstream docs for this contract:** contracts/spec, Phase docs, Architecture & Flows.

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

- [Phase 0: Setup & Configuration](https://www.notion.so/ed998ca8e6464de188987fbf06e30568)

- [Phase 1: Brain Dump Capture](https://www.notion.so/0538979e023a46528fb1a70b60ccd4ef)

- [Phase 2: Classification & Routing](https://www.notion.so/548d362076b243f1ad33df72fd6617a1)

- [Phase 3: Research Pipeline — Revised Architecture](https://www.notion.so/33c94ae1c521433ea32092a1a7856f90)

- [Brain Stem Architecture & Flows](https://www.notion.so/8d45305a868d4e73a6555b9e96d53a18)

- [📊 Brain Stem Master Roadmap](https://www.notion.so/8806dfbe864f478bb2cce258073ac2d3)
