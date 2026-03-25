# contracts/spec (Brain-Stem)

**Machine-readable specification for Brain Stem**

This is the automation anchor. Markdown CONTRACT is human-readable; this spec is machine-parseable. Aligned to CONTRACT v0.7.0.

---

## spec.yaml

```yaml
project: "brainstem"
contract_version: "0.7.0"
spec_version: "1.0.0"  # full rewrite from 0.2.0
last_updated: "2026-03-25"

# ═══════════════════════════════════════════════════════════════
# PROVIDERS — functional pipeline → current provider mapping
# See CONTRACT §3 / §3b
# ═══════════════════════════════════════════════════════════════
providers:
  capture:
    current: "slack"
    interface: "capture_interface"
  orchestration:
    current: "make.com"
    interface: "scenario_runner"
  intelligence:
    current: "claude"
    interface: "classification_interface"  # covers classification + extraction
  research:
    current: "perplexity"
    interface: "research_provider_interface"
  storage:
    current: "airtable"
    interface: "storage_interface"
  memory:
    current: "supabase"
    interface: "memory_interface"
    instances:
      open_brain:
        project_ref: "<<SUPABASE_PROJECT_REF>>"
        table: "thoughts"
        ingest_function: "ingest-thought"
        auth_secret: "MCP_ACCESS_KEY"
      research_brain:
        project_ref: "<<SUPABASE_PROJECT_REF>>"  # same project as Open Brain
        table: "research_returns"
        ingest_function: "ingest-research"
        auth_secret: "MCP_ACCESS_KEY"  # same credential
  publishing:
    current: "TBD"
    interface: "publishing_interface"

# ═══════════════════════════════════════════════════════════════
# SCENARIOS — Make.com automation scenarios
# ═══════════════════════════════════════════════════════════════
scenarios:
  scenario_a:
    name: "Brain Stem — Main Pipeline"
    trigger: "slack_webhook"
    routes: ["PRO", "BD", "CAL", "R", "fix"]
    memory_push: "open_brain"  # fire-and-forget after each destination route
    implementation: "implemented"

  scenario_b:
    name: "Research Runner"
    trigger: "webhook"  # from Scenario A (R: route) or Scenario C
    modes: ["sweep", "job"]
    research_provider: "perplexity"
    memory_push: "research_brain"  # fire-and-forget per article
    enrichment: "research_enrichment_v1"  # Claude end-of-run call
    implementation: "designed"  # Phase 3 — not yet built

  scenario_c:
    name: "Daily Research Cron"
    trigger: "schedule_24h"
    target: "scenario_b"
    mode: "sweep"
    implementation: "designed"  # Phase 3 — not yet built

# ═══════════════════════════════════════════════════════════════
# ROUTES — prefix-based message routing in Scenario A
# See CONTRACT §3.5, §13
# ═══════════════════════════════════════════════════════════════
routes:
  - name: "PRO"
    prefix: "PRO:"
    destination: "Projects"
    confidence: 1.0
    llm_mode: "extract_only"
    implementation: "implemented"
    prompt_id: "projects_extract_v1"
    scenario: "scenario_a"

  - name: "BD"
    prefix: "BD:"
    destination: "classified"  # Claude determines destination
    llm_mode: "classify_and_extract"
    implementation: "implemented"
    prompt_id: "brain_dump_classifier_v1"
    scenario: "scenario_a"

  - name: "CAL"
    prefix: "CAL:"
    destination: "Events"
    llm_mode: "extract_only"
    implementation: "scaffolded"
    prompt_id: "events_extract_v1"
    scenario: "scenario_a"

  - name: "R"
    prefix: "R:"
    destination: "ResearchJobs"
    llm_mode: "none"  # creates Research Job record; Perplexity handles research in Scenario B
    implementation: "designed"  # Phase 3
    triggers: "scenario_b"
    scenario: "scenario_a"

  - name: "fix"
    prefix: "fix:"
    destination: "user_specified"  # user provides destination keyword after fix:
    llm_mode: "re_extract"  # re-extracts original message with forced destination
    implementation: "implemented"  # live since Phase 2
    prompt_id: "brain_dump_classifier_v1"  # reuses BD classifier
    scenario: "scenario_a"

# ═══════════════════════════════════════════════════════════════
# THRESHOLDS
# See CONTRACT §4
# ═══════════════════════════════════════════════════════════════
thresholds:
  auto_file_confidence_min: 0.60

# ═══════════════════════════════════════════════════════════════
# DATA CONTRACTS — Airtable table schemas
# Field names are CamelCase spec identifiers; Airtable uses spaced equivalents
# See CONTRACT §9
# ═══════════════════════════════════════════════════════════════
data_contracts:
  tables:
    # --- Phase 1–2 tables (implemented) ---

    InboxLog:
      required_fields:
        - OriginalText
        - CleanText
        - FiledTo
        - Confidence
        - Status            # Pending, Filed, Error, NeedsReview
        - SlackChannel
        - SlackMessageTS
        - Created           # Created time (auto)
      optional_fields:
        - SlackThreadTS
        - DestinationName
        - DestinationURL
        - AIOutputRaw
        - ErrorDetails
        - SourceLink        # Slack permalink — traceability for fix + R: routes
        - AdminStatus       # Todo, Done
      notes:
        - "NO Tags field on Inbox Log"
        - "AdminStatus is just Todo/Done"

    People:
      required_fields:
        - Name
        - LastTouched
      optional_fields:
        - Context
        - FollowUps
        - Tags              # Long text (NOT Multiple select)
        - EntityType        # Single select: Person, Organization

    Projects:
      required_fields:
        - Name
        - Type              # digital, physical, hybrid
        - Status            # active, waiting, blocked, someday, done
        - NextAction
        - LastTouched
      optional_fields:
        - Notes
        - Tags              # Long text (NOT Multiple select)

    Ideas:
      required_fields:
        - Name
        - LastTouched
      optional_fields:
        - OneLiner
        - Notes
        - Tags              # Long text (NOT Multiple select)

    Admin:
      required_fields:
        - Name
        - Status            # Todo, Done (only two values)
        - Created
      optional_fields:
        - DueDate
        - Notes
        - Tags              # Long text (NOT Multiple select)

    Events:
      required_fields:
        - Title
        - Created
      optional_fields:
        - EventType
        - CalendarSource    # serves as source field — no separate Source field
        - Attendees
        - Location
        - Notes
        - StartTime
        - EndTime
        - Tags              # Long text (NOT Multiple select)
        - CalendarSyncStatus  # Synced, Pending, Failed, Not Synced

    # --- Phase 3 tables (designed, not yet built) ---

    Articles:
      phase: 3
      required_fields:
        - Title
        - URL               # primary dedup key (with PublishedDate)
        - Status            # New, Reviewed, Saved, Dismissed, Use
        - RunID
      optional_fields:
        - SourceDomain      # parsed from URL
        - PublishedDate
        - Summary           # Claude end-of-run enrichment
        - KeyPoints         # Claude end-of-run enrichment
        - Category          # Claude end-of-run enrichment (Single select)
        - Tags              # Claude end-of-run enrichment (Long text)
        - RelevanceScore    # Claude end-of-run enrichment (0.0–1.0)
        - WhyItMatters      # Claude end-of-run enrichment
        - FullText          # Perplexity synthesized content (domain-level, shared across articles)
        - MorningPick       # top 3 per run (Checkbox)
        - DedupKey          # Formula: URL + Published Date
        - ResearchJob       # Linked record → ResearchJobs (R: runs only)
        - Domain            # Linked record → Domains (sweep runs only)
        - Thumbnail         # deferred — not returned by Perplexity
        - Citations         # deferred
        - Drafts            # Phase 4-5
      dedup_strategy: "URL + PublishedDate — same URL with newer date = new record"
      notes:
        - "Domain and ResearchJob links are mutually exclusive per record"

    ResearchJobs:
      phase: 3
      required_fields:
        - JobName
        - Query
        - Active
        - Frequency         # Custom, Daily
        - RunNow
      optional_fields:
        - RecencyWindow     # 1d, 7d, 30d (default 30d)
        - RelevanceThreshold  # inert Phase 3 — future provider use
        - IncludeDomains    # allowlist for provider domain filter
        - ExcludeDomains    # inert (Perplexity is allowlist only)
        - LanguageRegion
        - NextRun
        - LastRun
        - LastRunSummary
        - Articles          # Linked record → Articles

    Domains:
      phase: 3
      required_fields:
        - DomainName
        - Prompt
        - Active
      optional_fields:
        - RecencyWindow     # 1d, 7d, 30d
        - LastRun
        - NextRun
        - LastRunSummary

    ResearchLens:
      phase: 3
      required_fields:
        - Entry             # Long text — free-form focus context
        - Active
      optional_fields:
        - Created

# ═══════════════════════════════════════════════════════════════
# MEMORY INTERFACE — Supabase write targets
# See CONTRACT §3.5, Open-Brain Deployment §6A
# Both use same project + credentials (as-built deviation from original spec)
# ═══════════════════════════════════════════════════════════════
memory_interface:
  open_brain:
    project_ref: "<<SUPABASE_PROJECT_REF>>"
    table: "thoughts"
    function: "ingest-thought"
    endpoint: "https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-thought"
    auth:
      header: "x-brain-key"
      secret_env: "MCP_ACCESS_KEY"
    writers:
      - scenario: "scenario_a"
        source_tag: "brain_stem"
        modules: [275, 276, 277, 278, 279, 288, 289]  # primary routes
      - scenario: "scenario_a"
        source_tag: "brain_stem_fix"
        modules: [281, 282, 283, 284, 285]  # fix routes
    payload:
      text: "string (required) — composed from Claude-extracted fields, not raw clean_text"
      metadata:
        source: "brain_stem | brain_stem_fix"
        destination: "people | projects | ideas | admin | events | needs_review"
        confidence: "number (0.0-1.0)"
        classified_name: "string"
        destination_record_id: "string (Airtable record ID)"

  research_brain:
    project_ref: "<<SUPABASE_PROJECT_REF>>"  # same project as Open Brain
    table: "research_returns"
    function: "ingest-research"
    endpoint: "https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-research"
    auth:
      header: "x-brain-key"
      secret_env: "MCP_ACCESS_KEY"  # same credential as Open Brain
    writers:
      - scenario: "scenario_b"
        source_tag: "research_digest"
    dedup: "partial unique index on url + published_date (WHERE NOT NULL), ON CONFLICT DO NOTHING"
    payload:
      text: "string (required) — title + snippet"
      url: "string"
      source_domain: "string"
      digest_run_id: "string (Scenario B execution ID)"
      research_job_id: "string (Airtable record ID)"
      published_date: "string (ISO date)"
      source_tag: "research_digest"

# ═══════════════════════════════════════════════════════════════
# LLM CONTRACTS — prompt configurations
# See CONTRACT §7
# ═══════════════════════════════════════════════════════════════
llm_contracts:
  prompts:
    - id: "projects_extract_v1"
      route: "PRO"
      model: "claude-3-5-haiku-20241022"
      temperature: 0
      max_tokens: 500
      input_fields: ["clean_text"]
      output_schema_ref: "schemas.projects_extract_v1"

    - id: "brain_dump_classifier_v1"
      route: "BD"
      model: "claude-3-5-sonnet-20241022"
      temperature: 0.3
      max_tokens: 500
      input_fields: ["clean_text"]
      output_schema_ref: "schemas.brain_dump_classifier_v1"
      also_used_by: ["fix"]  # fix route reuses with forced destination

    - id: "events_extract_v1"
      route: "CAL"
      model: "TBD"
      implementation: "scaffolded"
      input_fields: ["clean_text"]
      output_schema_ref: "schemas.events_extract_v1"

    - id: "research_enrichment_v1"
      context: "scenario_b_end_of_run"  # not a route — Scenario B enrichment call
      model: "claude-sonnet-class"
      purpose: "Enrich all articles from a single Scenario B run"
      input_fields: ["articles_from_run", "domain_prompt_or_job_query"]
      output_per_article:
        - Summary
        - KeyPoints
        - WhyItMatters
        - Category
        - Tags
        - RelevanceScore
        - MorningPick       # true for top 3 only
      implementation: "designed"  # Phase 3

# ═══════════════════════════════════════════════════════════════
# SCHEMAS — JSON output shapes for LLM calls
# ═══════════════════════════════════════════════════════════════
schemas:
  projects_extract_v1:
    type: object
    required: ["name", "type", "status", "next_action", "notes", "tags", "reason"]
    properties:
      name: { type: ["string", "null"] }
      type: { type: ["string", "null"], enum: ["digital", "physical", "hybrid", null] }
      status: { type: ["string", "null"], enum: ["active", "waiting", "blocked", "someday", "done", null] }
      next_action: { type: ["string", "null"] }
      notes: { type: ["string", "null"] }
      tags: { type: "array", items: { type: "string" } }
      reason: { type: "string" }

  brain_dump_classifier_v1:
    type: object
    required: ["destination", "confidence", "data", "reason"]
    properties:
      destination: { type: "string", enum: ["people", "projects", "ideas", "admin", "events", "needs_review"] }
      confidence: { type: "number", minimum: 0.0, maximum: 1.0 }
      data:
        type: object
        properties:
          name: { type: "string" }
          context: { type: ["string", "null"] }
          follow_ups: { type: ["string", "null"] }
          status: { type: ["string", "null"] }
          next_action: { type: ["string", "null"] }
          notes: { type: ["string", "null"] }
          one_liner: { type: ["string", "null"] }
          due_date: { type: ["string", "null"], pattern: "^\\d{4}-\\d{2}-\\d{2}$" }
          tags: { type: "array", items: { type: "string" } }
          project_type: { type: ["string", "null"], enum: ["digital", "physical", "hybrid", null] }
          attendees: { type: ["string", "null"] }
          location: { type: ["string", "null"] }
          event_type: { type: ["string", "null"] }
      reason: { type: "string" }

  events_extract_v1:
    type: object
    required: ["name"]
    properties:
      name: { type: "string" }
      event_type: { type: ["string", "null"] }
      attendees: { type: ["string", "null"] }
      location: { type: ["string", "null"] }
      notes: { type: ["string", "null"] }
      calendar_source: { type: ["string", "null"] }
    note: "scaffolded — schema is speculative until CAL route is implemented"

# ═══════════════════════════════════════════════════════════════
# INVARIANTS
# Authoritative definitions live in CONTRACT §10.
# This section indexes invariants for machine consumption (id + severity + applies_to only).
# ═══════════════════════════════════════════════════════════════
invariants:
  - { id: "INV-001", severity: "critical", applies_to: ["scenario_a"] }
  - { id: "INV-002", severity: "warning", applies_to: ["PRO"] }
  - { id: "INV-003", severity: "critical", applies_to: ["scenario_a"] }
  - { id: "INV-004", severity: "critical", applies_to: ["BD"] }
  - { id: "INV-005", severity: "critical", applies_to: ["scenario_a"] }
  - { id: "INV-006", severity: "warning", applies_to: ["scenario_a"] }
  - { id: "INV-007", severity: "warning", applies_to: ["scenario_a"] }
  - { id: "INV-008", severity: "warning", applies_to: ["BD"] }
  - { id: "INV-009", severity: "critical", applies_to: ["BD", "PRO", "fix"] }
  - { id: "INV-010", severity: "warning", applies_to: ["PRO", "BD"] }
  - { id: "INV-011", severity: "critical", applies_to: ["R"] }
  - { id: "INV-012", severity: "warning", applies_to: ["scenario_a", "scenario_b"] }
  - { id: "INV-013", severity: "warning", applies_to: ["scenario_b"] }

# ═══════════════════════════════════════════════════════════════
# CHANGE CONTROL
# ═══════════════════════════════════════════════════════════════
change_control:
  spec_version: "1.0.0"
  contract_version: "0.7.0"
  last_updated: "2026-03-25"
  change_summary: >-
    Full rewrite from v0.2.0. Added: memory_interface (Open Brain +
    Research Brain as shared-project tables), scenarios (A/B/C),
    Phase 3 tables (Articles, ResearchJobs, Domains, ResearchLens),
    research_enrichment_v1 LLM contract. Updated: fix route to
    implemented (Phase 2), R: route redesigned (triggers Scenario B
    with Perplexity, not Claude extract), all table schemas per
    as-built corrections (Tags = Long text, Admin Status = Todo/Done,
    Events CalendarSource, no Tags on InboxLog), new invariants
    INV-006 through INV-008.
```
