<!-- Auto-generated from Notion. Do not edit directly. -->


```yaml
---
doc_id: "phase_1"
last_updated: "2026-02-25"
contract_version: "0.2.0"
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

- **CONTRACT §3.5: Interface Definitions** — Implements Capture Interface, Classification Interface (BD route), Extraction Interface (PRO route), Storage Interface

- **CONTRACT §5: Input Contracts** — Implements PRO: prefix detection (extraction mode) and BD: prefix detection (classification mode)

- **CONTRACT §6: Normalization Contracts** — Strips prefixes, normalizes text for LLM input

- **CONTRACT §7: Route Semantics** — PRO route guarantees destination=Projects with confidence 1.0, calls Claude for field extraction

- **CONTRACT §8: LLM Contracts** — Uses `projects_extract_v1` (Haiku) for PRO route, `brain_dump_classifier_v1` (Sonnet) for BD route

- **CONTRACT §9: Data Contracts** — Creates records in all 6 destination tables (People, Projects, Ideas, Admin, Events, Inbox Log)

- **CONTRACT §10: Invariants & Validation Rules** — Enforces confidence thresholds (≥0.60 auto-file), immutable OriginalText

- **Invariants Implemented:**


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


1.1 [Claude] Create Claude/Anthropic Connection

- In [Make.com](http://make.com/), go to Connections (left sidebar)

- Click "Add" → Search "HTTP"

- Name: "Claude API - Brain Stem"

- You'll configure headers in each HTTP module (no persistent connection needed)


1.2 [Airtable] Create Airtable Connection

- Click "Add" → Search "Airtable"

- Select "Airtable"

- Name: "Airtable - Brain Stem"

- Authentication: Enter your Personal Access Token (from Phase 0 Step 1.9)

- Test connection

- Click "Save"


1.3 [Slack] Create Slack Connection

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


2.1 Add Router Module

- After the Webhook Response module, click "+"

- Search for "Router"

- Add "Flow Control > Router"

- This creates multiple parallel paths


2.2 Create Route 1: PRO: Prefix (Projects Bypass)

- Click first route label → Rename to "PRO: Projects Bypass"

- Click "Set up a filter"


2.3 Create Route 2: CAL: Prefix (Calendar - Future)

- Click second route → Rename to "CAL: Events"

- Add filter:

- Add placeholder module: "Tools > Set variable"
