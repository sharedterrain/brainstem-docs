# Phase 3: Research Pipeline — Architecture Draft

```yaml
---
doc_id: "phase_3"
last_updated: "2026-03-19"
contract_version: "0.3.0"
status: "Draft — pre-implementation"
---
```

---

## Overview

Phase 3 builds automated research on top of the existing Brain Stem pipeline. Perplexity runs saved queries from the Research Jobs table and surfaces articles into a new Articles table. Two triggers: scheduled (daily runner) and ad-hoc (R: prefix in Slack).

**What gets built:**

- Articles table (new Airtable table)

- Scenario B — scheduled research runner

- R: prefix handler in Scenario A

- Open Brain push for each new article

- Review Gallery view in Airtable

---

## 1. New Airtable Table: Articles

**Table ID:** To be created. Add to module reference after setup.

**Base ID:** `<<AIRTABLE_BASE_ID>>`

| Field | Type | Notes |
| --- | --- | --- |
| Title | Single line text | Article headline. Perplexity may not return this — derive from URL or leave blank for now. |
| URL | Single line text | Primary dedup key. One record per URL. |
| Source Domain | Single line text | Parsed from URL (e.g., `theguardian.com`) |
| Summary | Long text | Perplexity-synthesized snippet for this citation |
| Relevance Score | Number | 0.0–1.0. Populated by Airtable AI enrichment (Phase 3 step, not at ingest time) |
| Published Date | Date | From Perplexity citation metadata if available, else null |
| Status | Single select | `New`, `Reviewed`, `Saved`, `Dismissed` |
| Notes | Long text | Manual notes during review |
| Research Job | Link to Research Jobs | Linked to the job that sourced this article |
| Tags | Multiple select | Airtable AI enrichment pass (same pattern as Brain Stem — deferred within Phase 3) |
| Created | Date | Auto via Airtable |

**Rationale for URL as dedup key:** Perplexity returns the same high-authority sources repeatedly across jobs. URL dedup prevents duplicate records when two jobs surface the same article.

---

## 2. Scenario B — Scheduled Research Runner

**Trigger:** Schedule module. Runs daily (or per-job Frequency — see §2.3).

**Purpose:** Pull all active Research Jobs due to run, call Perplexity for each, create Article records, update job metadata.

### 2.1 Module Sequence

```plain text
[Schedule Trigger]
    ↓
[HTTP GET] Search Research Jobs
    filterByFormula: AND(Active=TRUE(), OR(Run Now=TRUE(), Next Run ≤ NOW()))
    ↓
[Iterator] — one execution per job
    ↓
[HTTP POST] Perplexity API
    ↓
[JSON Parse] Extract citations array
    ↓
[Iterator] — one execution per citation
    ↓
[HTTP GET] Articles — search by URL (dedup check)
    ↓
[Filter] URL does not exist in Articles
    ↓
[HTTP POST] Create Article record
    ↓
[HTTP POST] Open Brain ingest (fire-and-forget)
    ↓
[HTTP PATCH] Research Job — update Last Run, Next Run, Last Run Summary, uncheck Run Now
```

### 2.2 Perplexity API Call

**URL:** `https://api.perplexity.ai/chat/completions` **Method:** POST **Auth header:** `Authorization: Bearer <<PERPLEXITY_API_KEY>>`

**Request body template:**

```json
{
  "model": "sonar",
  "messages": [
    {
      "role": "user",
      "content": "<<job.Query>>"
    }
  ],
  "search_domain_filter": <<job.Include Domains — parse to array, omit if empty>>,
  "search_recency_filter": "<<job.Recency Window — map: 30d→month, 7d→week, 1d→day>>",
  "return_citations": true,
  "max_tokens": 1024
}
```

**Response shape (relevant fields):**

```json
{
  "choices": [
    {
      "message": {
        "content": "Synthesized answer text with inline [1][2] citation markers"
      }
    }
  ],
  "citations": [
    "https://example.com/article-1",
    "https://example.com/article-2"
  ]
}
```

**Note:** Perplexity returns URLs in `citations[]` and synthesized text in `choices[0].message.content`. There is no per-citation title or summary in the raw response — the synthesized content references citations by index. For Phase 3, store the full synthesized content as `Last Run Summary` on the job, and store each citation URL as an Article record with a blank Summary (Airtable AI enrichment fills this later). If per-article summaries are needed at ingest time, a second Claude call can extract them — defer until usage shows it's necessary.

**Field mapping: Recency Window → Perplexity filter**

| Airtable value | Perplexity value |
| --- | --- |
| `1d` | `day` |
| `7d` | `week` |
| `30d` | `month` |
| anything else | omit filter |

### 2.3 Frequency → Next Run Calculation

After each job runs, compute Next Run based on Frequency:

| Frequency value | Next Run |
| --- | --- |
| Daily | now + 1 day |
| Weekly | now + 7 days |
| Custom | <<UNKNOWN — needs field clarification>> |

**Open question:** The Research Jobs table has a `Frequency` field with a `Custom` value visible. Clarify what Custom means — fixed interval in days? A separate interval field? This affects how Next Run is computed after each run.

### 2.4 Dedup Check

Before creating an Article record:

1. GET Articles with `filterByFormula: URL="<<citation_url>>"`

1. If any records returned → skip. Filter passes only on empty result.

**Airtable GET for dedup:**

```plain text
GET https://api.airtable.com/v0/<<AIRTABLE_BASE_ID>>/<<ARTICLES_TABLE_ID>>
  ?filterByFormula=URL%3D%22<<encoded_url>>%22
  &maxRecords=1
```

### 2.5 Article POST Body

```json
{
  "fields": {
    "Title": "",
    "URL": "<<citation_url>>",
    "Source Domain": "<<parsed from URL>>",
    "Status": "New",
    "Research Job": ["<<job_record_id>>"]
  }
}
```

Source Domain can be parsed in Make using a Text Parser regex: `^https?://(?:www\.)?([^/]+)`.

### 2.6 Research Job PATCH (post-run update)

```json
{
  "fields": {
    "Last Run": "<<now — ISO8601>>",
    "Last Run Summary": "<<choices[0].message.content>>",
    "Run Now": false
  }
}
```

Next Run is a typed date field → isolate in a separate conditional PATCH (same pattern as Brain Stem typed-field guards).

---

## 3. R: Prefix Handler (Scenario A Extension)

**Trigger:** Message in #brain-stem starts with `R:`

**Purpose:** Create a Research Job record from Slack and optionally trigger immediate research.

**Design decision — two options:**

**Option A (queue only):** R: creates a Research Job with `Run Now = true`. Scenario B picks it up on next scheduled run (could be within minutes if Scenario B runs frequently).

**Option B (immediate):** R: creates the Research Job AND calls Perplexity inline within Scenario A, then creates Article records immediately. Slack confirmation includes article count.

**Recommendation: Option A.** Keeps Scenario A fast and stateless. Scenario B can be scheduled every 15–30 min for near-real-time response. Option B adds significant complexity to Scenario A and creates a slow path for every R: message.

### 3.1 Module Sequence (Option A)

```plain text
[Existing webhook + bot filter]
    ↓
[Filter] text starts with R:
    ↓
[Tools > Set variable] clean_text = strip "R:" prefix
    ↓
[HTTP POST] Create Research Job record
    ↓
[HTTP POST] Create Inbox Log record (Status=Filed, Filed To=Research Jobs)
    ↓
[HTTP POST] Slack reply — in-thread confirmation
```

**Research Job POST body (R: route):**

```json
{
  "fields": {
    "Job Name": "<<clean_text — first ~50 chars>>",
    "Query": "<<clean_text>>",
    "Active": true,
    "Run Now": true,
    "Recency Window": "30d"
  }
}
```

**Slack confirmation:**

```plain text
Research job queued: "<<clean_text>>"
It'll run within 30 minutes. Results → Articles table.
```

### 3.2 Placement in Scenario A

Add R: as a new route off the existing prefix router, before the bot filter passes to BD classification. Route ordering:

1. PRO: (existing)

1. R: (new)

1. fix: (existing — threaded replies only)

1. BD: / fallthrough (existing)

---

## 4. Open Brain Integration

Each new Article record gets pushed to Open Brain (fire-and-forget, same pattern as Brain Stem captures).

**Module placement:** After Article POST, before Research Job PATCH.

**Body:**

```json
{
  "text": "<<URL>> <<Title if non-empty>>",
  "source": "brain_stem",
  "destination": "research_jobs",
  "confidence": 1.0,
  "destination_record_id": "<<job_record_id>>",
  "classified_name": "<<URL>>"
}
```

**URL:** `https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-thought` **Header:** `x-brain-key: <<OPEN_BRAIN_ACCESS_KEY>>`

---

## 5. Airtable: Review Gallery View

Manual step — no Make involvement.

In the Articles table, create a Gallery view:

- Filter: `Status = New`

- Card title: Title (or URL if title empty)

- Card fields: Source Domain, Research Job, Created

- Sort: Created DESC

This is the triage interface. Jedidiah reviews New articles, sets Status to Saved or Dismissed.

---

## 6. Airtable AI Enrichment

Airtable AI can auto-populate Summary, Relevance Score, and Tags per article. This requires:

- An Airtable AI field for each (configured per-table in Airtable UI)

- A prompt referencing URL and Research Job query

**Deferred within Phase 3** — build and test the ingest pipeline first. Add AI enrichment in a second pass once article volume is real.

**When ready, the enrichment prompt pattern:**

```plain text
The following article was surfaced by a research query: "<<Research Job.Query>>"
Article URL: <<URL>>

Score its relevance to the query (0.0–1.0) and write a 2-sentence summary.
Return JSON: { "relevance_score": 0.0, "summary": "..." }
```

---

## 7. Module Reference (Scenario B — new)

Scenario B is a new Make scenario. Module numbers start fresh.

| Module # | Type | Purpose |
| --- | --- | --- |
| 1 | Schedule | Trigger (daily or every N hours — TBD) |
| 2 | HTTP GET | Search Research Jobs (Active + due) |
| 3 | Iterator | Per job |
| 4 | HTTP POST | Perplexity API call |
| 5 | JSON Parse | Extract citations + synthesized content |
| 6 | Iterator | Per citation URL |
| 7 | HTTP GET | Articles dedup check |
| — | Filter | URL not found |
| 8 | HTTP POST | Create Article record |
| 9 | HTTP POST | Open Brain ingest (fire-and-forget) |
| 10 | HTTP PATCH | Research Job — Last Run, Last Run Summary, Run Now=false |
| 11 | HTTP PATCH | Research Job — Next Run (conditional, typed date) |

**Scenario A additions (R: route):**

| Module # | Type | Purpose |
| --- | --- | --- |
| ~290 | Tools > Set variable | Strip R: prefix → clean_text |
| ~291 | HTTP POST | Create Research Job (Run Now=true) |
| ~292 | HTTP POST | Create Inbox Log record (Status=Filed, Filed To=Research Jobs) |
| ~293 | HTTP POST | Slack in-thread confirmation |

Module numbers ~290+ to avoid collision with existing modules. Assign during build.

---

## 8. Open Questions (Resolve Before Build)

1. **Frequency/Custom field** — What does `Custom` mean in the Frequency field? Is there a separate interval field, or is it a fixed value? Affects Next Run calculation.

1. **Scenario B schedule interval** — How often should the runner fire? Daily is simple; every 30 min enables near-real-time R: response. Affects cost negligibly at current volume.

1. **Article Title** — Perplexity doesn't return per-citation titles. Accept blank Title at ingest (filled manually or via Airtable AI), or add a Claude call to extract title from URL? Recommendation: blank for now.

1. **Exclude Domains** — Perplexity supports `search_domain_filter` but only as an allowlist, not a blocklist, in some model versions. Verify current sonar model supports exclusion; if not, the Exclude Domains field is inert for Phase 3.

---

## 9. Build Sequence

| Step | What | Prereq |
| --- | --- | --- |
| 1 | Create Articles table in Airtable (schema per §1) | — |
| 2 | Add Articles table ID to module reference | Step 1 |
| 3 | Build Scenario B skeleton (Schedule → Research Jobs GET → Iterator) | Step 2 |
| 4 | Add Perplexity call + JSON parse | Step 3, Perplexity key |
| 5 | Add citation iterator + dedup check + Article POST | Step 4 |
| 6 | Add Open Brain push | Step 5 |
| 7 | Add Research Job PATCH (Last Run + Next Run) | Step 5 |
| 8 | Seed one Research Job, run manually, verify Article records created | Step 7 |
| 9 | Add R: route to Scenario A | Step 8 |
| 10 | Create Review Gallery view in Airtable | Step 1 |
| 11 | Airtable AI enrichment (deferred — second pass) | Step 8 |

---

## 10. Deferred (Not Phase 3)

- AI enrichment (Summary, Relevance Score, Tags) — second pass within Phase 3 or Phase 4

- Article deduplication across jobs (same URL sourced by two different jobs — currently creates two records linked to different jobs; acceptable at current volume)

- CAL: route (Phase 4)

- Perplexity fallback (none designed — if Perplexity is down, job is skipped, Next Run is not updated, it retries next scheduled run)

---

## Next Phase

[Phase 4: Content Synthesis](https://www.notion.so/25f0383da86e40c5ab833bf28f7185ad)

**Child page:** Phase 3 review
---
### 🔴 Contract violations / conflicts
**1. Airtable Base ID in plain text — violates CONTRACT §11**[[1]](https://www.notion.so/CONTRACT-Brain-Stem-cb5393105c784cc3969571a898b4f81e)
§11 explicitly says: *"Never publish in Git mirror or public docs: Airtable Base IDs, Table IDs (treat as sensitive metadata)."* The Phase 3 doc exposes `appuT9wJR9eKmVfyU` in §1. Should be `<<AIRTABLE_BASE_ID>>`.
**2. No Inbox Log record on R: capture — violates §10 invariant**[[1]](https://www.notion.so/CONTRACT-Brain-Stem-cb5393105c784cc3969571a898b4f81e)
CONTRACT §10 invariant: *"Every invocation of the Storage Interface must produce exactly one Inbox Log record."* The R: handler in Scenario A (§3.1) creates a Research Job directly but never creates an Inbox Log entry. PRO: also bypasses classification but still creates an Inbox Log. R: should follow the same pattern — or the invariant needs a documented exception.
**3. Open Brain payload shape deviates from Memory Interface (§3.5)**[[1]](https://www.notion.so/CONTRACT-Brain-Stem-cb5393105c784cc3969571a898b4f81e)
CONTRACT §3.5 Memory Interface defines flat fields: `text`, `source`, `destination`, `confidence`, `classified_name`, `record_id`. Phase 3 §4 wraps them in a `metadata` object and introduces new values:
- `source: "brain_stem_research"` — not defined in CONTRACT (only `"brain_stem"` and `"brain_stem_fix"` are)
- `destination: "articles"` — not in the CONTRACT entity list
- `research_job_id` replaces the standard `record_id` field
Either the Phase 3 payload needs to conform to the existing interface, or the CONTRACT Memory Interface needs a minor bump to accommodate the research source.
---
### 🟡 Missing from CONTRACT — needs additive updates
**4. Articles table not in §9 Data Contracts**[[1]](https://www.notion.so/CONTRACT-Brain-Stem-cb5393105c784cc3969571a898b4f81e)
Articles is a brand new entity. CONTRACT §9 defines Inbox Log, Projects, People, Ideas, Admin, Events. Articles needs to be added — schema is well-defined in Phase 3 §1, just needs to be promoted to the contract.
**5. Research Jobs table not in §9 either**
Research Jobs is referenced as the R: destination in §7 but its schema never appears in §9. This may have been an oversight from the original contract — it was always planned but never schematized.
**6. CONTRACT §13 needs Phase 3 scope definition**[[1]](https://www.notion.so/CONTRACT-Brain-Stem-cb5393105c784cc3969571a898b4f81e)
§13 currently says "Phase 3–9: Not yet implemented" with no scope breakdown. When Phase 3 moves to implementation, §13 needs a scope entry similar to Phase 1 and Phase 2.
---
### 🟡 Spec staleness
**7. contracts/spec is at v0.2.0, CONTRACT is at v0.4.0**[[2]](https://www.notion.so/contracts-spec-Brain-Stem-98d781fe40ed4e31a566f0d8886325fc)
The spec hasn't been updated since the Memory Interface, fix: route, and Open Brain changes. Relevant gaps:
- R route shows `llm_mode: "extract_only"` and `prompt_id: "research_extract_v1"` — but Phase 3 doesn't use Claude for the R: route at all; it calls Perplexity directly. The spec's R route definition needs revision.
- fix route shows `implementation: "scaffolded"` — should be `"implemented"` (live since Phase 2).
- No Memory Interface or Supabase provider in spec.
- No Articles or Research Jobs table definitions.
---
### 🟡 Internal doc issues
**8. Duplicate/stale content at bottom of page**
The page contains TWO documents spliced together. Everything below the second `---` + YAML block (dated `2026-02-18`, `contract_version: "0.2.0"`) is the original placeholder template — stale overview, empty "As-Designed" and "As-Built" sections, a completion checklist that doesn't match the architecture above it. Should be deleted or clearly superseded.
**9. YAML header references contract v0.3.0**
The top YAML says `contract_version: "0.3.0"` but CONTRACT is at v0.4.0. Should be `"0.4.0"`.
**10. Contract References section (bottom) references v0.2.0**
The `See: CONTRACT (Brain-Stem) v0.2.0` line is stale — should reference v0.4.0.
---
### 🟢 Aligned / well-designed
- **R: prefix routing** matches CONTRACT §7 semantics (prefix → Research Jobs, scaffolded Phase 3) ✅
- **Option A recommendation** (queue-only R: handler) is the right call — keeps Scenario A fast and stateless, consistent with the existing route pattern ✅
- **Perplexity API usage** aligns with CONTRACT §2 scope and §3b provider mapping ✅
- **URL dedup pattern** is sound — prevents citation duplication across jobs ✅
- **Fire-and-forget Open Brain push** follows the established pattern from Phase 1/2 (once payload shape is reconciled) ✅
- **Build sequence** is well-ordered with sensible prereqs ✅
- **Deferred items** are clearly scoped and reasonable ✅
---
### Summary — action items before build
| # | Action | Severity |
| --- | --- | --- |
| 1 | Replace Base ID with `<<AIRTABLE_BASE_ID>>` placeholder | 🔴 Security |
| 2 | Add Inbox Log creation to R: route (or document exception) | 🔴 Invariant |
| 3 | Reconcile Open Brain payload with Memory Interface | 🔴 Contract deviation |
| 4 | Add Articles + Research Jobs schemas to CONTRACT §9 | 🟡 Additive |
| 5 | Update contracts/spec to v0.4.0 | 🟡 Staleness |
| 6 | Delete stale placeholder content at bottom of page | 🟡 Hygiene |
| 7 | Fix YAML contract_version to 0.4.0 | 🟡 Reference |
