# phases/phase_1_capture.md

# Phase 1: Brain Dump Capture

## Objective

Establish and validate the capture workflow: brain dump → Inbox Log → structured entries. Ensure all capture channels route correctly and Inbox Log maintains audit integrity.

## Inputs

**Brain dumps arrive via:**

- Slack DMs (direct message to Brain Stem bot)
- Slack commands (slash commands in any channel)
- Manual Notion entry (direct to Inbox Log database)
- Email forwarding (future: not implemented in Phase 1)

**Capture requirements:**

- Every input gets an Inbox Log entry (audit backbone)
- Timestamp recorded automatically
- Raw text preserved
- Classification happens post-capture (Phase 2)

## Capture Channels (Quick Entry Points)

### Slack Bot DM

**Setup:**

```
1. DM the Brain Stem bot: <<SLACK_BOT_NAME>>
2. Type brain dump as free-form text
3. Bot acknowledges and logs entry
```

**Example flow:**

```
You: "PRO: Update docs mirror Phase 1 by Friday"
Bot: "✅ Logged to Inbox (#12345)"
```

**Behind the scenes:**

- Slack webhook triggers [Make.com](http://Make.com) scenario
- Make posts to Airtable Inbox Log
- Returns confirmation to Slack

### Slack Slash Command

**Usage:**

```
/braindump [text]
```

**Example:**

```
/braindump BD: Meeting notes from sync with external AI vendor
```

**Result:**

- Entry created in Inbox Log
- Ephemeral confirmation message (only you see it)
- Original message not visible to channel

### Manual Notion Entry

**Direct entry to Inbox Log database:**

1. Open Inbox Log in Notion
2. Click "+ New" or press `Cmd/Ctrl + N`
3. Fill required fields:
    - **Raw Input** (text): The brain dump content
    - **Timestamp** (auto-filled if created via button)
    - **Source** (select): Manual, Slack, Email, etc.
4. Save (creates audit record)

**Use case:**

- Offline brain dumps
- Batch imports from notes
- Corrections or manual logs

## Notion Database Targets

### Inbox Log (Primary)

**Purpose:** Audit backbone for all incoming brain dumps

**Required fields:**

```yaml
- Raw Input: text (long text property)
- Timestamp: date (with time)
- Source: select (Slack, Manual, Email, etc.)
- Status: select (New, Processed, Archived)
- Routing Prefix: text (extracted from Raw Input)
```

**Optional fields (Phase 2):**

```yaml
- Classification Confidence: number (0.00 to 1.00)
- Destination: relation (links to Projects/People/Ideas/etc.)
- Processing Notes: text
```

**Database location:**

```
Notion workspace → Brain Stem Project → Inbox Log
```

### Destination Databases (Phase 2 and beyond)

**Not implemented in Phase 1:**

- Projects
- People
- Ideas
- Admin
- Events
- Research Jobs/Articles/Drafts

**Phase 1 scope:** All entries stay in Inbox Log until Phase 2 classification is implemented.

## Naming Conventions

### Routing Prefixes (Informational Only in Phase 1)

These prefixes help future classification but are not enforced in Phase 1:

**Format:**

```
PREFIX: [content]
```

**Recognized prefixes:**

- `PRO:` – Project-related (high confidence, extraction only)
- `BD:` – Brain dump (requires classification)
- `CAL:` – Calendar/event (scaffolded)
- `R:` – Research (scaffolded)
- `fix:` – Correction or update (scaffolded)

**Examples:**

```
PRO: Update mirror docs by Friday
BD: Had interesting conversation about AI governance
CAL: Team sync next Tuesday 2pm
R: Look into Claude routing strategies
fix: Correct webhook URL in config
```

**Phase 1 behavior:**

- Prefix extracted and stored in Inbox Log
- No automatic routing (classification is Phase 2)
- All entries remain in Inbox Log for manual review

### Timestamp Format

**Auto-generated timestamps:**

```
YYYY-MM-DD HH:MM:SS (local timezone)
```

**Example:**

```
2026-02-07 09:30:15
```

## Validation Checklist

### Test Slack Bot Capture

**Steps:**

```
1. DM Brain Stem bot with test message:
   "TEST: Phase 1 capture validation"

2. Verify bot responds:
   "✅ Logged to Inbox (#XXXXX)"

3. Check Inbox Log in Notion:
   - New entry exists
   - Raw Input contains test message
   - Timestamp is current
   - Source = "Slack"
   - Status = "New"
```

### Test Manual Entry

**Steps:**

```
1. Open Inbox Log in Notion

2. Create new entry:
   Raw Input: "TEST: Manual entry validation"
   Source: Manual

3. Verify entry saved:
   - Timestamp auto-filled
   - Status defaults to "New"
```

### Verify Webhook Integration

**Check [Make.com](http://Make.com) scenario:**

```
1. Navigate to Make.com dashboard
   URL: <<MAKE_SCENARIO_URL>>

2. Review recent executions:
   - Slack webhook triggered
   - Airtable connection successful
   - No errors in log

3. Verify Airtable → Notion sync:
   - Airtable has matching entry
   - Notion Inbox Log has matching entry
   - Data fields match
```

## "Done" Definition

**Phase 1 capture is working when:**

- Slack DM to bot → entry in Inbox Log (< 5 seconds)
- Slack slash command → entry in Inbox Log (< 5 seconds)
- Manual Notion entry → saved to Inbox Log immediately
- Every entry has:
    - ✅ Raw Input (not empty)
    - ✅ Timestamp (current time)
    - ✅ Source (correct channel)
    - ✅ Status (defaults to "New")
- Webhook errors are caught and logged (not silent failures)
- Inbox Log is the single source of truth for all captures

**Not required in Phase 1:**

- Classification (Phase 2)
- Auto-routing to destination databases (Phase 2)
- Confidence scoring (Phase 2)
- Structured extraction (Phase 2+)

## Exit Criteria

**Phase 1 is complete when:**

- [ ]  Slack bot DM capture tested and working
- [ ]  Slack slash command tested and working
- [ ]  Manual Notion entry tested and working
- [ ]  Inbox Log database has required fields:
    - Raw Input (text)
    - Timestamp (date with time)
    - Source (select)
    - Status (select)
    - Routing Prefix (text)
- [ ]  [Make.com](http://Make.com) scenario tested:
    - Slack webhook → Airtable → Notion
    - End-to-end latency < 10 seconds
    - Error handling active
- [ ]  10+ test entries in Inbox Log with variety:
    - Different sources (Slack DM, slash command, manual)
    - Different routing prefixes (PRO, BD, CAL, R, fix)
    - Mix of short and long inputs
- [ ]  No silent failures (all errors visible in [Make.com](http://Make.com) logs)
- [ ]  Inbox Log integrity verified:
    - No duplicate entries
    - All timestamps accurate
    - No missing Raw Input fields
- [ ]  Documentation updated:
    - Routing prefix conventions documented
    - Capture workflow documented
    - Troubleshooting guide added

**Once exit criteria met, Phase 1 is complete.**

## Next Phase

Proceed to Phase 2: Classification & Routing.

**Phase 2 will add:**

- LLM-based classification (Claude/Perplexity)
- Confidence scoring
- Auto-routing to destination databases
- Structured field extraction

## Troubleshooting

### Problem: Slack bot not responding

**Check:**

```
1. Verify bot is online in Slack workspace
2. Check Make.com scenario status (active/paused)
3. Review Make.com execution log for errors
4. Verify webhook URL is correct:
   - Slack app settings → Event Subscriptions
   - Request URL should match Make webhook
5. Check Slack app permissions:
   - Bot needs `chat:write` scope
   - App must be installed in workspace
```

### Problem: Entries not appearing in Notion

**Check:**

```
1. Verify Airtable has entry (if using Airtable sync)
2. Check Notion API token is valid:
   - Test connection in Make.com
   - Refresh token if expired
3. Verify Inbox Log database URL is correct in Make scenario
4. Check Notion integration permissions:
   - Integration has access to Inbox Log
   - Page sharing settings allow integration
```

### Problem: Duplicate entries

**Resolution:**

```
1. Review Make.com scenario for retry logic
2. Add deduplication check:
   - Check if timestamp + Raw Input already exists
   - Skip if duplicate detected
3. Set webhook timeout appropriately (5-10 seconds)
```

### Problem: Webhook rate limiting

**Symptoms:**

```
- HTTP 429 errors in Make.com log
- Delayed or dropped messages
```

**Resolution:**

```
1. Add rate limiting in Make scenario:
   - Max 10 requests/second to Notion API
   - Queue messages if limit exceeded
2. Consider batching if high volume:
   - Collect messages for 1 minute
   - Bulk insert to Notion
```

## Mirror Note

**This page exports to:**

```
phases/phase_1_capture.md
```

**Publish safety rules:**

- No real secrets (use `<<PLACEHOLDERS>>`)
- No real webhook URLs (use `<<MAKE_WEBHOOK_URL>>`)
- No real Notion tokens (use `<<NOTION_API_TOKEN>>`)
- Example credentials must have `EXAMPLE_SECRET:` prefix on same line
- Drift logging is Notion-only (no mention of public drift log files)

**When exporting:**

1. Verify all placeholders are in correct format
2. Strip any linkified filenames from Notion export
3. Run secret scan before committing:
    
    ```bash
    bash checks/scan_secrets.sh
    ```
    
4. Follow mirror procedure in protocols/MIRRORING.md