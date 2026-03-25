# Open-Brain Deployment

---

# Open Brain: Architecture & Build Specification

```yaml
---
doc_id: "open_brain_build_spec"
created: "2026-03-04"
author: "Claude Opus 4.6 (architectural spec)"
builder: "Claude Sonnet (execution)"
contract_version: "1.0.1"
status: "Steps 1-13 Complete — Primary Routes + Research Brain Live"
---
```

## 1. Purpose

Open Brain is a semantic memory layer that stores vector embeddings of every captured thought, enabling meaning-based retrieval across all AI tools in Jedidiah's ecosystem. It serves two integration points:

**Magi/OpenClaw** — gains persistent semantic memory beyond its 50k token session context. Can store and retrieve thoughts via tool calls.

**Brain Stem (Make.com)** — gains a secondary push target. Every classified capture gets embedded and stored alongside its Brain Stem metadata, making the full capture history semantically searchable.

## 2. Architecture Overview

### 2.1 Memory Topology

The deployed system uses a **three-memory architecture** plus a **Research Brain catalogue**. Two memories are semantic vector stores (Supabase + pgvector), deployed as independent Supabase projects with their own credentials; one is local filesystem state. The Research Brain (v1.0.1) is a vector-enabled table (`research_returns`) within Jedi's Open Brain project — same instance, same credentials, dedicated Edge Function (`ingest-research`), embeddings via the same OpenRouter pipeline.

```plain text
┌──────────────────────────────────────────────────────────────────┐
│                    THREE-MEMORY TOPOLOGY                         │
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────┐       │
│  │  JEDI'S OPEN BRAIN      │  │  MAGI BRAIN             │       │
│  │  (shared semantic store) │  │  (Magi-exclusive store) │       │
│  │                          │  │                          │       │
│  │  Writers:                │  │  Writer:                 │       │
│  │   • Brain Stem (Make)    │  │   • Magi only            │       │
│  │   • Magi (OpenClaw)      │  │                          │       │
│  │                          │  │  Reader:                 │       │
│  │  Readers:                │  │   • Magi only            │       │
│  │   • Magi (OpenClaw)      │  │                          │       │
│  │   • Claude Desktop/Code  │  │  Content:                │       │
│  │   • Any MCP client       │  │   • Cross-session        │       │
│  │                          │  │     operational patterns  │       │
│  │  Content:                │  │   • Learned behaviors     │       │
│  │   • Brain Stem captures  │  │   • Magi's own context    │       │
│  │   • Decisions & insights │  │                          │       │
│  │   • People, projects,    │  │  Functions:              │       │
│  │     events, ideas, admin │  │   • magi-brain-ingest    │       │
│  │                          │  │   • magi-brain-mcp       │       │
│  │  Functions:              │  │                          │       │
│  │   • ingest-thought       │  │  Instance:               │       │
│  │   • open-brain-mcp       │  │   <<MAGI_BRAIN_REF>>     │       │
│  │                          │  │                          │       │
│  │  Instance:               │  └─────────────────────────┘       │
│  │   <<SUPABASE_PROJECT_REF>>│                                    │
│  └─────────────────────────┘                                     │
│                                                                  │
│  ┌─────────────────────────┐                                     │
│  │  OPENCLAW LOCAL MEMORY  │  Not a Supabase instance.           │
│  │  (filesystem state)     │  Included for completeness.         │
│  │                          │                                     │
│  │  • MEMORY.md (curated)  │                                     │
│  │  • memory/YYYY-MM-DD.md │                                     │
│  │  • No network required  │                                     │
│  └─────────────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
```

> **v1.0.1:** Jedi's Open Brain now also hosts the Research Brain — `research_returns` table (vector-enabled) + `ingest-research` Edge Function + research tools on `open-brain-mcp`, same project and credentials. See §6A Instance Registry.

### 2.2 Pattern vs Instance

This document serves two purposes:

1. **Reusable pattern** — §3 (schema), §4 (ingest function), §5 (MCP function) describe a generic semantic memory instance. Fork these sections to stand up additional brains.

1. **Instance registry** — §6A documents the two deployed Supabase instances, the Research Brain catalogue table, and their roles.

### 2.3 Single-Instance Data Flow (applies to each brain)

```plain text
┌─────────────────────────────────────────────────────────────┐
│                     WRITE PATH (Ingest)                      │
│                                                              │
│  Callers ────────────────→ Supabase Edge Function            │
│    POST with text +         "ingest-thought" (or variant)    │
│    metadata                   │                              │
│                               ├─→ OpenRouter embedding       │
│                               ├─→ INSERT into thoughts table │
│                               └─→ Return {id, status}        │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                     READ PATH (Retrieval)                     │
│                                                              │
│  Callers ────────────────→ Supabase Edge Function            │
│    MCP or curl                "*-mcp" endpoint               │
│                                 │                             │
│                                 ├─→ search_thoughts (semantic)│
│                                 ├─→ recent_thoughts (time)    │
│                                 └─→ brain_stats (counts)      │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Storage: Supabase (PostgreSQL + pgvector)
Embeddings: OpenRouter → text-embedding-3-small (1536 dimensions)
```

## 3. Components

### 3.1 Supabase Project

**Project name:** `open-brain` **Region:** Closest to Victoria, BC (US West or Canada if available)

### 3.2 Database Schema

**Extension required:** `pgvector`

**Table: **`thoughts`

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | uuid | PK, default `gen_random_uuid()` |  |
| `content` | text | NOT NULL | Raw captured text |
| `embedding` | vector(1536) |  | text-embedding-3-small output |
| `metadata` | jsonb | DEFAULT '{}' | Structured metadata (see §3.3) |
| `created_at` | timestamptz | DEFAULT `now()` |  |
| `updated_at` | timestamptz | DEFAULT `now()` |  |

**Function: **`match_thoughts`

```sql
create or replace function match_thoughts (
  query_embedding vector(1536),
  match_threshold float default 0.5,
  match_count int default 10
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float,
  created_at timestamptz
)
language plpgsql
as $$
begin
  return query
  select
    thoughts.id,
    thoughts.content,
    thoughts.metadata,
    1 - (thoughts.embedding <=> query_embedding) as similarity,
    thoughts.created_at
  from thoughts
  where 1 - (thoughts.embedding <=> query_embedding) > match_threshold
  order by thoughts.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

**Security:**

```sql
alter table thoughts enable row level security;
create policy "Service role full access"
  on thoughts for all
  using (auth.role() = 'service_role');
```

### 3.3 Metadata Schema

The `metadata` JSONB column carries source-specific context. All fields optional.

**From Brain Stem captures:**

```json
{
  "source": "brain_stem",
  "destination": "people|projects|ideas|admin|events",
  "confidence": 0.85,
  "prefix": "BD:|PRO:|null",
  "destination_record_id": "rec...",
  "classified_name": "string",
  "tags": ["string"]
}
```

**From Magi:**

```json
{
  "source": "magi",
  "session_id": "string (optional)",
  "type": "decision|action_item|insight|context|note",
  "topic": "string (optional)"
}
```

**From manual/other:**

```json
{
  "source": "manual|slack_direct|other",
  "category": "string (optional)"
}
```

## 4. Edge Function: `ingest-thought`

**Purpose:** Universal write endpoint. Accepts text + metadata, generates embedding, stores in Supabase.

**URL:** `https://[PROJECT_REF].supabase.co/functions/v1/ingest-thought`

**Method:** POST

**Authentication:** `x-brain-key` header checked against `MCP_ACCESS_KEY` secret.

**Request body:**

```json
{
  "text": "string (required — the thought to embed and store)",
  "metadata": { }
}
```

**Processing steps:**

1. Validate `x-brain-key` header against `MCP_ACCESS_KEY` env var. Return 401 if missing/wrong.

1. Validate `text` field exists and is non-empty after trim. Return 400 if invalid.

1. Generate embedding via OpenRouter API:
    - Endpoint: `https://openrouter.ai/api/v1/embeddings`
    - Model: `openai/text-embedding-3-small`
    - Input: the `text` value

1. INSERT into `thoughts` table: `content` = text, `embedding` = result, `metadata` = metadata object.

1. Return `{ "id": "<uuid>", "status": "stored" }` with 200.

**Error handling:**

- OpenRouter failure → return 502 with `{ "error": "Embedding generation failed", "detail": "..." }`

- Supabase insert failure → return 500 with `{ "error": "Storage failed", "detail": "..." }`

**Environment variables (Supabase secrets):**

- `OPENROUTER_API_KEY` — OpenRouter API key

- `MCP_ACCESS_KEY` — shared access key for both ingest and MCP endpoints

- `SUPABASE_URL` — auto-provided by Supabase

- `SUPABASE_SERVICE_ROLE_KEY` — auto-provided by Supabase

**Implementation notes:**

- This function does NOT generate metadata via LLM. Brain Stem and Magi both pass structured metadata at call time. This eliminates the redundant LLM call from the original Open Brain guide.

- No Slack reply logic. Callers handle their own confirmations.

- The function should handle the Slack event challenge handshake ONLY if direct Slack integration is added later. For now, skip it.

### Reference implementation (Deno/Supabase Edge Function):

```typescript
import { createClient } from "@supabase/supabase-js";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/embeddings";
const EMBEDDING_MODEL = "openai/text-embedding-3-small";

Deno.serve(async (req: Request) => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "content-type, x-brain-key",
        "Access-Control-Allow-Methods": "POST",
      },
    });
  }

  // Auth check
  const accessKey = req.headers.get("x-brain-key");
  const expectedKey = Deno.env.get("MCP_ACCESS_KEY");
  if (!accessKey || accessKey !== expectedKey) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Parse body
  let body: { text?: string; metadata?: Record<string, unknown> };
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const text = body.text?.trim();
  if (!text) {
    return new Response(
      JSON.stringify({ error: "text field required and must be non-empty" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const metadata = body.metadata ?? {};

  // Generate embedding
  let embedding: number[];
  try {
    const embRes = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${Deno.env.get("OPENROUTER_API_KEY")}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: EMBEDDING_MODEL,
        input: text,
      }),
    });
    if (!embRes.ok) {
      const detail = await embRes.text();
      return new Response(
        JSON.stringify({ error: "Embedding generation failed", detail }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }
    const embData = await embRes.json();
    embedding = embData.data[0].embedding;
  } catch (err) {
    return new Response(
      JSON.stringify({
        error: "Embedding generation failed",
        detail: String(err),
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }

  // Store in Supabase
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
  );

  const { data, error } = await supabase
    .from("thoughts")
    .insert({ content: text, embedding, metadata })
    .select("id")
    .single();

  if (error) {
    return new Response(
      JSON.stringify({ error: "Storage failed", detail: error.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(
    JSON.stringify({ id: data.id, status: "stored" }),
    { status: 200, headers: { "Content-Type": "application/json" } }
  );
});
```

## 5. Edge Function: `open-brain-mcp`

**Purpose:** MCP-compatible read endpoint. Exposes semantic search, recent browse, stats, and research retrieval (6 tools total) to any MCP client.

**URL:** `https://[PROJECT_REF].supabase.co/functions/v1/open-brain-mcp`

**Authentication:** `x-brain-key` header, same key as ingest.

**Tools exposed:**

### 5.1 `search_thoughts`

- **Input:** `{ query: string, threshold?: number (default 0.5), limit?: number (default 10) }`

- **Process:** Generate embedding of query via OpenRouter (same model), call `match_thoughts` RPC.

- **Output:** Array of `{ id, content, metadata, similarity, created_at }`

### 5.2 `recent_thoughts`

- **Input:** `{ hours?: number (default 24), limit?: number (default 20), source?: string (optional filter) }`

- **Process:** SELECT from thoughts WHERE `created_at > now() - interval`, optionally filtered by `metadata->>'source'`, ordered by `created_at DESC`.

- **Output:** Array of `{ id, content, metadata, created_at }`

### 5.3 `brain_stats`

- **Input:** `{}`

- **Process:** COUNT total, COUNT by source, COUNT by destination, MIN/MAX created_at.

- **Output:** `{ total, by_source: {...}, by_destination: {...}, oldest, newest }`

### 5.4 `search_research`

- **Input:** `{ query: string, threshold?: number (default 0.5), limit?: number (default 10) }`

- **Process:** Generate embedding of query via OpenRouter, call `match_research` RPC against `research_returns` table.

- **Output:** Array of `{ id, title, url, source, published_date, summary, similarity, created_at }`

### 5.5 `latest_research_run`

- **Input:** `{ limit?: number (default 10) }`

- **Process:** SELECT from `research_returns` ORDER BY `created_at DESC`, returning the most recent ingested research articles.

- **Output:** Array of `{ id, title, url, source, published_date, summary, created_at }`

### 5.6 `get_research_digest`

- **Input:** `{ hours?: number (default 24), topic?: string (optional) }`

- **Process:** Retrieve recent research articles, optionally filtered by semantic similarity to topic. Provides a digest-oriented view of research activity.

**Output:** Array of `{ id, title, url, source, published_date, summary, created_at }` with optional similarity score when topic is provided.

**Implementation:** Follow the Open Brain guide's MCP server code (Step 11), which uses `@hono/mcp` and `@modelcontextprotocol/sdk`. Adapt the six tools above. The guide's implementation is sound — the only changes are:

1. Add the `source` filter option to `recent_thoughts`.

1. Add `by_destination` breakdown to `brain_stats`.

1. Use the same `x-brain-key` auth as ingest.

1. Add `search_research`, `latest_research_run`, and `get_research_digest` tools targeting the `research_returns` table and `match_research` RPC.

**Dependencies (deno.json):**

```json
{
  "imports": {
    "@hono/mcp": "npm:@hono/mcp@0.1.1",
    "@modelcontextprotocol/sdk": "npm:@modelcontextprotocol/sdk@1.24.3",
    "hono": "npm:hono@4.9.2",
    "zod": "npm:zod@4.1.13",
    "@supabase/supabase-js": "npm:@supabase/supabase-js@2.47.10"
  }
}
```

## 6A. Instance Registry

Two Supabase instances are deployed, plus the **Research Brain** (vector-enabled) within Jedi's Open Brain project. The two vector-store instances (Jedi's Open Brain and Magi Brain) use the identical schema (§3.2), matching function (§3.2), and RLS policy (§3.2). Research Brain uses a separate table (`research_returns`), its own matching function (`match_research`), and a dedicated Edge Function (`ingest-research`) but shares the same project, credentials, and `open-brain-mcp` endpoint as Jedi's Open Brain. All Edge Functions follow the same patterns (§4–5) with instance-specific naming.

| **Instance** | **Project Ref** | **Table** | **Ingest Function** | **MCP Function** | **Access Key Env Var** | **Writers** | **Readers** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jedi's Open Brain (shared) | `<<SUPABASE_PROJECT_REF>>` | `thoughts` | `ingest-thought` | `open-brain-mcp` | `<<OPEN_BRAIN_ACCESS_KEY>>` | Brain Stem (Make), Magi | Magi, Claude Desktop/Code, any MCP client |
| Research Brain (vector-enabled) | `<<SUPABASE_PROJECT_REF>>` (shared) | `research_returns` | `ingest-research` | `open-brain-mcp` (shared) | `<<OPEN_BRAIN_ACCESS_KEY>>` (shared) | Brain Stem Scenario B | Magi (via open-brain-mcp), Claude (via Supabase MCP) |
| Magi Brain (Magi-exclusive) | `<<MAGI_BRAIN_REF>>` | `thoughts` | `magi-brain-ingest` | `magi-brain-mcp` | `<<MAGI_BRAIN_ACCESS_KEY>>` | Magi only | Magi only |

**Jedi's Open Brain** stores shared knowledge: Brain Stem captures (people, projects, ideas, admin, events), Magi's decisions and insights, and any manual entries. Multiple systems write and read.

**Magi Brain** stores Magi's private operational memory: cross-session patterns, learned behaviors, tool usage observations, and operational context that only Magi needs. No external writers or readers. This is Magi's equivalent of institutional knowledge — what it has learned about how things work across sessions.

**Research Brain** stores research article metadata returned by Perplexity (or any research provider) via Brain Stem Scenario B. Articles are embedded at ingest time using the same OpenRouter pipeline as `thoughts`, enabling semantic search via `match_research` RPC and the `search_research` MCP tool. Deduplication uses a partial unique index on `url + published_date` (WHERE NOT NULL) with `ON CONFLICT DO NOTHING`; an empty result set signals a duplicate.

**Metadata differentiation:**

- Jedi's Open Brain: `metadata.source` distinguishes writers (`brain_stem`, `brain_stem_fix`, `magi`, `manual`)

- Magi Brain: `metadata.source` is always `magi-brain` — instance isolation provides the access boundary, not metadata filtering

**Key design principle:** Instance isolation over metadata filtering. Rather than storing everything in one database and filtering by source, each actor class gets its own Supabase project. This provides credential-level access control without complex RLS policies.

**Exception:** Research Brain deliberately uses table isolation within Jedi's Open Brain project rather than a separate instance. Rationale: free tier limits 2 projects, same embedding pipeline, same credential chain. Research tools are exposed on the existing `open-brain-mcp` endpoint — no separate MCP registration required. Documented in Brain-Stem CONTRACT deviation log (v0.6.1).

---

## 6. Brain Stem Integration (Make.com)

**What:** Add one HTTP POST module at the tail end of each Brain Stem destination route, after the Inbox Log PATCH completes. This is a fire-and-forget push — Brain Stem does not wait for or act on the Open Brain response.

**Where in the scenario:** After the final module in each of these chains:

- People route (primary + fallback)

- Projects route (primary + fallback)

- Ideas route (primary + fallback)

- Admin route (primary + fallback)

- Events route (primary + fallback)

- Needs Review route (primary + fallback)

- PRO bypass route

That's **13 HTTP modules** total (6 primary destinations + 6 fallback destinations + 1 PRO bypass). All identical in structure, only the pill references differ.

**Module configuration (each instance):**

```plain text
Type: HTTP > Make a request
Method: POST
URL: https://[PROJECT_REF].supabase.co/functions/v1/ingest-thought
Headers:
  x-brain-key: <<OPEN_BRAIN_ACCESS_KEY>>
  Content-Type: application/json
Body type: Raw
Content type: JSON (application/json)
Parse response: No (fire-and-forget)
```

**Body template (primary BD routes):**

```json
{
  "text": "<<CLEAN_TEXT_PILL>>",
  "metadata": {
    "source": "brain_stem",
    "destination": "<<55.destination or literal>>",
    "confidence": <<55.confidence>>,
    "classified_name": "<<55.data.name>>",
    "destination_record_id": "<<CREATE_MODULE.data.id>>"
  }
}
```

**Pill mapping per route (primary — off router 30):**

| Route | clean_text pill | destination | confidence pill | name pill | record_id pill |
| --- | --- | --- | --- | --- | --- |
| People | `21.clean_text` | `"people"` | `55.confidence` | `55.data.name` | People create module `.data.id` |
| Projects | `21.clean_text` | `"projects"` | `55.confidence` | `55.data.name` | Projects create module `.data.id` |
| Ideas | `21.clean_text` | `"ideas"` | `55.confidence` | `55.data.name` | Ideas create module `.data.id` |
| Admin | `21.clean_text` | `"admin"` | `55.confidence` | `55.data.name` | Admin create module `.data.id` |
| Events | `21.clean_text` | `"events"` | `55.confidence` | `55.data.name` | Events create module `.data.id` |
| Needs Review | `21.clean_text` | `"needs_review"` | `55.confidence` | `55.destination` | `null` |

**PRO bypass route body:**

```json
{
  "text": "<<7.clean_text>>",
  "metadata": {
    "source": "brain_stem",
    "destination": "projects",
    "confidence": 1.0,
    "prefix": "PRO:",
    "destination_record_id": "<<PRO_CREATE_MODULE.data.id>>"
  }
}
```

**Fallback routes (off OpenRouter branch):** Same structure, same pills but from the fallback Parse JSON module instead of `55`.

**Error handling:** None required. If the Open Brain push fails, Brain Stem continues normally — the capture is already in Airtable. The Open Brain push is additive, not critical path.

**Fix route:** Also add a push after fix handler creates the new record. Body uses `213` pills and `"source": "brain_stem_fix"`.

### 6.1 As-Built Report (Step 11 — March 5, 2026)

**Status:** ✅ Complete (primary routes)

**Modules built: 12** (not 13 as designed — fallback routes parked)

- 7 primary route modules: People (275), Projects (276), Events (277), Admin (278), Ideas (279), Needs Review (288), PRO bypass (289)

- 5 fix route modules: People (281), Projects (282), Ideas (283), Admin (284), Events (285)

**Module reference:**

| **Module #** | **Route** | **text field** | **record_id** |
| --- | --- | --- | --- |
| 275 | People | `55.data.name + 55.data.context` | `65.data.id` |
| 276 | Projects | `55.data.name + 55.data.next_action + 55.data.notes` | `73.data.id` |
| 277 | Events | `55.data.name + 55.data.attendees + 55.data.location + 55.data.notes` | `77.data.id` |
| 278 | Admin | `55.data.name + 55.data.notes` | `76.data.id` |
| 279 | Ideas | `55.data.name + 55.data.one_liner + 55.data.notes` | `75.data.id` |
| 288 | Needs Review | `21.clean_text` | — |
| 289 | PRO bypass | `7.clean_text` | `15.data.id` |
| 281 | fix: People | `213.name + 213.context` | `215.data.id` |
| 282 | fix: Projects | `213.name + 213.next_action + 213.notes` | `222.data.id` |
| 283 | fix: Ideas | `213.name + 213.one_liner + 213.notes` | `228.data.id` |
| 284 | fix: Admin | `213.name + 213.notes` | `231.data.id` |
| 285 | fix: Events | `213.name + 213.attendees + 213.location + 213.notes` | `234.data.id` |

All `record_id` pills confirmed. Main create modules: People (65), Projects (73), Ideas (75), Admin (76), Events (77).

**Key deviation from as-designed:** The `text` field uses Claude-extracted fields rather than raw `clean_text`. This was a deliberate improvement:

- **Primary BD routes (People, Projects, Ideas, Admin, Events):** Text is composed from `55.data.name` + destination-specific content fields (e.g., `55.data.context` for People, `55.data.next_action` + `55.data.notes` for Projects). This eliminates BD:/PRO: prefix contamination and stores richer semantic content.

- **Fix routes:** Same pattern using `213` pills. Hardcoded `confidence: 1.0`, `source: "brain_stem_fix"`.

- **Needs Review:** Uses raw `21.clean_text` (no extracted fields available — Claude returned low confidence).

- **PRO bypass:** Uses raw `7.clean_text` (no classification/extraction on this route).

**Parked/deferred:**

- Fallback routes (6 modules): Parked until primary routes are tuned through real usage

- CAL: and R: routes: Not built — routes don't exist in Brain Stem yet

- Fix route end-to-end test: Deferred to Step 12 — requires a naturally occurring misclassification

**Verified in testing:**

- 11 records in Supabase `thoughts` table

- All 6 destinations represented (people, projects, ideas, admin, events, needs_review)

- 9 `brain_stem` source entries, embeddings populating correctly

- Magi can access Open Brain via `brain_stats` and `search_thoughts`

- Full round-trip confirmed: Brain Stem capture → Supabase → Magi retrieval

**Credential tracker:** No new credentials generated. All existing Open Brain credentials remain valid.

## 7. Magi/OpenClaw Integration

Magi accesses **both** Supabase brains (see §6A). Access is via `curl` wrapped in `/bin/zsh -c '...'` subshells — environment variables for brain keys are only available in zsh (loaded from keychain via `~/.zshenv`). This is by design.

### 7.1 Dual-Brain MCP Registration

```json
{
  "mcpServers": {
    "open-brain": {
      "type": "http",
      "url": "https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/open-brain-mcp",
      "headers": {
        "x-brain-key": "<<OPEN_BRAIN_ACCESS_KEY>>"
      }
    },
    "magi-brain": {
      "type": "http",
      "url": "https://<<MAGI_BRAIN_REF>>.supabase.co/functions/v1/magi-brain-mcp",
      "headers": {
        "x-brain-key": "<<MAGI_BRAIN_ACCESS_KEY>>"
      }
    }
  }
}
```

Magi Brain exposes three tools (`search_thoughts`, `recent_thoughts`, `brain_stats`). Jedi's Open Brain (`open-brain-mcp`) exposes six: the same three plus `search_research`, `latest_research_run`, and `get_research_digest` for Research Brain retrieval. Research tools are available on the existing endpoint — no separate MCP registration needed. Magi must search **both** brains at session start — a search of one does not search the other.

### 7.2 Dual-Brain Write Routing

Magi writes to both brains. The routing rule is based on content type, not volume:

| **Content type** | **Target brain** | **metadata.source** | **Example** |
| --- | --- | --- | --- |
| Decisions made with Jedidiah | Jedi's Open Brain | `magi` | "Decided to use n8n for Phase 3 orchestration" |
| Action items assigned | Jedi's Open Brain | `magi` | "Deploy [livingsystems.earth](http://livingsystems.earth/) by end of week" |
| Project insights | Jedi's Open Brain | `magi` | "Brain Stem fix route handles multi-subject edge case" |
| People/events/things worth retrieving | Jedi's Open Brain | `magi` | "Sarah from sustainability conf — regen ag tech" |
| Operational patterns learned | Magi Brain | `magi-brain` | "Make formula fields don't evaluate in Parse JSON modules" |
| Tool usage observations | Magi Brain | `magi-brain` | "OpenClaw allow-always doesn't persist for Supabase domain" |
| Cross-session operational context | Magi Brain | `magi-brain` | "WHC deploy requires explicit credential provisioning" |

**Rule of thumb:** If Jedidiah or another system would benefit from retrieving it → Jedi's Open Brain. If only Magi would ever need it → Magi Brain. Don't duplicate across systems.

### 7.3 Direct Ingest (store_thought)

If OpenClaw supports custom HTTP tools outside MCP, add direct tool definitions for both brains:

**Jedi's Open Brain:**

```yaml
name: store_thought
description: Store a thought, decision, or insight in Jedidiah's Open Brain for shared semantic retrieval.
endpoint: https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-thought
method: POST
headers:
  x-brain-key: "<<OPEN_BRAIN_ACCESS_KEY>>"
  Content-Type: "application/json"
body_schema:
  text: string (required)
  metadata:
    source: "magi" (always)
    type: "decision|action_item|insight|context|note"
    topic: string (optional)
    session_id: string (optional)
```

**Magi Brain:**

```yaml
name: store_magi_thought
description: Store an operational pattern, learned behavior, or Magi-specific context in Magi Brain.
endpoint: https://<<MAGI_BRAIN_REF>>.supabase.co/functions/v1/magi-brain-ingest
method: POST
headers:
  x-brain-key: "<<MAGI_BRAIN_ACCESS_KEY>>"
  Content-Type: "application/json"
body_schema:
  text: string (required)
  metadata:
    source: "magi-brain" (always)
```

### 7.4 Bootstrap File Reference

Magi's `AGENTS.md` defines the full session start ritual and write routing rules. The authoritative version is maintained in Magi's workspace (see Memory section of [AGENTS.md](http://agents.md/)). Key points:

- **Session start:** Query both brains for context relevant to the current session topic

- **Write discipline:** Don't store operational noise in either Supabase brain; don't duplicate across systems

- **Access pattern:** All brain curl commands must be wrapped in `/bin/zsh -c '...'` — keys are not available in the base exec environment

## 8. Build Sequence

Execute in this order. Each step is independently testable.

| Step | What | Time | Test |
| --- | --- | --- | --- |
| ✅ 1 | Create Supabase project, enable pgvector, run SQL (table + function + RLS) | 15 min | Table visible in Table Editor, function in Database > Functions |
| ✅ 2 | Get OpenRouter API key, add $5 credits | 5 min | Key in credential tracker |
| ✅ 3 | Generate `MCP_ACCESS_KEY` (`openssl rand -hex 32`) | 1 min | Key in credential tracker |
| ✅ 4 | Set Supabase secrets: `OPENROUTER_API_KEY`, `MCP_ACCESS_KEY` | 2 min | `supabase secrets list` shows both |
| ✅ 5 | Deploy `ingest-thought` Edge Function | 10 min | `curl -X POST` with test payload returns `{"id":"...","status":"stored"}` |
| ✅ 6 | Verify storage: check Supabase Table Editor for test row with embedding | 2 min | Row exists with 1536-dim vector |
| ✅ 7 | Deploy `open-brain-mcp` Edge Function | 10 min | Claude Desktop or `curl` can call `brain_stats` and see count=1 |
| ✅ 8 | Test semantic search: call `search_thoughts` with a query related to test row | 2 min | Returns the test row with similarity > 0.5 |
| ✅ 9 | Configure Magi MCP endpoint + `store_thought` tool | 15 min | Magi can search and store |
| ✅ 10 | Test Magi round-trip: store a thought, then search for it semantically | 5 min | Stored thought returns on semantic query |
| ✅ 11 | Add HTTP POST modules to Brain Stem Make scenario (12 modules — primary + fix, fallback parked) | 45 min | 11 records in Supabase, all 6 destinations, full round-trip confirmed |
| ⏸️ 12 | Fix route end-to-end test (deferred — requires naturally occurring misclassification) | 10 min | Fix a capture, verify corrected version appears in Supabase |
| ✅ 13 | Research Brain: `research_returns` migration, `ingest-research` Edge Function deployed, dedup verified (partial unique index on `url + published_date`) | 30 min | Table exists, `ingest-research` returns `{"status":"stored"}`, duplicate → empty result set |

**Total estimated time:** ~2 hours

## 9. Credential Tracker

```plain text
=== JEDI'S OPEN BRAIN CREDENTIALS ===
Supabase Project Ref: <<SUPABASE_PROJECT_REF>>
Supabase Project URL: https://<<SUPABASE_PROJECT_REF>>.supabase.co
Supabase DB Password: <<OPEN_BRAIN_DB_PASSWORD>>
Supabase Service Role Key: (auto-available in Edge Functions)
OpenRouter API Key: <<OPENROUTER_API_KEY>>
MCP Access Key: <<OPEN_BRAIN_ACCESS_KEY>> (generated via openssl rand -hex 32)
Ingest URL: https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-thought
Research Ingest URL: https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-research
MCP URL: https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/open-brain-mcp

=== MAGI BRAIN CREDENTIALS ===
Supabase Project Ref: <<MAGI_BRAIN_REF>>
Supabase Project URL: https://<<MAGI_BRAIN_REF>>.supabase.co
Supabase DB Password: <<MAGI_BRAIN_DB_PASSWORD>>
Supabase Service Role Key: (auto-available in Edge Functions)
OpenRouter API Key: <<OPENROUTER_API_KEY>> (shared — same OpenRouter account)
MCP Access Key: <<MAGI_BRAIN_ACCESS_KEY>> (generated via openssl rand -hex 32)
Ingest URL: https://<<MAGI_BRAIN_REF>>.supabase.co/functions/v1/magi-brain-ingest
MCP URL: https://<<MAGI_BRAIN_REF>>.supabase.co/functions/v1/magi-brain-mcp
```

Each instance has its own Supabase project, DB password, and MCP access key. The OpenRouter API key is shared across both projects (same account, same billing) and is required on Jedi's Open Brain for both `ingest-thought` and `ingest-research` embedding generation.

## 10. Security Notes

- `MCP_ACCESS_KEY` is the single shared secret for both endpoints. Rotate if compromised.

- Supabase Service Role Key never leaves the Edge Function environment.

- OpenRouter API Key never leaves the Edge Function environment.

- Make.com stores the `MCP_ACCESS_KEY` as a header value in HTTP modules — treat the Make scenario as a sensitive asset.

- The `x-brain-key` header is sent over HTTPS. No additional encryption needed.

- RLS policy restricts all access to service role — no anonymous reads possible.

## 11. Cost Estimate

| Component | Unit Cost | Usage (30 captures/day + 10 Magi queries/day) | Monthly |
| --- | --- | --- | --- |
| Embeddings (write) | ~$0.02/1M tokens | ~30 captures × 200 tokens avg = 6K tokens/day | ~$0.004 |
| Embeddings (read queries) | ~$0.02/1M tokens | ~10 queries × 50 tokens avg = 500 tokens/day | ~$0.001 |
| Supabase | Free tier | Well within limits | $0 |
| OpenRouter minimum | $5 prepaid | Lasts months at this rate | ~$0.15 amortized |

**Effective monthly cost: < $0.50**

## 12. Known Limitations & Future Enhancements

**Not in this build:**

- No LLM-generated metadata at ingest time (Brain Stem and Magi supply their own)

- No deduplication on `thoughts` table (same text stored twice = two rows). Acceptable at current volume. Note: `research_returns` has dedup via partial unique index on `url + published_date`.

- No deletion/update tools exposed via MCP (manual via Supabase dashboard if needed)

- No Slack confirmation from Open Brain (Brain Stem handles its own confirmations)

- **Edge Function secret rotation requires redeploy** — Supabase Edge Functions cache secrets at deploy time. This surfaces in two scenarios: (1) After rotating any secret (e.g. `MCP_ACCESS_KEY`) via `supabase secrets set`, **all existing Edge Functions** reading it must be redeployed — they continue using the stale cached value until redeployed. (2) When deploying **anything new** — a new Edge Function (e.g. `ingest-research`), a table migration, or any `supabase db push` / `supabase functions deploy` — the deploy refreshes secrets only for the function being deployed, not for existing functions. If a secret was rotated between existing functions' last deploy and now, they silently break. Affected functions: `ingest-thought`, `open-brain-mcp`, `ingest-research`, and Magi Brain equivalents. Symptom: 401 Unauthorized on previously-working endpoints.

**Future possibilities:**

- Add `source` filter to `search_thoughts` for scoped queries ("only Brain Stem captures" or "only Magi insights")

- Passive Magi channel capture (webhook on Magi Slack channel → ingest)

- Weekly digest via Supabase scheduled function (trending topics, orphaned action items)

- Open Brain as context loader for Claude sessions (pre-load relevant thoughts into project context)

## 13. Known Issues (Carried Forward)

Issues discovered during build and integration testing, documented here for tracking. Each is also recorded in the respective project page.

### Brain Stem issues

- **Double curly brace encoding on **`clean_text`** pill** — The `21.clean_text` pill in [Make.com](http://make.com/) encodes double curly braces, producing `content` instead of raw text. Cosmetic only — does not affect Airtable storage or Open Brain ingestion.

- **Fix route command format ambiguity** — The fix route parser reads the word immediately after `fix:` as the destination keyword. Users naturally want to include context (e.g., `fix: admin dutch passport renewal...`) but the correct format is `fix: [destination]` — one word only. The re-extraction happens from the original captured message via module 209, not from the fix command text. The Slack bot reply doesn't make this format explicit enough.

- **Module 209 empty-result guard missing** — If the Airtable lookup-by-TS in module 209 returns no results (e.g., message was deleted or TS mismatch), the fix route proceeds with empty data. Needs a guard/error branch. Pre-existing issue.

### OpenClaw (Magi) issues

- **Magi defaulting to **`recent_thoughts`** instead of **`search_thoughts` — When asked to search Open Brain, Magi sometimes calls `recent_thoughts` (time-based) instead of `search_thoughts` (semantic). Behavioral — requires prompt tuning in Magi's bootstrap instructions.

- **Magi hallucinating on truncated MCP responses** — When MCP responses are truncated due to length, Magi fabricates the remaining content rather than acknowledging the truncation. Behavioral issue.

- **Allow-always not persisting for Supabase domain** — OpenClaw's allow-always permission for the Supabase domain does not persist across sessions. Requires re-approval each session. Platform limitation.

## 14. Architecture Notes

**Morning Brief — Option C (Recommended for Phase 7)**

During Step 11 integration testing, an architecture discussion was initiated regarding how Brain Stem and Magi should collaborate on daily/weekly digest delivery (Phase 7). Notion AI (Claude Opus 4.6) recommended **Option C — hybrid architecture:**

- **Brain Stem** collects structured digest data (counts, highlights, trends) and pushes to Open Brain

- **Magi** reads the digest data from Open Brain, synthesizes a natural-language brief, and delivers to #magination

- **Open Brain** serves as the bridge between the two systems, consistent with its role as the shared semantic memory layer

This avoids Brain Stem needing LLM synthesis capabilities and avoids Magi needing direct Airtable access. Flagged for Phase 7 planning.

---

*Steps 1–11 and 13 complete. Step 12 (fix route e2e test) deferred pending naturally occurring misclassification. Step 13 (Research Brain) added 2026-03-25. Fallback routes parked for future tuning. No new credentials this session.*

---
