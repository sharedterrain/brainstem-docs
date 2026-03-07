# Phase 1: Brain Dump Capture

```yaml
---
doc_id: "phase_1"
last_updated: "2026-03-07"
contract_version: "0.4.0"
---
```

**Status:** ✅ **Live** — scenario toggled to "Immediately as data arrives" Feb 23, 2026. All routes tested, OpenRouter fallback wired, linked records operational. Slack reply links added Feb 25.

**Time Estimate:** 2-3 hours

**Dependencies:** Phase 0 complete

---

## Contract References

This phase implements the following contract sections:

- **CONTRACT §3a: Functional Pipeline** — This phase implements Capture → Classification → Extraction → Storage stages

- **CONTRACT §3b: Current Provider Mapping** — Slack (capture), [Make.com](http://make.com/) (orchestration), Claude (intelligence), Airtable (storage)

- **CONTRACT §3.5: Interface Definitions** — Implements Capture Interface, Classification Interface (BD route), Extraction Interface (PRO route), Storage Interface, Memory Interface (Open Brain write path)

- **CONTRACT §5: Input Contracts** — Implements PRO: prefix detection (extraction mode) and BD: prefix detection (classification mode)

- **CONTRACT §6: Normalization Contracts** — Strips prefixes, normalizes text for LLM input

- **CONTRACT §7: Route Semantics** — PRO route guarantees destination=Projects with confidence 1.0, calls Claude for field extraction

- **CONTRACT §8: LLM Contracts** — Uses `projects_extract_v1` (Haiku) for PRO route, `brain_dump_classifier_v1` (Sonnet) for BD route

- **CONTRACT §9: Data Contracts** — Creates records in all 6 destination tables (People, Projects, Ideas, Admin, Events, Inbox Log)

- **CONTRACT §10: Invariants & Validation Rules** — Enforces confidence thresholds (≥0.60 auto-file), immutable OriginalText

- **Invariants Implemented:**
    - INV-001: One Inbox Log entry per Slack message
    - INV-002: PRO route guarantees confidence 1.0
    - INV-003: Filed status requires DestinationName + DestinationURL
    - INV-004: Confidence range 0-1
    - INV-008: Auto-file threshold 0.60

See: [CONTRACT (Brain Stem)](https://www.notion.so/cb5393105c784cc3969571a898b4f81e) v0.2.0 | [contracts/spec (Brain Stem)](https://www.notion.so/98d781fe40ed4e31a566f0d8886325fc)

---

## Overview

Build the core capture and classification logic that takes Slack messages from #brain-stem and routes them to the correct Airtable destination tables (People, Projects, Ideas, Admin, Events) with confidence scoring.

**What you're building:**

- Message parsing with prefix detection (BD:, PRO:, CAL:, R:, fix:)

- PRO: prefix extraction (guarantees destination=Projects with confidence 1.0, but still calls Claude to extract structured fields)

- Claude-based classification with structured JSON output

- Confidence threshold routing (≥0.60 auto-files, <0.60 → Needs Review)

- Airtable record creation across multiple tables

- Slack confirmation replies with Airtable record links

---

## As-Designed: Implementation Steps

---

### 📋 How This Guide Works

This guide will prompt you at **checkpoints** to record your actual [Make.com](http://make.com/) module numbers. You'll fill in a simple reference table, then copy-paste formulas with the correct numbers.

**No manual tracking needed** - just answer the prompts when you see "✋ CHECKPOINT" sections.

---

**Pre-Build Checklist**

Before starting Phase 1, gather these items:

**API Keys & Tokens:**

- [ ] Claude API key (starts with `sk-ant-`)

- [ ] Airtable Personal Access Token (starts with `pat`)

- [ ] Slack Bot Token (starts with `xoxb-`)

**Airtable IDs (from Phase 0):**

- [ ] Base ID (starts with `app`, found in URL)

- [ ] Table IDs for: People, Projects, Ideas, Admin, Events, Inbox Log (each starts with `tbl`)

- [ ] Default View ID for each table (starts with `viw`, found in URL)

**Current Context:**

- [ ] Webhook URL: [<<MAKE_WEBHOOK_URL>>](%3C%3CMAKE_WEBHOOK_URL%3E%3E)

### Scenario D — Fix (Slack threaded reply containing `fix:`)

**Trigger**

- Threaded reply in `#bs-inbox` containing `fix:`

- [ ] [Make.com](http://make.com/) organization: [<<MAKE_ORG_NAME>>](http:///%3C%3CMAKE_ORG_NAME%3E%3E)

**Verification:**

- [ ] Phase 0 webhook test successful (messages flowing to [Make.com](http://make.com/))

- [ ] Brain Dump Classifier v1.0.0 prompt accessible in Notion Prompt Library

---

### Prerequisites

Before starting Phase 1:

- ✅ Phase 0 complete (webhook verified and receiving messages)

- ✅ Brain Dump Classifier v1.0.0 prompt ready in Prompt Library

- ✅ Claude API key available

- ✅ Airtable connections configured in [Make.com](http://make.com/)

---

### Step 1: [[Make.com](http://make.com/)] Create [Make.com](http://make.com/) Connections

**Time:** 10 minutes | **Status:** Pending

<!-- unsupported block type: heading_4 -->

- In [Make.com](http://make.com/), go to Connections (left sidebar)

- Click "Add" → Search "HTTP"

- Name: "Claude API - Brain Stem"

- You'll configure headers in each HTTP module (no persistent connection needed)

<!-- unsupported block type: heading_4 -->

- Click "Add" → Search "Airtable"

- Select "Airtable"

- Name: "Airtable - Brain Stem"

- Authentication: Enter your Personal Access Token (from Phase 0 Step 1.9)

- Test connection

- Click "Save"

<!-- unsupported block type: heading_4 -->

- Click "Add" → Search "Slack"

- Select "Slack"

- Name: "Slack - Brain Stem"

- Authentication: OAuth (click "Sign in with Slack")

- Or use Bot Token: Your `xoxb-...` token from Phase 0

- Test connection

- Click "Save"

---

### Step 2: [[Make.com](http://make.com/)] Add Prefix Detection Router

**Time:** 15 minutes | **Status:** Pending

Open your "Brain Stem - Capture" scenario from Phase 0.

<!-- unsupported block type: heading_4 -->

- After the Webhook Response module, click "+"

- Search for "Router"

- Add "Flow Control > Router"

- This creates multiple parallel paths

<!-- unsupported block type: heading_4 -->

- Click first route label → Rename to "PRO: Projects Bypass"

- Click "Set up a filter"
    - Label: "Starts with PRO:"
    - Condition: `event.text`
    - Operator: Text operators > "Matches pattern (case insensitive)"
    - Pattern: `^PRO:`
    - Click "OK"

<!-- unsupported block type: heading_4 -->

- Click second route → Rename to "CAL: Events"

- Add filter:
    - Label: "Starts with CAL:"
    - Condition: `event.text`
    - Pattern: `^CAL:`

- Add placeholder module: "Tools > Set variable"
    - Variable name: `route_type`
    - Value: `calendar`

- *(Will build out in Phase 4)*

<!-- unsupported block type: heading_4 -->

- Click third route → Rename to "R: Research"

- Add filter:
    - Label: "Starts with R:"
    - Pattern: `^R:`

- Add placeholder module: "Tools > Set variable"
    - Variable name: `route_type`
    - Value: `research`

- *(Will build out in Phase 3)*

<!-- unsupported block type: heading_4 -->

- Click fourth route → Rename to "fix: Corrections"

- Add filter:
    - Label: "Starts with fix:"
    - Pattern: `^fix:`

- Add placeholder module: "Tools > Set variable"
    - Variable name: `route_type`
    - Value: `correction`

- *(Will build out in Phase 2)*

<!-- unsupported block type: heading_4 -->

- Click fifth route → Rename to "BD: Brain Dumps"

- Add filter:
    - Label: "Default brain dump"
    - Condition: `event.text`
    - Operator: "Does not match pattern"
    - Pattern: `^(PRO:|CAL:|R:|fix:)`
    - Click "OK"

- This catches everything else (BD: prefix or no prefix)

---

### Step 3: [[Make.com](http://make.com/)] Build PRO: Extraction Path (Route 1)

**Time:** 20 minutes | **Status:** Pending

This path guarantees destination=Projects, but still calls Claude API to extract structured fields (Name, Type, Status, Next Action, Notes, Tags).

<!-- unsupported block type: heading_4 -->

- On Route 1 (PRO:), click "+" after filter

- Add "Tools > Set variable"

**Variable 1: clean_text**

- Name: `clean_text`

- Value: `replace(event.text; "PRO:"; "")` (removes prefix)

**Variable 2: project_type**

- Name: `project_type`

- Formula:

```javascript
if(
  contains(lower(event.text), "installation") or 
  contains(lower(event.text), "exhibition") or 
  contains(lower(event.text), "fabrication") or 
  contains(lower(event.text), "gallery"),
  "Physical",
  if(
    contains(lower(event.text), "article") or 
    contains(lower(event.text), "video") or 
    contains(lower(event.text), "website") or 
    contains(lower(event.text), "blog"),
    "Digital",
    "Digital"
  )
)
```

**Note:** This simplified logic checks for physical keywords first, then digital, defaulting to Digital. Hybrid projects would need both keywords present - you can add manual override later if needed.

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Airtable > Create a record"

- Connection: "Airtable - Brain Stem"

- Base: "Brain Stem"

- Table: "Inbox Log"

- Fields:
    - Original Text: `event.text`
    - Filed To: `Projects`
    - Confidence: `1`
    - Status: `Filed`
    - Slack Channel: [`event.channel`](http://event.channel/)
    - Slack Message TS: `event.ts`
    - Slack Thread TS: `event.ts`
    - Captured At: `now`

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Airtable > Create a record"

- Connection: "Airtable - Brain Stem"

- Base: "Brain Stem"

- Table: "Projects"

- Fields:
    - Name: `3.clean_text` (first 100 chars or extract title)
    - Type: `3.project_type`
    - Status: `Active`
    - Next Action: `3.clean_text`
    - Last Touched: `now`
    - Tags: `slack-capture`

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Airtable > Update a record"

- Record ID: [`2.id`](http://2.id/) (from Inbox Log create)

- Fields:
    - Destination Name: [`4.fields.Name`](http://4.fields.name/)
    - Destination URL: [[[[[[[[[[[`https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id`]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))]([https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id))

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Slack > Create a message"

- Connection: "Slack - Brain Stem"

- Channel: [`event.channel`](http://event.channel/)

- Text:

```javascript
✅ Filed to **Projects** (PRO: bypass)
*4.fields.Name*
Type: 4.fields.Type
Confidence: 1.0

[View in Airtable](https://airtable.com/[BASE_ID]/[PROJECTS_TABLE_ID]/[VIEW_ID]/4.id)
```

- Thread TS: `event.ts`

- As user: No

---

### Step 4: [[Make.com](http://make.com/)] Build Brain Dump Classification Path (Route 5)

**Time:** 45 minutes | **Status:** Pending

This is the main path using Claude.

<!-- unsupported block type: heading_4 -->

- On Route 5 (Brain Dumps), click "+" after filter

- Add "Tools > Set variable"

- Name: `clean_text`

- Value: `replace(event.text; "BD:"; "")`

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Airtable > Create a record"

- Table: "Inbox Log"

- Fields:
    - Original Text: `event.text`
    - Status: `Processing`
    - Slack Channel: [`event.channel`](http://event.channel/)
    - Slack Message TS: `event.ts`
    - Slack Thread TS: `event.ts`
    - Captured At: `now`

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Tools > Set variable"

- Name: `message_length`

- Value: `length(trim(9.clean_text))`

- Click wrench icon on this module → "Set up a filter"
    - Condition: `message_length` > 0
    - This prevents empty messages from reaching Claude API

<!-- unsupported block type: heading_4 -->

> ⚠️ **As-Built supersedes As-Designed for classifier prompt.** The current production prompt is embedded in module 48 — see As-Built section for the authoritative version including Events fields (`start_time`, `end_time`, `attendees`, `location`) added Feb 25.

- Click "+"

- Add "HTTP > Make a request"

**⚠️ Note the module number **[**Make.com**](http://make.com/)** assigns** - you'll need it in the next checkpoint.

- URL: [`https://api.anthropic.com/v1/messages`](https://api.anthropic.com/v1/messages)

- Method: POST

- Headers (click "Add item" for each):
    - `x-api-key`: `[Your Claude API key from Pre-Build Checklist]`
    - `anthropic-version`: `2023-06-01`
    - `content-type`: `application/json`

- Body type: Raw

- Content type: JSON (application/json)

- Request content:

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 500,
  "temperature": 0.3,
  "messages": [
    {
      "role": "user",
      "content": "You are a classification assistant for a creative professional's Brain Stem system.\n\n**CONTEXT:**\nThe user is a multimedia creator working across print, video, presentations, and physical installations. Their work focuses on:\n- AI and creativity\n- Sustainable design and regenerative systems\n- Human-AI collaboration\n- Traditional ecological knowledge integrated with modern technology\n- Speculative futures\n\nThey publish on LinkedIn (thought leadership), Substack (long-form essays), personal blog (portfolio/process), and create physical exhibition documentation.\n\n**YOUR TASK:**\nClassify the following brain dump into ONE of these categories:\n\n1. **PEOPLE** - Mentions a person by name, includes contact info, describes relationship context, or notes follow-up actions with someone\n2. **PROJECTS** - Active work with status, executable next action, blocked/waiting dependencies, or project-specific notes\n   - **Digital projects:** Keywords like 'article', 'video edit', 'website', 'script', 'blog post', 'social media'\n   - **Physical projects:** Keywords like 'installation', 'exhibition', 'fabrication', 'gallery', 'sculpture', 'build'\n   - **Hybrid projects:** Contains both digital and physical keywords\n3. **IDEAS** - Concepts without immediate action, brainstorms, inspiration, \"someday/maybe\" thoughts, creative directions\n4. **ADMIN** - Tasks with deadlines, administrative to-dos, one-time action items, personal errands\n5. **EVENTS** - Meetings, appointments, deadlines with time, calendar-based reminders, scheduled gatherings\n\n**EDGE CASES:**\n- **Empty message or only whitespace:** Set destination to \"needs_review\", confidence 0.0, reason \"Empty message\"\n- **Non-English message:** Attempt classification, but if uncertain, set destination to \"needs_review\", confidence below 0.60, reason \"Non-English content requires manual review\"\n- **Image/attachment only (no text):** Set destination to \"needs_review\", confidence 0.0, reason \"No text content to classify\"\n- **Multiple distinct items:** Set destination to \"needs_review\", confidence below 0.60, reason \"Contains multiple topics requiring separate captures\"\n\n**OUTPUT FORMAT (raw JSON with no code block formatting):**\n\n{\n  \"destination\": \"people|projects|ideas|admin|events|needs_review\",\n  \"confidence\": 0.85,\n  \"data\": {\n    \"name\": \"Clear, descriptive title\",\n    \"context\": \"For PEOPLE: relationship and interaction notes\",\n    \"follow_ups\": \"For PEOPLE: specific next actions with this person\",\n    \"status\": \"For PROJECTS: active|waiting|blocked|someday|done\",\n    \"next_action\": \"For PROJECTS: Specific executable action\",\n    \"notes\": \"For PROJECTS/IDEAS/EVENTS: Additional context\",\n    \"one_liner\": \"For IDEAS: Core insight in one sentence\",\n    \"due_date\": \"For ADMIN/EVENTS: YYYY-MM-DD or null\",\n    \"tags\": [\"relevant\", \"tags\"],\n    \"project_type\": \"For PROJECTS: digital|physical|hybrid (based on keywords above)\"\n  },\n  \"reason\": \"Brief explanation of why this classification and confidence score\"\n}\n\n**CONFIDENCE SCORING RULES:**\n- 0.85-1.0: Very clear classification, all key info present\n- 0.70-0.84: Clear classification, some ambiguity or missing details\n- 0.60-0.69: Reasonable classification, notable uncertainty\n- Below 0.60: Route to \"needs_review\" - too ambiguous or contains multiple distinct items\n\n**BRAIN DUMP TO CLASSIFY:**\n" + 9.clean_text
    }
  ]
}
```

**⚠️ PAUSE HERE:** What module number did [Make.com](http://make.com/) assign to your "Strip BD: Prefix" module from Step 4.1? Replace `9.clean_text` with `[YOUR_NUMBER].clean_text` in the formula above.

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Tools > Parse JSON"

- JSON string: `[CLAUDE_API_MODULE_NUMBER].data.content[0].text`

**⚠️ PAUSE HERE:** What module number did [Make.com](http://make.com/) assign to the HTTP module you just created in Step 4.4? Replace `[CLAUDE_API_MODULE_NUMBER]` with that number.

**⚠️ CRITICAL:** Use `content[0]` not `content[1]` - array indexing starts at 0.

- Data structure: Leave auto

---

### ✋ CHECKPOINT 1: Record Your Core Module Numbers

**Stop and fill this in before proceeding to Step 4.7:**

Open a text file or Notion page and record these:

```javascript
=== MY MODULE NUMBERS ===

Clean Text (Strip BD: Prefix) = Module #____
Inbox Log (Create Record) = Module #____  
Claude API = Module #____
Text Parser Replace 1 = Module #____
Text Parser Replace 2 = Module #____
Parse JSON = Module #____
```

**Example:**

```javascript
Clean Text (Strip BD: Prefix) = Module #7
Inbox Log (Create Record) = Module #8
Claude API = Module #10
Text Parser Replace 1 = Module #12
Text Parser Replace 2 = Module #13
Parse JSON = Module #11
```

> ⚠️ **Note:** Actual module numbers will vary depending on your build order and any modules added/removed during troubleshooting. The **As-Built: Actual Implementation Notes** section at the bottom of this page contains the definitive module reference table for the current scenario.

You'll use these numbers to build all 6 destination routes in the next step.

---

<!-- unsupported block type: heading_4 -->

**Before building destination routes, collect IDs for ALL 12 tables:**

Create a text file or Notion page with your Airtable IDs. You'll use some now (Phase 1) and the rest in later phases.

```javascript
Base ID: app[YOUR_BASE_ID]

=== PHASE 1 TABLES (needed now) ===
Table IDs:
- People: tbl______
- Projects: tbl______
- Ideas: tbl______
- Admin: tbl______
- Events: tbl______
- Inbox Log: tbl______

View IDs:
- People Default View: viw______
- Projects Default View: viw______
- Ideas Default View: viw______
- Admin Default View: viw______
- Events Default View: viw______
- Inbox Log Default View: viw______

=== FUTURE PHASE TABLES (collect now, use later) ===
Table IDs:
- Research Jobs: tbl______ (Phase 3)
- Articles: tbl______ (Phase 3)
- Drafts: tbl______ (Phase 4)
- Publications: tbl______ (Phase 5)
- Metrics: tbl______ (Phase 6)
- Runs: tbl______ (used across all phases for logging)

View IDs:
- Research Jobs Default View: viw______ (Phase 3)
- Articles Default View: viw______ (Phase 3)
- Drafts Default View: viw______ (Phase 4)
- Publications Default View: viw______ (Phase 5)
- Metrics Default View: viw______ (Phase 6)
- Runs Default View: viw______ (all phases)
```

**How to get View IDs:**

1. Open Airtable table in browser

1. Copy URL: [[[[[[[[[`airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]`]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))]([http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]](http://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]))

1. The third segment starting with `viw` is your View ID

<!-- unsupported block type: heading_4 -->

- Click "+"

- Add "Flow Control > Router"

- This creates 6 sub-routes:
    1. People (confidence ≥ 0.60)
    1. Projects (confidence ≥ 0.60)
    1. Ideas (confidence ≥ 0.60)
    1. Admin (confidence ≥ 0.60)
    1. Events (confidence ≥ 0.60)
    1. Needs Review (confidence < 0.60 OR destination = needs_review)

---

### Step 5: [Airtable] [Slack] Build Destination Routes (6 paths)

**Time:** 60 minutes | **Status:** Pending

Repeat this pattern for each destination:

<!-- unsupported block type: heading_4 -->

**Filter:**

- Condition 1: `[PARSE_JSON_MODULE].destination` = `people`

- AND Condition 2: `[PARSE_JSON_MODULE].confidence` ≥ `0.60`

**⚠️ PAUSE:** Replace `[PARSE_JSON_MODULE]` with your actual Parse JSON module number from Checkpoint 1.

**Modules:**

**A. Create People Record**

- Airtable > Create a record

- Table: "People"

- Fields:
    - Name: `[PARSE_JSON_MODULE].`[`data.name`](http://data.name/)
    - Context: `[PARSE_JSON_MODULE].data.context`
    - Follow-ups: `[PARSE_JSON_MODULE].data.follow_ups`
    - Last Touched: `now`
    - Tags: `join([PARSE_JSON_MODULE].data.tags; ",")`

**⚠️ Note:** [Make.com](http://make.com/) will assign this "Create People Record" module a number - you'll need it for the next two steps.

**B. Update Inbox Log**

- Airtable > Update a record

- Record ID: `[INBOX_LOG_MODULE].id`

- Fields:
    - Filed To: `People`
    - Destination Name: `[PEOPLE_RECORD_MODULE].`[`fields.Name`](http://fields.name/)
    - Destination URL: [[[[[[[[`https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id`]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))]([https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id))
    - Confidence: `[PARSE_JSON_MODULE].confidence`
    - Status: `Filed`
    - AI Output Raw: `[CLAUDE_API_MODULE].data.content[0].text`

**⚠️ PAUSE - Fill in these placeholders:**

- `[INBOX_LOG_MODULE]` = Your "Create Inbox Log" module number from Checkpoint 1

- `[PEOPLE_RECORD_MODULE]` = The "Create People Record" module number you just created in Step 5.1A

- `[PARSE_JSON_MODULE]` = Your Parse JSON module number from Checkpoint 1

- `[CLAUDE_API_MODULE]` = Your Claude API module number from Checkpoint 1

- Get [BASE_ID], [PEOPLE_TABLE_ID], [VIEW_ID] from Step 4.6 reference

**C. Reply in Slack**

- Slack > Create a message

- Text:

```javascript
✅ Filed to **People**
*[PEOPLE_RECORD_MODULE].fields.Name*
Confidence: formatNumber([PARSE_JSON_MODULE].confidence; 2)

[View in Airtable](https://airtable.com/[BASE_ID]/[PEOPLE_TABLE_ID]/[VIEW_ID]/[PEOPLE_RECORD_MODULE].id)

Reply "fix: [correction]" if wrong.
```

- Thread TS: `event.ts`

**⚠️ PAUSE - Fill in these placeholders:**

- `[PEOPLE_RECORD_MODULE]` = Your "Create People Record" module number from Step 5.1A

- `[PARSE_JSON_MODULE]` = Your Parse JSON module number from Checkpoint 1

- Get [BASE_ID], [PEOPLE_TABLE_ID], [VIEW_ID] from Step 4.6 reference

---

**✅ People route complete!** Routes 5.2-5.5 follow the same pattern.

---

<!-- unsupported block type: heading_4 -->

**Filter:**

- `11.destination` = `projects`

- AND `11.confidence` ≥ `0.60`

**A. Create Projects Record**

- Table: "Projects"

- Fields:
    - Name: [`11.data.name`](http://11.data.name/)
    - Type: [`11.data`](http://11.data/)`.project_type`
    - Status: [`11.data`](http://11.data/)`.status`
    - Next Action: [`11.data.next`](http://11.data.next/)`_action`
    - Notes: [`11.data`](http://11.data/)`.notes`
    - Last Touched: `now`
    - Tags: `join(`[`11.data`](http://11.data/)`.tags; ",")`

**B. Update Inbox Log**

- Same pattern as People route (Step 5.1B)

- Replace People table IDs with Projects table IDs

**C. Reply in Slack**

- Same pattern as People route (Step 5.1C)

- Replace "People" with "Projects" in message text

- Use Projects table IDs

---

<!-- unsupported block type: heading_4 -->

**Filter:**

- `11.destination` = `ideas`

- AND `11.confidence` ≥ `0.60`

**A. Create Ideas Record**

- Table: "Ideas"

- Fields:
    - Name: [`11.data.name`](http://11.data.name/)
    - One-Liner: [`11.data.one`](http://11.data.one/)`_liner`
    - Notes: [`11.data`](http://11.data/)`.notes`
    - Last Touched: `now`
    - Tags: `join(`[`11.data`](http://11.data/)`.tags; ",")`

**B. Update Inbox Log**

- Same pattern as People route (Step 5.1B)

- Replace People table IDs with Ideas table IDs

**C. Reply in Slack**

- Same pattern as People route (Step 5.1C)

- Replace "People" with "Ideas" in message text

- Use Ideas table IDs

---

<!-- unsupported block type: heading_4 -->

**Filter:**

- `11.destination` = `admin`

- AND `11.confidence` ≥ `0.60`

**A. Create Admin Record**

- Table: "Admin"

- Fields:
    - Name: [`11.data.name`](http://11.data.name/)
    - Due Date: [`11.data`](http://11.data/)`.due_date`
    - Status: `Todo`
    - Notes: [`11.data`](http://11.data/)`.notes`
    - Created: `now`

**B. Update Inbox Log**

- Same pattern as People route (Step 5.1B)

- Replace People table IDs with Admin table IDs

**C. Reply in Slack**

- Same pattern as People route (Step 5.1C)

- Replace "People" with "Admin" in message text

- Use Admin table IDs

---

<!-- unsupported block type: heading_4 -->

**Filter:**

- `11.destination` = `events`

- AND `11.confidence` ≥ `0.60`

**A. Create Events Record**

- Table: "Events"

- Fields:
    - Name: [`11.data.name`](http://11.data.name/)
    - Event Type: `Meeting` (default)
    - Notes: [`11.data`](http://11.data/)`.notes`
    - Created: `now`

**B. Update Inbox Log**

- Same pattern as People route (Step 5.1B)

- Replace People table IDs with Events table IDs

**C. Reply in Slack**

- Same pattern as People route (Step 5.1C)

- Replace "People" with "Events" in message text

- Use Events table IDs

---

<!-- unsupported block type: heading_4 -->

**Filter:**

- No filter OR fallback route

- Catches: confidence < 0.60, destination = needs_review, errors

**A. Update Inbox Log**

- Record ID: `[YOUR_MODULE_NUMBER].id` (from Create Inbox Log)

- Fields:
    - Filed To: `Needs Review`
    - Status: `Needs Review`
    - Confidence: `[YOUR_MODULE_NUMBER].confidence` (from Parse JSON)
    - AI Output Raw: `[YOUR_MODULE_NUMBER].data.content[0].text` (from Claude API)

**B. Reply in Slack**

- Text:

```javascript
⚠️ Needs Manual Review
Confidence too low (formatNumber([YOUR_MODULE_NUMBER].confidence; 2))

Claude suggested: [YOUR_MODULE_NUMBER].destination
Reason: [YOUR_MODULE_NUMBER].reason

Review in Airtable: https://airtable.com/[BASE_ID]/[INBOX_TABLE_ID]/[VIEW_ID]/[YOUR_MODULE_NUMBER].id

Reply with classification or "fix: [destination]" to refile.
```

---

### Step 6: [[Make.com](http://make.com/)] Add Error Handling

**Time:** 15 minutes | **Status:** Pending

<!-- unsupported block type: heading_4 -->

- Click module 10 (HTTP - Claude API)

- Click wrench icon → "Add error handler"

- Add "Tools > Set variable"
    - Name: `error_type`
    - Value: `claude_api_error`
    - Name: `error_message`
    - Value: `10.error.message`

<!-- unsupported block type: heading_4 -->

- After error handler, add "Airtable > Update a record"

- Record ID: [`8.id`](http://8.id/)

- Fields:
    - Status: `Error`
    - Error Details: `Claude API failed: error_message`

<!-- unsupported block type: heading_4 -->

- Add "Slack > Create a message"

- Text:

```javascript
❌ Classification Error
The AI couldn't process this message.

Error: error_message

Your capture is logged. Reply "fix: [destination]" to manually file.
```

---

### Step 7: Test End-to-End

**Time:** 30 minutes | **Status:** Pending

<!-- unsupported block type: heading_4 -->

- Click "Scheduling" (bottom left)

- Toggle: ON

- Trigger: Instantly (webhook)

- Click "OK"

<!-- unsupported block type: heading_4 -->

In #brain-stem Slack channel:

```javascript
PRO: Landing page redesign - next: wireframe homepage and schedule design review
```

**Expected:**

- Routes to PRO: path

- Creates Projects record with Type = "Digital"

- Confidence = 1.0

- Slack reply confirms

<!-- unsupported block type: heading_4 -->

```javascript
Met Sarah at the sustainability conference - she's working on regenerative agriculture tech. Follow up next week about potential collaboration.
```

**Expected:**

- Routes to Brain Dump path

- Claude classifies as People

- Confidence ≥ 0.60

- Creates People record

- Slack reply with link

<!-- unsupported block type: heading_4 -->

```javascript
BD: Exhibition installation guide - Status: active, Next: photograph assembly process and write step-by-step documentation
```

**Expected:**

- Classified as Projects

- Type = "Physical" or "Hybrid"

- Status = "Active"

- Next Action extracted

<!-- unsupported block type: heading_4 -->

```javascript
What if we created an AI that generates architectural forms based on local ecosystem patterns?
```

**Expected:**

- Classified as Ideas

- One-liner extracted

<!-- unsupported block type: heading_4 -->

```javascript
Renew car registration by March 15
```

**Expected:**

- Classified as Admin

- Due date parsed: 2026-03-15

<!-- unsupported block type: heading_4 -->

```javascript
Call Alex about the project and also remember to buy groceries and maybe we should write that article
```

**Expected:**

- Low confidence (multiple items)

- Routes to Needs Review

- Slack prompts for manual review

<!-- unsupported block type: heading_4 -->

- Check Airtable Inbox Log table

- All 7 test messages should appear

- Confidence scores logged

- Links to destination records

---

### Step 8: Document Configuration

**Time:** 10 minutes | **Status:** Pending

<!-- unsupported block type: heading_4 -->

Add to Configuration Registry page:

- Scenario name: "Brain Stem - Capture"

- Module count: ~35 modules

- Active routes: PRO:, BD: (default)

- Placeholder routes: CAL:, R:, fix:

- Claude model: claude-3-5-sonnet-20241022

- Average execution time: 2-4 seconds

- Cost per capture: ~$0.002

<!-- unsupported block type: heading_4 -->

- Take screenshot of full scenario flow

- Save to Product Archive

- Annotate key decision points

---

## Testing Checklist

**Prefix Detection:**

- [ ] PRO: routes to Projects bypass

- [ ] BD: routes to Claude classification

- [ ] No prefix routes to Claude classification

- [ ] CAL: placeholder works

- [ ] R: placeholder works

- [ ] fix: placeholder works

**Classification Accuracy:**

- [ ] People mentions with names → People table

- [ ] Projects with next actions → Projects table

- [ ] Projects with "installation" keyword → Type = Physical

- [ ] Projects with "article" keyword → Type = Digital

- [ ] Ideas without actions → Ideas table

- [ ] Tasks with deadlines → Admin table

- [ ] Meetings/appointments → Events table

- [ ] Ambiguous messages → Needs Review

**Data Integrity:**

- [ ] All messages logged in Inbox Log

- [ ] Confidence scores recorded correctly

- [ ] Destination links populate

- [ ] Slack thread TS captured for fix: replies

**Slack Confirmations:**

- [ ] Success messages include Airtable links

- [ ] Confidence scores display

- [ ] Needs Review messages explain why

- [ ] Error messages are helpful

**Edge Cases:**

- [ ] Empty message → Needs Review

- [ ] Very long message (>500 words) → Processes

- [ ] Special characters and emojis → Handles correctly

- [ ] Multiple messages rapid-fire → All process

---

## Common Issues & Solutions

### Issue: Claude returns markdown-wrapped JSON

**Symptom:** Parse JSON module fails with "Source is not valid JSON" error. Inspecting the input shows Claude's response wrapped in markdown code fences (triple backticks + "json" header and trailing triple backticks).

**Root cause:** Claude models consistently wrap JSON output in markdown code fences regardless of prompt instructions. This is a known model behavior, not a prompt issue.

**Solution: Position-based regex replacement (two-step Text Parser)**

Add two **Text Parser > Replace** modules between the Claude API module and Parse JSON:

**Text Parser Replace 1 (strip prefix):**

- Pattern: `^[\s\S]*?\{`

- New value: `{`

- Global match: No

- Singleline: **Yes**

- Text: mapped from Claude module's Text Response output

- *Matches everything from start of string up to and including the first *`{`*, replaces with just *`{`

**Text Parser Replace 2 (strip suffix):**

- Pattern: `\}[^}]*$`

- New value: `}`

- Global match: No

- Singleline: **Yes**

- Text: mapped from first Text Parser's Text output

- *Matches the last *`}`* followed by any non-*`}`* characters to end of string, replaces with just *`}`

**Then point Parse JSON's JSON string field** at the second Text Parser's Text output.

**Why this works:** Instead of trying to match backtick characters (which Make cannot handle in formulas or regex due to syntax conflicts), these patterns match by position — "everything before the first `{`" and "everything after the last `}`". The backtick characters are never referenced directly.

> ⚠️ **Greedy regex warning:** Do NOT use `\}[\s\S]*$` for the second pattern — it matches from the FIRST `}` (inside nested objects like `data: {...}`) instead of the last one, cutting off fields like `reason`. The pattern `\}[^}]*$` ensures only the final `}` is matched because `[^}]*` cannot cross another `}` character.

**Approaches that were tried and failed:**

1. Prompt engineering ("start with {, no backticks") — Claude ignores consistently

1. Text Parser > Match Pattern with regex `\{[\s\S]*\}` — output was Empty

1. Text Parser > Replace with literal backtick matching — produced `null` values instead of clean removal

1. `replace()` function in Set variable or Parse JSON fields — Make treated formula as literal text due to backtick syntax conflicts

1. Anthropic module JSON Schema output format — "Grammar compilation timed out" error

1. `substring()` / `indexOf()` in Set variable — treated as literal text, not evaluated

### Issue: [Make.com](http://make.com/) formulas treated as literal text in certain module fields

**Symptom:** Formulas like `replace()`, `substring()`, and `indexOf()` appear as literal text in module output instead of being evaluated. Commonly encountered when trying to use these functions in Parse JSON's JSON string field, or when the search/replace strings contain backtick characters.

**Root cause:** Not all [Make.com](http://make.com/) module fields support formula evaluation. Parse JSON's JSON string field only accepts mapped values, not formulas. Additionally, backtick characters conflict with Make's formula syntax (backticks are used as field name delimiters).

**Solution:** Use **Text Parser > Replace** modules with regex patterns instead of inline formulas. Text Parser modules reliably evaluate regex and produce clean mapped output that other modules can consume.

---

### Issue: Confidence always showing as 0.00

**Symptom:** Inbox Log shows confidence = 0

**Solution:**

- Check Parse JSON output structure

- Verify mapping: Should be `11.confidence`, not [`11.data`](http://11.data/)`.confidence`

### Issue: Airtable links broken in Slack

**Symptom:** Links don't navigate to correct record

**Solution:**

- Verify URL format: [[[[[[[[[[[`https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]`]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))]([https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]](https://airtable.com/[BASE_ID]/[TABLE_ID]/[VIEW_ID]/[RECORD_ID]))

- Get VIEW_ID from Airtable URL when viewing table

- Make sure RECORD_ID uses `id` from create module

### Issue: PRO: bypass creates project with "PRO:" in title

**Symptom:** Project name includes prefix

**Solution:**

- Check "Strip Prefix" module (Step 3.1)

- Verify replace() function removes prefix correctly

### Issue: Tags not appearing in Airtable

**Symptom:** Tags field empty even though Claude returned tags

**Solution:**

- Check mapping uses `join(`[`11.data`](http://11.data/)`.tags; ",")`

- Verify Claude returns array: `["tag1", "tag2"]`

- May need to create tags in Airtable first if field is restricted

---

## Performance Notes

**Expected Metrics:**

- Execution time: 2-4 seconds per capture

- [Make.com](http://make.com/) operations: ~8-12 per capture

- Claude API cost: ~$0.002 per capture

- Monthly cost (30 captures/day): ~$1.80 Claude + $9 [Make.com](http://make.com/) Core

**Optimization Opportunities:**

- PRO: bypass saves ~$0.002 and 2 seconds per project capture

- Batch processing not recommended - instant feedback is key UX

- Consider caching People/Projects for duplicate detection in Phase 2

---

## As-Built: Actual Implementation Notes

**Phase 1: Brain Dump Capture — As-Built Report**

**Date:** February 20, 2026 (updated February 21, 2026)

**Status:** ✅ **Live** (toggled to "Immediately as data arrives" — Feb 23, 2026)

**contract_version:** 0.2.0

### Go-Live — Feb 23, 2026

- **Status changed from:** Functional — all routes tested → **Live**

- **Final punch list completed:** Test records cleared, scenario toggled to "Immediately as data arrives", Config Registry updated

- **Deferred items still outstanding:** AI Output Raw in PATCH bodies, PRO route Claude extraction

- **Known edge case carried to Phase 2:** Multi-subject messages route to the first category mentioned (e.g. People) instead of flagging for review, even when the message contains two or more other potential categories. Use as few-shot ground truth for tuning.

- **Phase 2 next:** fix: handler, few-shot tuning, calibration loop, weekly digest

- **Post-launch discovery (Feb 25):** Slack confirmation replies missing Airtable record links. Required per original spec. Resolved Feb 25.

### Updates — Feb 25, 2026

- **Field mapping resolved across all 5 main CREATE modules.** Token format confirmed as picker-mapped `55. data: fieldname` — dot notation pills do not resolve. All 5 routes tested and passing.

- **Admin table:** Created field is computed — cannot be written via API. Removed from CREATE body.

- **Events table:** Attendees changed from linked record to Long Text. Classifier prompt updated with four new Events fields: `start_time`, `end_time`, `attendees`, `location`. Start/end format: ISO 8601 UTC with America/Vancouver inference.

- **Tags deferred:** Tags field type changed to Long Text across all destination tables. Claude continues returning tags array; not written to Airtable at capture time. Will be generated by Airtable AI during enrichment pass (phase TBD).

- **Slack reply links fixed:** Airtable record links were missing from Slack confirmation replies at launch. Added Feb 25.

### Open Brain Write Path — Mar 7, 2026

7 fire-and-forget HTTP POST modules added to write captured thoughts to Open Brain (Supabase Edge Function `ingest-thought`). See CONTRACT §3.5 Memory Interface for the full interface definition.

**All modules share:**

- Method: POST

- URL: `https://<<SUPABASE_PROJECT_REF>>.supabase.co/functions/v1/ingest-thought`

- Header: `x-brain-key: <<MCP_ACCESS_KEY>>`

- Body content type: application/json

- Body input method: JSON string

- Parse response: No (fire-and-forget)

**Primary routes (off router 30):**

| **Route** | **text field** | **destination** | **source** | **confidence** | **record_id** |
| --- | --- | --- | --- | --- | --- |
| People | `55.data.name + 55.data.context` | people | brain_stem | `55.confidence` | `65.data.id` |
| Projects | `55.data.name + 55.data.next_action + 55.data.notes` | projects | brain_stem | `55.confidence` | projects create module |
| Ideas | `55.data.name + 55.data.one_liner + 55.data.notes` | ideas | brain_stem | `55.confidence` | ideas create module |
| Admin | `55.data.name + 55.data.notes` | admin | brain_stem | `55.confidence` | admin create module |
| Events | `55.data.name + 55.data.attendees + 55.data.location + 55.data.notes` | events | brain_stem | `55.confidence` | events create module |
| Needs Review | `21.clean_text` | needs_review | brain_stem | `55.confidence` | — |

**PRO bypass route:**

| **Route** | **text field** | **destination** | **source** | **confidence** | **prefix** | **record_id** |
| --- | --- | --- | --- | --- | --- | --- |
| PRO bypass | `7.clean_text` | projects | brain_stem | 1.0 | PRO: | `15.data.id` |

All primary route modules use `classified_name: 55.data.name`. PRO bypass uses `classified_name` from the PRO extraction output.

**Note:** Backup/fallback array modules will be cloned from primary once primary routes are tuned and hardened.

### Phase 2 Additions to Main Routes — Feb 26, 2026

- Modules 263, 264, 266, 267, 268 (conditional typed-field PATCHes) added to main BD routes

- `unfurl_links`/`unfurl_media` added to all Slack reply modules

- See [Phase 2: Classification & Routing](https://www.notion.so/548d362076b243f1ad33df72fd6617a1) As-Built for details

### Summary

Phase 1 build completed in a single session. All 7 routes (PRO: bypass + 5 BD classification destinations + Needs Review fallback) are functional with Slack confirmation replies. The scenario processes Slack messages from #brain-stem, classifies via Claude API (with OpenRouter fallback), creates records in destination Airtable tables with linked record fields, updates Inbox Log, and replies in-thread.

### Scenario Architecture

```plain text
Webhook (1) → Webhook Response (2) → [Bot Filter] → Router (prefix detection)
  ├── PRO: → Tools (7) → HTTP Inbox Log (15) → HTTP Projects (16) → HTTP Inbox Log PATCH (17) → HTTP Slack Reply
  ├── CAL: → Tools placeholder
  ├── R: → Tools placeholder
  ├── fix: → Tools placeholder
  └── BD: (default) → Tools (21) → HTTP Inbox Log (24) → Anthropic Claude (48)
        ├── [Primary] → Text Parser (54) → Text Parser (57) → Parse JSON (55) → Router (30)
        │     ├── People → Create → Linked PATCH → Inbox Log PATCH → Slack Reply
        │     ├── Projects → Create → Linked PATCH → Inbox Log PATCH → Slack Reply
        │     ├── Ideas → Create → Linked PATCH → Inbox Log PATCH → Slack Reply
        │     ├── Admin → Create → Linked PATCH → Inbox Log PATCH → Slack Reply
        │     ├── Events → Create → Linked PATCH → Inbox Log PATCH → Slack Reply
        │     └── Needs Review (fallback) → Inbox Log PATCH → Slack Reply
        └── [48 error] → OpenRouter (116) → Text Parsers → Parse JSON → Router
              ├── [same 6 destinations with linked PATCHes]
              └── [116 error] → PATCH Error status → Slack alert
```

### Key Module Reference (BD Route)

| Module # | Type | Purpose |  |  |  |
| --- | --- | --- | --- | --- | --- |
| 1 | Webhooks | Custom webhook (Slack events) | 2 | Webhooks | Webhook response (challenge handler) |
| — | Filter | Bot message filter (`1.event.bot_id` does not exist) | 21 | Tools &gt; Set variable | Strip BD: prefix → `clean_text` |
| 24 | HTTP &gt; Make a request | POST to Inbox Log (status: Processing) | 48 | Anthropic Claude | Create a Prompt (classification + extraction) |
| 54 | Text Parser &gt; Replace | Strip JSON prefix (regex: `^[\s\S]*?\{` → `{`) | 57 | Text Parser &gt; Replace | Strip JSON suffix (regex: `\}[^}]*$` → `}`) |
| 55 | JSON &gt; Parse JSON | Parse cleaned response → destination, confidence, data, reason | 30 | Router | 6 routes by destination + confidence |

### Claude API Configuration

- **Module:** Anthropic Claude &gt; Create a Prompt (module 48)

- **Model:** `claude-sonnet-4-5-20250929`

- **Authentication:** [Make.com](http://make.com/) built-in API Key auth (not HTTP header)

- **Prompt ID:** `brain_dump_classifier_v1` (embedded in module, not external)

- **Temperature:** Not explicitly set (module default)

- **Max tokens:** Default

- **Classifier prompt updated (Feb 25):** Four new Events fields added — `start_time`, `end_time` (ISO 8601 UTC, infer America/Vancouver), `attendees` (comma-separated string), `location`. As-Built is now the authoritative prompt reference.

### JSON Response Handling (Critical)

Claude wraps JSON responses in markdown code fences (`json ... `). [Make.com](http://make.com/) cannot match backtick characters in formulas (reserved as field name delimiters).

**Solution — Two-step Text Parser regex:**

**Module 54 (strip prefix):**

- Pattern: `^[\s\S]*?\{`

- New value: `{`

- Singleline: Yes

- Input: `48.Text Response`

**Module 57 (strip suffix):**

- Pattern: `\}[^}]*$`

- New value: `}`

- Singleline: Yes

- Input: `54.Text`

**Why **`\}[^}]*$`** and not **`\}[\s\S]*$`**:** The greedy `[\s\S]*` matches the first `}` in the response. Using `[^}]*$` ensures only the final closing brace is matched by preventing the match from crossing another `}`.

### Failed Approaches (documented for reference)

1. Prompt engineering ("raw JSON only") — Claude ignores instructions

1. JSON Schema output format — Grammar compilation timeout

1. Text Parser Match Pattern `\{[\s\S]*\}` — Returned empty

1. Set Variable with replace() — Make treated formulas as literal text

1. Substring/indexOf formulas — Same literal text issue

### Router Filters (BD Route — Module 30)

**Destination Routes (People/Projects/Ideas/Admin/Events)**

- Condition 1: `55.destination` Equal to `[destination_name]`

- Condition 2: `55.confidence` Greater than or equal to `.60`

**Needs Review Route**

- **Fallback: Yes** (no conditions — catches everything unmatched)

- Previous issue: Had conditions with wrong value (`needs review` vs `needs_review`) and wrong operator. Fixed by removing all conditions and relying on fallback behavior.

### Prefix Router Filters (First Router)

- PRO: `1.event.text` starts with (case insensitive) `PRO:`

- CAL: `1.event.text` starts with (case insensitive) `CAL:` (placeholder)

- R: `1.event.text` starts with (case insensitive) `R:` (placeholder)

- fix: `1.event.text` starts with (case insensitive) `fix:` (placeholder)

- BD: `1.event.text` does not match pattern `^(PRO:|CAL:|R:|fix:)`

**Critical note:** The BD filter condition field must use the **mapped variable pill** (purple tag) for `1.event.text`, not typed plain text. Typed text causes the filter to always pass, resulting in PRO: messages hitting both routes.

### Bot Message Filter

- **Location:** Between Webhook Response (2) and first Router

- **Condition:** `1.event.bot_id` does not exist

- **Purpose:** Prevents the bot's own Slack reply messages from re-entering the pipeline

- **Note:** In "Run once" mode, queued bot messages still appear as "Unprocessed data in webhook queue". This does not occur in live "Immediately as data arrives" mode.

### HTTP Module Patterns

**All Airtable Modules**

- **Authentication:** No authentication (auth via header)

- **Headers:**
    - `Authorization`: `Bearer <<AIRTABLE_PAT>>`
    - `Content-Type`: `application/json`

- **Body input method:** JSON string

- **Parse response:** Yes

**Create Record (POST)**

- URL: `https://api.airtable.com/v0/<<BASE_ID>>/<<TABLE_ID>>`

- Body: `{ "fields": { "Field": "value" } }`

**Update Record (PATCH)**

- URL: `https://api.airtable.com/v0/<<BASE_ID>>/<<TABLE_ID>>/<record_id>`

- Body: `{ "fields": { "Field": "value" } }`

- Single-record URL format (record ID in URL, no `records` array wrapper)

**Slack Reply (POST)**

- URL: `https://slack.com/api/chat.postMessage`

- Headers:
    - `Authorization`: `Bearer <<SLACK_BOT_TOKEN>>`
    - `Content-Type`: `application/json`

- Body: `{ "channel": "<channel>", "thread_ts": "<ts>", "text": "..." }`

### Destination Route Bodies (Module A — Create Record)

**People**

```json
{"fields": {"Name": "55.data.name", "Context": "55.data.context", "Follow-Ups": "55.data.follow_ups", "Last Touched": "now"}}
```

**Note:** Field name is `Follow-Ups` (capital U, hyphenated) — case-sensitive.

**Projects**

```json
{"fields": {"Name": "55.data.name", "Type": "capitalize(55.data.project_type)", "Status": "capitalize(55.data.status)", "Next Action": "55.data.next_action", "Notes": "55.data.notes"}}
```

**Note:** `capitalize()` required — Claude returns lowercase (`physical`, `active`), Airtable expects title case (`Physical`, `Active`).

**Ideas**

```json
{"fields": {"Name": "55.data.name", "One-Liner": "55.data.one_liner", "Notes": "55.data.notes"}}
```

**Admin**

```json
{"fields": {"Name": "55.data.name", "Due Date": "55.data.due_date", "Status": "Todo", "Notes": "55.data.notes"}}
```

**Note:** Created field is computed in Airtable — cannot be written via API. Removed from CREATE body (Feb 25).

**Events**

```json
{"fields": {"Title": "55.data.name", "Event Type": "Meeting", "Start Time": "55.data.start_time", "End Time": "55.data.end_time", "Attendees": "55.data.attendees", "Location": "55.data.location", "Notes": "55.data.notes"}}
```

**Note:** Events table uses `Title` not `Name` as the title field. Attendees changed from linked record to Long Text (Feb 25). Start/end times in ISO 8601 UTC with America/Vancouver inference. Four new Events fields added to classifier prompt Feb 25.

### Inbox Log PATCH Bodies (Module B)

All destination routes use the same pattern (only `Filed To` value differs):

```json
{"fields": {"Filed To": "[Destination]", "Confidence": 55.confidence, "Status": "Filed", "Destination Name": "55.data.name"}}
```

**Needs Review PATCH**

```json
{"fields": {"Filed To": "Needs Review", "Confidence": 55.confidence, "Status": "Needs Review", "Destination Name": "55.destination"}}
```

### Error Handling & OpenRouter Fallback (updated Feb 21, 2026)

**Primary error path: OpenRouter fallback (Module 116)**

- Wired as error handler on Module 48 (Anthropic Claude)

- Module 116: HTTP POST to OpenRouter (`https://openrouter.ai/api/v1/chat/completions`)

- Fallback models array: `openai/gpt-4o` → `google/gemini-2.5-pro` (Anthropic excluded — already down if this branch fires)

- Text Parser input mapping: `116.Data.choices[1].message.content` (OpenAI-compatible response format; Make 1-indexed)

- Full downstream clone: Text Parser (strip prefix) → Text Parser (strip suffix) → Parse JSON → Router → all 6 destination routes (with linked record PATCHes)

- Tested via OpenRouter with GPT-4o: correct classification (People, 0.85), cost ~$0.003305/call (GPT-4o; Gemini 2.5 Pro cost will differ)

**Last-resort error path (Module 116 error handler):**

1. HTTP PATCH → Inbox Log status to "Error", Filed To "Needs Review"

1. HTTP POST → Slack alert with error message

### Linked Record Fields (Feb 21, 2026)

Isolated HTTP PATCH modules added on all 5 destination routes (People, Projects, Ideas, Admin, Events) for both primary (Anthropic) and fallback (OpenRouter) branches.

Each is a separate PATCH updating only the linked field, placed between the Create module and the existing Inbox Log PATCH:

- **People route** → `Linked People`

- **Projects route** → `Linked Projects`

- **Ideas route** → `Linked Ideas`

- **Admin route** → `Linked Admin`

- **Events route** → `Linked Events`

**Body pattern:**

```json
{"fields": {"Linked [Table]": ["<record_id>"]}}
```

**Airtable schema change:** Added "Linked Events" column to Inbox Log table (was missing from Phase 0 schema).

**Why isolated PATCHes:** Linked record fields cause `InvalidConfigurationError` when included in the main Create or PATCH bodies alongside other fields. Separating them into dedicated single-field PATCH calls avoids this.

### Test Results

| Test Message | Expected Route | Actual Route | Confidence | Result |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BD: Met Sarah at sustainability conference... | People | People | 0.92 | ✅ | BD: Exhibition installation guide... | Projects | Projects | 0.92 | ✅ |
| BD: What if we created an AI that generates... | Ideas | Ideas | 0.92 | ✅ | BD: Renew car registration by March 15 | Admin | Admin | 0.95 | ✅ |
| BD: Meeting with coastal engineering team... | Events | Events | — | ✅ | BD: Call Alex... buy groceries... write article | Needs Review | Needs Review | 0.45 | ✅ |
| PRO: Landing page redesign... | PRO bypass | PRO bypass | 1.0 (fixed) | ✅ |  |  |  |  |  |

### Test Results — Feb 21, 2026 (OpenRouter + Linked Records)

- 5/5 test messages routed correctly with linked records populating on all destination routes

- OpenRouter standalone test confirmed working (GPT-4o classification: People, confidence 0.85 — matched expected output)

- **Known limitation:** Multi-subject messages (e.g. person + project + task in one message) not yet caught by classifier — fuel for Phase 2 few-shot tuning

### Known Deferred Items

1. ~~Linked Record Fields~~ — **Resolved Feb 21, 2026**

- Isolated PATCH modules added for linked fields on all destination routes (both primary and fallback branches). See "Linked Record Fields" section above.

1. AI Output Raw Field (all PATCH bodies)

- Claude's raw response contains double quotes that break the outer JSON when embedded as a string value. Removed from all routes.

1. PRO Route Claude Extraction

- PRO route currently uses keyword matching, not Claude API extraction.

1. Duplicate Test Records

- Multiple test records exist in People, Projects, Ideas, Admin, Events, and Inbox Log from debugging. Clean up manually in Airtable.

1. Project Type Consistency

- Claude returns varying project types for ambiguous messages. Acceptable for now.

1. Tags (all destination tables) — deferred (phase TBD)

- Tags field type changed to Long Text across all destination tables. Claude continues returning tags array; not written to Airtable at capture time. Airtable AI will generate tags during enrichment pass (phase TBD, not Phase 3 Research).

1. Linked record fields and multi-entity detection — deferred to Phase 2

- **Two distinct issues:**
    1. **Linked record fields in PATCH bodies** — Airtable linked record fields (Linked People, Linked Projects, Linked Ideas, Linked Admin, Linked Events in Inbox Log) cause `InvalidConfigurationError` when included in PATCH bodies. Simple linked field writes (single destination record per capture) are working via the linkify modules. Complex cross-table linking where a single capture references multiple entity types (e.g. an event with new attendees not yet in People) is deferred.
    1. **Multi-entity detection** — When a capture contains multiple distinct entities (e.g. an event + people not yet in the People table), the classifier routes to a single destination only. Phase 2 will add a lookup against the People DB at capture time, flag unrecognized names via Slack reply, and allow resolution via `fix: people - \[name\]` reply. This pattern may extend to other routes where captures reference entities across tables.

### Airtable IDs Reference

- **Base ID:** `appuT9wJR9eKmVfyU`

- **Inbox Log:** `tblrXultsjYl2aYqy`

- **People:** (check URL)

- **Projects:** (check URL)

- **Ideas:** (check URL)

- **Admin:** (check URL)

- **Events:** `tblr37R...` (partial from screenshot)

### Operational Notes

- **Cost per BD capture (primary):** ~1 credit (Anthropic) + 6-8 Make operations

- **Cost per BD capture (fallback):** ~$0.003305 (GPT-4o via OpenRouter) + 6-8 Make operations

- **Cost per PRO capture:** 0 credits (no AI) + 4 Make operations

- **Scenario scheduling:** Set to "Immediately as data arrives" for live mode

- **Bot echo prevention:** Filter on `1.event.bot_id` does not exist

- **Airtable outage (Feb 20, 2026):** 4+ hour outage during build session. Work done blind, tested after recovery.

### Phase 1 Completion Checklist

- [x] Claude API connection configured (Anthropic Claude native module)

- [x] Classification prompt embedded in module 48

- [x] Message parsing logic implemented (prefix detection + clean_text)

- [x] All 6 destination paths created (People, Projects, Ideas, Admin, Events, Needs Review)

- [x] PRO: prefix bypass logic implemented

- [x] Airtable record creation tested for each table

- [x] Inbox Log entries created and updated correctly

- [x] Slack reply formatting correct (in-thread replies) — *Airtable links missing at launch, added Feb 25*

- [x] Confidence scoring working as expected

- [x] Bot message filter preventing echo loops

- [x] Error handling on Claude API module

- [x] Linked record fields via isolated PATCHes (resolved Feb 21)

- [x] OpenRouter fallback branch wired — Module 116 (Feb 21)

- [x] End-to-end test with scenario in live mode (5/5 Feb 21)

- [ ] AI Output Raw in PATCH bodies (deferred)

- [ ] PRO route Claude extraction (deferred)

### Next Steps

1. Toggle scenario to live ("Immediately as data arrives" ON)

1. Clean up duplicate test records in Airtable

1. Monitor for a few days of real usage

1. Proceed to Phase 2: Classification & Routing (fix: handler, few-shot examples, calibration)

---

## Blockers & Issues

**Resolved:**

- ✅ **Claude markdown code fence wrapping** — Solved with position-based regex two-step Text Parser approach (see As-Built Deviation 2)

---

## Completion Checklist

*Superseded by the As-Built Phase 1 Completion Checklist above. Retained for traceability.*

- [x] Claude API connection configured in [Make.com](http://make.com/)

- [x] Classification prompt added to Prompt Library

- [x] Message parsing logic implemented

- [x] All 6 destination paths created (People, Projects, Ideas, Admin, Events, Needs Review)

- [x] PRO: prefix bypass logic implemented

- [x] Airtable record creation tested for each table

- [x] Inbox Log entries created correctly

- [x] Slack reply formatting correct

- [x] Confidence scoring working as expected

- [x] End-to-end test with 10+ diverse messages

- [x] OpenRouter fallback branch (Feb 21)

- [x] Linked record fields operational (Feb 21)

---

## Next Phase

[Phase 2: Classification & Routing](https://www.notion.so/548d362076b243f1ad33df72fd6617a1)

**Child page:** PRO: Route Fix - Working Instructions
**Status:** Ready to implement
**Time:** 30 minutes
**Architecture Change:** PRO: prefix guarantees destination=Projects with confidence 1.0, but message still requires Claude extraction for structured fields.
---
## Problem Summary
The PRO: route should NOT bypass intelligence entirely. Instead:
- **PRO: prefix** guarantees destination = **Projects** with **confidence = 1.0** (no classification needed)
- **Message body** must still be parsed via **Claude API** to populate Projects fields (Name, Type, Status, Next Action, Notes, Tags, Due Date)
This ensures effective filing, retrieval, and referencing while maintaining user control over destination.
---
## Implementation Steps
### Step 1: Strip Prefix and Normalize
**Add Set Multiple Variables module after Router (PRO route)**
1. Click + after Router → PRO: route
1. Select **Tools > Set multiple variables**
1. Create two variables:
**Variable 1 - original_text:**
- Name: `original_text`
- Value: (use picker) Webhooks [1] → event.text
**Variable 2 - clean_text:**
- Name: `clean_text`  
- Value: (use picker) Webhooks [1] → event.text
- Then add **replace** function: `replace(1.event.text; "/^PRO:\s*/"; "")`
- This strips both "PRO:" and "PRO: " and trims whitespace
1. Click **OK**
---
### Step 2: Create Inbox Log (Processing Status)
**Add Airtable > Create a record**
1. Click + after Set Variables
1. Select **Airtable > Create a record**
1. **Connection:** Airtable - Brain Stem
1. **Base:** Brain Stem  
1. **Table:** Inbox Log
**Map Field Values:**
**Original Text:**
- Picker → Tools [previous module] → **original_text**
**Filed To:**
- **Map toggle OFF**
- Type: `Projects`
**Confidence:**
- Type: `1`
**Status:**
- **Map toggle OFF**
- Type: `Processing`
**Slack Channel:**
- Picker → Webhooks [1] → [event.channel](http://event.channel/)
**Slack Message TS:**
- Picker → Webhooks [1] → event.ts
**Slack Thread TS:**
- Picker → Webhooks [1] → event.thread_ts
- If empty, falls back to event.ts automatically
**Created:**
- Use "Date & time" picker → **now**
1. Click **OK**
**Note the module number** - you'll need it for Step 5.
---
### Step 3: Call Claude (Projects Field Extraction)
**Add HTTP > Make a request**
1. Click + after Create Inbox Log
1. Select **HTTP > Make a request**
1. **URL:** [`https://api.anthropic.com/v1/messages`](https://api.anthropic.com/v1/messages)
1. **Method:** POST
1. **Headers:**
```javascript
x-api-key: [Your Claude API key]
anthropic-version: 2023-06-01
Content-Type: application/json
```
1. **Body:** (Request content)
```json
{
  "model": "claude-3-5-haiku-20241022",
  "max_tokens": 500,
  "temperature": 0,
  "messages": [
    {
      "role": "user",
      "content": "Extract project fields from this Slack message. Destination is FIXED to Projects (do not reclassify). Return ONLY raw JSON.\n\nMessage: SET_VARIABLE_MODULE.clean_text\n\nJSON schema (exact keys matching Airtable Projects table from Phase 0):\n{\n  \"name\": \"string\",\n  \"type\": \"digital|physical|hybrid|null\",\n  \"status\": \"active|waiting|blocked|someday|done|null\",\n  \"next_action\": \"string|null\",\n  \"notes\": \"string|null\",\n  \"tags\": [\"string\"],\n  \"reason\": \"string\"\n}\n\nRules:\n- name: Project title (required) → maps to 'Name' field\n- type: Infer from message (digital/physical/hybrid) → maps to 'Type' select field (capitalize first letter)\n- status: Default 'active' unless message indicates otherwise → maps to 'Status' select field (capitalize first letter)\n- next_action: Single executable action if clear, else null → maps to 'Next Action' long text field\n- notes: Additional context from message → maps to 'Notes' long text field\n- tags: Short keywords, always include 'slack-capture' → maps to 'Tags' multi-select field\n- reason: Brief explanation of extraction choices (for logging/debugging, not stored in Airtable)\n\nNote: 'Last Touched' is set automatically to current timestamp in Make.com, not extracted from message.\n\nReturn ONLY the JSON object, no markdown formatting."
    }
  ]
}
```
**Replace **`SET_VARIABLE_MODULE.clean_text`** with the actual picker reference to your Set Variables module's clean_text output.**
1. **Parse response:** ON
1. Click **OK**
**Module output will be:** `data.content[].text` containing Claude's JSON response.
---
### Step 4: Parse Claude JSON
**Add JSON > Parse JSON**
1. Click + after HTTP module
1. Select **JSON > Parse JSON**
1. **JSON string:** (use picker)
    - Navigate to your HTTP module
    - Select **data > content > Collection > text**
    - Or use formula: `first(HTTP_`[`MODULE.data`](http://module.data/)`.content).text`
1. Click **OK**
**This creates structured variables:** `name`, `type`, `status`, `next_action`, `notes`, `tags`, `reason`
---
### Step 5: Create Projects Record
**Add Airtable > Create a record**
1. Click + after Parse JSON
1. Select **Airtable > Create a record**
1. **Connection:** Airtable - Brain Stem
1. **Base:** Brain Stem
1. **Table:** Projects
**Map Field Values:**
**Name:**
- Picker → Parse JSON [previous module] → **name**
- Fallback: If empty, use clean_text (truncate to 255 chars)
**Type:**
- **Map toggle OFF** (it's a select field but we're setting value directly)
- Picker → Parse JSON → **type**
- If null, default to: `Digital`
**Status:**
- **Map toggle OFF**
- Picker → Parse JSON → **status**  
- If null, default to: `Active`
**Next Action:**
- Picker → Parse JSON → **next_action**
- Leave empty if null (do NOT use clean_text as fallback)
**Notes:**
- Picker → Parse JSON → **notes**
- If null, fallback: Picker → Set Variables → **clean_text**
**Tags:**
- **Map toggle ON** (multi-select requires mapping)
- Click **Add item**
- Map each tag from Parse JSON → **tags** array
- Ensure "slack-capture" is included (add manually if not in array)
**Last Touched:**
- Use "Date & time" picker → **now**
1. Click **OK**
**Note the module number** - you'll need it for Step 6.
---
### Step 6: Update Inbox Log (Filed Status)
**Add Airtable > Update a record**
1. Click + after Create Projects
1. Select **Airtable > Update a record**
1. **Connection:** Airtable - Brain Stem
1. **Base:** Brain Stem
1. **Table:** Inbox Log
**Record ID:**
- Picker → Find your "Create Inbox Log" module from Step 2
- Select **ID**
**Map Field Values:**
**Status:**
- **Map toggle OFF**
- Type: `Filed`
**Destination Name:**
- Picker → Create Projects module from Step 5
- Select **Name**
**Destination URL:**
- Type: [`https://airtable.com/appuT9wJR9eKmVfyU/tblkG1bqVjQhQ9JtD/viwCNITHPk13nzw8H/`](https://airtable.com/appuT9wJR9eKmVfyU/tblkG1bqVjQhQ9JtD/viwCNITHPk13nzw8H/)
- Then at the end (after the last /), use picker:
- Navigate to Create Projects module
- Select **ID**
- Final result: URL base + purple ID pill
1. Click **OK**
---
### Step 7: Slack Confirmation Reply
**Add Slack > Create a message**
1. Click + after Update Inbox Log
1. Select **Slack > Create a message**
1. **Connection:** Your Slack connection
1. **Channel:** (use picker) Webhooks [1] → [event.channel](http://event.channel/)
1. **Thread TS:** (use picker) Webhooks [1] → event.ts
1. **Text:**
```javascript
✅ Filed to *Projects*

*Project:* PROJECTS_MODULE.Name
*Status:* PROJECTS_MODULE.Status
if(PROJECTS_MODULE.Next Action; "*Next Action:* " + PROJECTS_MODULE.Next Action; "")

🔗 <INBOX_LOG_UPDATE_MODULE.Destination URL|View in Airtable>
```
**Replace **`PROJECTS_MODULE`** and **`INBOX_LOG_UPDATE_MODULE`** with actual picker references.**
1. Click **OK**
---
## Testing
1. Ensure scenario is **ON**
1. In #brain-stem, send: `PRO: Build the new content synthesis interface`
1. Check [Make.com](http://make.com/) execution - all modules should be green
1. Verify in Airtable:
**Inbox Log:**
- Original Text = full Slack message with prefix
- Filed To = Projects
- Confidence = 1
- Status = Filed
- Destination Name + URL populated
**Projects:**
- Name = extracted project title (not full message)
- Type = Digital/Physical/Hybrid (inferred)
- Status = Active (or as specified)
- Next Action = executable action if present
- Notes = additional context
- Tags includes "slack-capture"
1. Check Slack reply in thread with project details + Airtable link
---
## Success Criteria
✅ Inbox Log shows original message with PRO: prefix
✅ Projects record has structured fields (not just raw text dump)
✅ Next Action is a single executable step (when applicable)
✅ Tags include "slack-capture" + relevant keywords
✅ Slack confirmation shows project name, status, next action
✅ No literal variable names like "7.clean_text" in any field
---
## Key Differences from Previous Version
**OLD (bypass):**
- PRO: → Skip Claude → Dump clean_text into all fields
**NEW (extraction):**
- PRO: → Guarantees destination=Projects (confidence 1.0) → Claude extracts structured fields → Populated properly
**Why this matters:**
- **Retrieval:** Can filter by Status, Type, Tags
- **Actionability:** Next Action is distinct from full message
- **Intelligence:** Claude interprets intent, not just text storage
- **Consistency:** Same structured data quality as classified captures
---
## Troubleshooting
**Claude returns markdown instead of JSON:**
- Check prompt emphasizes "Return ONLY raw JSON, no markdown formatting"
- Add filter module to strip `json and ` wrapper if needed
**Parse JSON fails:**
- View HTTP module output in execution history
- Copy Claude response, validate at [jsonlint.com](http://jsonlint.com/)
- Adjust prompt to enforce stricter JSON format
**Tags not appearing:**
- Map toggle must be ON for multi-select fields
- Manually add "slack-capture" as first item if not in Claude response
**Variable substitution fails:**
- Always use picker, never type module references manually
- Ensure Parse JSON module successfully extracted all fields
- Check field names match exactly (case-sensitive)
---
## Related Documentation
See also:
- **Phase 0:** Inbox Log and Projects table schemas
- **Operating Protocol:** Prefix semantics and role split (Claude vs Airtable AI)
- **Prompt Library:** Projects Extraction prompt (when versioned)
