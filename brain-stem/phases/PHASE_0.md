# Phase 0: Setup & Configuration

```yaml
---
doc_id: "phase_0"
last_updated: "2026-02-21"
contract_version: "0.2.0"
---
```

**Status:** ✅ Complete

**Time Estimate:** 1 hour

**Dependencies:** None

---

## Contract References

This phase establishes infrastructure prerequisites for all pipeline interfaces (retroactive documentation — Phase 0 is complete).

**Implements:**

- **CONTRACT §3b: Current Provider Mapping** — establishes connections for all providers (Slack, [Make.com](http://make.com/), Claude, Perplexity, Airtable)

- **CONTRACT §4: Canonical Entities & Definitions** — establishes core tables (People, Projects, Ideas, Admin, Events, Inbox Log)

- **CONTRACT §5: Input Contracts** — prerequisites: Slack webhook endpoint, channel configuration

- **CONTRACT §9: Data Contracts** — prerequisites: Airtable base with 12 tables matching CONTRACT table schemas

- **CONTRACT §11: Security & Redaction Rules** — API keys and tokens registered as placeholders

- **CONTRACT §12: Observability** — [Make.com](http://make.com/) webhook verification

- **Invariants Implemented:**
    - INV-001: Inbox Log singleton per message (SlackChannel + SlackMessageTS uniqueness)
    - INV-005: OriginalText immutability established

See: [CONTRACT (Brain Stem)](https://www.notion.so/cb5393105c784cc3969571a898b4f81e) v0.2.0 | [contracts/spec (Brain Stem)](https://www.notion.so/98d781fe40ed4e31a566f0d8886325fc)

---

## Overview

This phase establishes the foundational infrastructure for the entire Brain Stem system. You'll create the Airtable data layer, set up the Slack bot for message capture, configure [Make.com](http://make.com/) as the orchestration engine, and collect all necessary API credentials.

### Prerequisites

Before starting Phase 0, ensure you have:

- **Airtable account** (free tier acceptable, Team plan recommended for AI features)

- **Slack workspace admin access** (ability to create apps and channels)

- [**Make.com**](http://make.com/)** account** (will create during Step 3)

- **Credit card for API access** (Claude API, Perplexity API)

- **Password manager** (for secure API key storage)

**What you're building:**

- 12-table Airtable base (data storage + UI)

- Slack app with bot permissions (capture interface)

- [Make.com](http://make.com/) webhook (event receiver)

- API access for Claude and Perplexity (intelligence layer)

---

## As-Designed: Implementation Steps

### [Airtable] Step 1: Create Airtable Base ✅

**Time:** 45-90 minutes (includes AI builder bypass) | **Status:** Complete

<!-- unsupported block type: heading_4 -->

- Create new base named "Brain Stem"

- Start with blank base (not AI template)

**⚠️ If Airtable AI builder auto-launches:**

- Dismiss the AI builder interface

- Access 'Grid View' directly from base menu

- Manually create tables one-by-one (AI builder cannot replicate this specific schema)

<!-- unsupported block type: heading_4 -->

**Field Configuration Notes:**

- **Date fields with time:** Use "Date" type with "Include time" enabled (not "Created time" or "Last modified time" auto-generated fields)

- **Link fields:** Name singular for single-link ("Research Job"), plural for multi-link ("Source Articles")

- **Link configuration:** Works via Record IDs automatically - field names don't need to match between tables

**People Table:**

- Name (Title)

- Context (Long text)

- Follow-ups (Long text)

- Last Touched (Date with time)

- Tags (Multiple select)

**Projects Table:**

- Name (Title)

- Type (Single select: Digital, Physical, Hybrid)

- Status (Single select: Active, Waiting, Blocked, Someday, Done)

- Next Action (Long text)

- Notes (Long text)

- Last Touched (Date with time)

- Tags (Multiple select)

**Ideas Table:**

- Name (Title)

- One-Liner (Long text)

- Notes (Long text)

- Last Touched (Date with time)

- Tags (Multiple select)

**Admin Table:**

- Name (Title)

- Due Date (Date)

- Status (Single select: Todo, Done)

- Notes (Long text)

- Created (Date with time)

**Events Table:**

- Name (Title)

- Event Type (Single select: Meeting, Deadline, Appointment)

- Start Time (Date with time)

- End Time (Date with time)

- Attendees (Link to People, multiple)

- Location (Single line text)

- Notes (Long text)

- Calendar Sync Status (Single select: Synced, Pending, Manual)

- Created (Date with time)

**Inbox Log Table:**

- Original Text (Title)

- Filed To (Single select: People, Projects, Ideas, Admin, Events, Needs Review)

- Original Destination (Single select: People, Projects, Ideas, Admin, Events)

- Corrected Destination (Single select: People, Projects, Ideas, Admin, Events)

- Destination Name (Single line text)

- Destination URL (URL)

- Confidence (Number, 0-1 decimal format)

- Status (Single select: Processing, Filed, Needs Review, Fixed)

- Created (Date with time)

- Slack Channel (Single line text)

- Slack Message TS (Single line text)

- Slack Thread TS (Single line text)

**Research Jobs Table:**

- Query (Title)

- Domains (Multiple select)

- Recency (Single select: 24h, 3d, 1w, 1m)

- Frequency (Single select: Daily, Weekly, Manual)

- Min Relevance Score (Number, 0-100 format)

- Active (Checkbox)

- Last Run (Date with time)

**Articles Table:**

- Title (Title from Articles)

- Research Job (Link to Research Jobs, single link)

- URL (URL)

- Source Domain (Single line text)

- Summary (Long text)

- Key Points (Long text)

- Relevance Score (Number, 0-100)

- Why It Matters (Long text)

- Tags (Multiple select)

- Review Status (Single select: New, Reviewed, Keep, Use, Archive)

- Published Date (Date)

- Retrieved (Date with time)

**Drafts Table:**

- Title (Title)

- Format (Single select: LinkedIn, Substack, Blog, Video, Presentation, Installation)

- Source Articles (Link to Articles, multiple)

- Source Captures (Link to Inbox Log, multiple)

- Thesis (Long text)

- Outline (Long text)

- Body (Long text)

- Status (Single select: Draft, Ready, Scheduled, Published)

- Created (Date with time)

- Scheduled For (Date with time)

**Publications Table:**

- Title (Title from Publications)

- Draft (Link to Drafts, single)

- Platform (Single select: LinkedIn, Substack, Blog, Facebook, Instagram, YouTube)

- Published URL (URL)

- Published At (Date with time)

- Status (Single select: Published, Failed)

**Metrics Table:**

- Title (Title from Metrics)

- Publication (Link to Publications, single)

- Views (Number)

- Likes (Number)

- Comments (Number)

- Shares (Number)

- Last Updated (Date with time)

**Runs Table:**

- Run ID (Title)

- Scenario (Single select: Capture, Fix, Research, Draft, Publish, Metrics, Digest)

- Status (Single select: Success, Failed, Partial)

- Started (Date with time)

- Completed (Date with time)

- Records Processed (Number)

- Error Log (Long text)

<!-- unsupported block type: heading_4 -->

- **Base ID:** Found in URL (format: `appXXXXXXXXXXX`)

- **Table IDs:** Found in URL for each table (format: `tblXXXXXXXXXXX`)

- **Personal Access Token:** Create at [airtable.com/create/tokens](http://airtable.com/create/tokens)
    - Scopes needed: data.records:read, data.records:write, schema.bases:read
    - Access: Grant to "Brain Stem" base
    - Format: `patXXXXXXXXXXX.XXXXXXXXXXXXXXX`

---

### [Slack] Step 2: Create Slack App ✅

**Time:** 30-40 minutes | **Status:** Complete

<!-- unsupported block type: heading_4 -->

- App Name: "Brain Stem Bot"

- Workspace: Your workspace

<!-- unsupported block type: heading_4 -->

- Channel name: #brain-stem

- Visibility: Private recommended

<!-- unsupported block type: heading_4 -->

- Right-click channel → View details → Copy ID (starts with C)

<!-- unsupported block type: heading_4 -->

Used YAML manifest with:

- Bot scopes: `channels:history`, `channels:read`, `chat:write`, `users:read`

- Event subscriptions enabled

- Subscribe to: `message.channels`, `message.groups`

- Webhook URL: (Set in Step 4)

<!-- unsupported block type: heading_4 -->

- OAuth & Permissions → Install to workspace

- Copy Bot User OAuth Token (starts with `xoxb-`)

<!-- unsupported block type: heading_4 -->

- In #brain-stem: `/invite @Brain Stem Bot`

---

### [[Make.com](http://make.com/)] Step 3: Set Up [Make.com](http://make.com/) Account ✅

**Time:** 15 minutes | **Status:** Complete

<!-- unsupported block type: heading_4 -->

- Sign up at [make.com](http://make.com/)

- Verify email

- Plan selection:
    - **Free tier:** 1,000 operations/month (insufficient for this system)
    - **Core plan:** $9/month, 10,000 ops, **max 2 active scenarios** (Phase 0-1 only)
    - **Pro plan:** $16.67/month (annual), 10,000 ops/month + bonus pool, unlimited scenarios (recommended for full system)

**Current subscription:** Pro annual — 120,000 base + 100,000 bonus = 220,000 ops for the year.

<!-- unsupported block type: heading_4 -->

- Set organization name

- Create first team/workspace

---

### [[Make.com](http://make.com/)] [Slack] Step 4: Configure Webhook ✅

**Time:** 30-45 minutes (includes verification troubleshooting) | **Status:** Complete

<!-- unsupported block type: heading_4 -->

- New scenario named "Brain Stem - Capture"

- Add Custom Webhook module

- Copy webhook URL

<!-- unsupported block type: heading_4 -->

**⚠️ CRITICAL:** This module is **required** for Slack webhook verification - not optional.

- Add "Webhook Response" module immediately after Custom Webhook

- Set Status: 200

- Set Body: `1.challenge`

- This responds to Slack's verification handshake automatically

**Without this module:** Webhook verification will fail and events won't flow.

<!-- unsupported block type: heading_4 -->

- Back to [api.slack.com/apps](http://api.slack.com/apps)

- Event Subscriptions → Request URL: [webhook URL]

- Save changes

- Verification successful ✅

<!-- unsupported block type: heading_4 -->

**Required after adding event subscriptions:**

1. Go to OAuth & Permissions page

1. Click "Reinstall App" button

1. Authorize the app again

1. Verify "Event Subscriptions" shows as active

**Why this is needed:** Event subscriptions don't activate until app is reinstalled, even after webhook verification succeeds.

---

### [Claude] [Perplexity] [Airtable] [Slack] Step 5: Collect API Keys ✅

**Time:** 15 minutes | **Status:** Complete

**⚠️ Security Warning:**

- Store all API keys in a password manager immediately

- Never commit API keys to version control (git, etc.)

- Never share API keys in screenshots or documentation

- Treat API keys like passwords - they provide full access to your accounts

<!-- unsupported block type: heading_4 -->

- [console.anthropic.com/settings/keys](http://console.anthropic.com/settings/keys)

- Create key with name "Brain Stem"

- Format: `sk-ant-XXXXXXXXXXXXXXXX`

- Stored securely

<!-- unsupported block type: heading_4 -->

- [perplexity.ai/settings/api](http://perplexity.ai/settings/api)

- Create new key

- Format varies by provider

- Stored securely

<!-- unsupported block type: heading_4 -->

- Created in Step 1.9

- Format: `patXXXXXXXXXXX.XXXXXXXXXXXXXXX`

<!-- unsupported block type: heading_4 -->

- Retrieved in Step 2.5

- Format: `xoxb-XXXXXXXXXXXXXXXX`

---

### [[Make.com](http://make.com/)] Step 6: Test Webhook ✅

**Time:** 10 minutes | **Status:** Complete

<!-- unsupported block type: heading_4 -->

- Post message in #brain-stem: "Test message"

- Check [Make.com](http://make.com/) scenario history

- Verify webhook received payload

<!-- unsupported block type: heading_4 -->

- Note message text location

- Note user ID location

- Note channel ID location

- Note timestamp location

**Expected payload structure:**

```json
{
  "event": {
    "type": "message",
    "text": "Test message",
    "user": "U123456",
    "channel": "C123456",
    "ts": "1234567890.123456"
  }
}
```

---

## As-Built: Actual Implementation Notes

### ✅ Completed (Steps 1-5)

**[Airtable] Step 1: Airtable Base Created (45-60 min actual)**

*Problem encountered:* Airtable's new interface auto-launched the AI app builder instead of allowing manual table creation as the guide described.

*Solution:* Bypassed AI builder by:

- Creating a blank base through the traditional interface

- Accessing grid view directly

- Manually creating tables one-by-one

*Tables created:* All 12 tables with field types as specified:

- People, Projects (with Type field: Digital/Physical/Hybrid), Ideas, Admin, Events, Inbox Log (with Original/Corrected Destination fields for calibration), Research Jobs (Min Relevance Score 0-100), Articles, Drafts (with Thesis/Outline fields), Publications, Metrics, Runs

*Field configuration questions resolved:*

- "Last Touched" field: Used "Date" type with "Include time" enabled (not "Created time" or "Last modified time")

- "Research Job" link field in Articles: Configured as single-link (one article from one job)

- Link field names: Singular for single-link ("Research Job"), plural for multi-link ("Source Articles")

*Credentials captured:*

- Base ID from URL (format: `appXXXXXXXXXXX`)

- Table IDs from URLs (format: `tblXXXXXXXXXXX`)

- Personal Access Token created with scopes: `data.records:read`, `data.records:write`, `schema.bases:read`

- Token format: `pat...`

**[Slack] Step 2: Slack App Configured (30 min actual)**

*Channel created:* #brain-stem (private)

*App creation approach:* Used YAML manifest (Option A from guide) rather than manual configuration

*Problem encountered:* Initial webhook verification failed with error at [api.slack.com](http://api.slack.com/)

*Root cause:* Guide's step sequencing was confusing - Step 2 redirected to Step 4 before app manifest was complete, and webhook URL couldn't be included in manifest until [Make.com](http://make.com/) scenario existed (Step 4).

*Solution path:*

1. Created Slack app with partial manifest (no webhook URL yet)

1. Proceeded to Step 4 to create [Make.com](http://make.com/) webhook

1. Returned to update manifest with webhook URL

1. Verification still failed until Webhook Response module was added

*Event subscriptions configured:*

- Bot scopes: `channels:history`, `channels:read`, `chat:write`, `users:read`

- Subscribed to: `message.channels`, `message.groups`

- Webhook URL added to manifest after Step 4.1

*Bot token retrieved:* Format `xoxb-...`

*Bot invitation:* Successfully invited to #brain-stem channel using `/invite @Brain Stem Bot`

**[**[**Make.com**](http://make.com/)**] [Slack] Step 4: Webhook Configuration (20 min actual + troubleshooting)**

*Problem encountered:* Slack webhook verification kept failing even after webhook URL was added to manifest.

*Root cause:* [Make.com](http://make.com/) scenario only had Custom Webhook module, which received Slack's verification challenge but didn't respond correctly.

*Solution:* Added Webhook Response module immediately after Custom Webhook:

- Set Status: 200

- Set Body: `1.challenge` (references the challenge parameter from Slack's payload)

- This responds to Slack's verification handshake automatically

*Secondary issue:* After webhook verified, events still weren't flowing.

*Solution:* Reinstalled Slack app via OAuth & Permissions page to activate event subscriptions.

*Final configuration:*

- Scenario name: "Brain Stem - Capture"

- Module 1: Custom Webhook

- Module 2: Webhook Response (challenge handler)

- Webhook URL: [<<MAKE_WEBHOOK_URL>>](%3C%3CMAKE_WEBHOOK_URL%3E%3E)

- Verification status: ✅ Successful

**[Claude] [Perplexity] [Airtable] [Slack] Step 5: API Keys Collected (15 min actual)**

- Claude API key: Retrieved from [console.anthropic.com](http://console.anthropic.com/), format `sk-ant-...`

- Perplexity API key: Retrieved from [perplexity.ai/settings/api](http://perplexity.ai/settings/api)

- Airtable PAT: Created in Step 1.9, format `pat...`

- Slack Bot Token: Retrieved in Step 2.5, format `xoxb-...`

- All keys stored in password manager

**[**[**Make.com**](http://make.com/)**] Step 3: **[**Make.com**](http://make.com/)** Account (15 min actual)**

- Account created at [make.com](http://make.com/)

- Email verified

- Pro plan (annual subscription, 220,000 ops/year)

- Organization: "[<<MAKE_ORG_NAME>>](http:///%3C%3CMAKE_ORG_NAME%3E%3E)"

- First scenario created (see Step 4)

### ✅ Complete (Step 6)

**[**[**Make.com**](http://make.com/)**] Step 6: Webhook Tested (5 min actual)**

- Test messages sent in #brain-stem

- Webhook executions confirmed in [Make.com](http://make.com/) scenario history

- All messages successfully received

- Payload structure visible in execution logs

- Ready for Phase 1 implementation

**Note:** Initially thought webhook wasn't working because execution history wasn't checked. Webhook was functioning correctly from the start after verification and app reinstall.

### Key Deviations from Guide

1. **Airtable UI changed:** Guide assumed traditional base creation flow; actual experience required bypassing AI builder

1. **Step sequencing confusion:** Step 2.4 required webhook URL from Step 4, creating circular dependency

1. **Webhook Response module critical:** Guide mentioned it but didn't emphasize it's required for verification to work

1. **Slack app reinstall needed:** Not mentioned in guide; required after adding event subscriptions

1. **Channel name:** Guide used #sb-inbox; actual implementation uses #brain-stem

1. **Table count:** Guide said 11 tables; actual implementation has 12 (added Events table for calendar integration)

### Improvements for Future Builders

- Reorder steps: Create [Make.com](http://make.com/) webhook (Step 4.1-4.2) before Slack app manifest (Step 2.4)

- Emphasize Webhook Response module is not optional

- Document Slack app reinstall requirement after event subscription changes

- Update Airtable instructions for new AI builder interface (bypass method)

- Add troubleshooting section for common webhook verification errors

---

## Blockers & Issues

**None currently**

---

## Phase 0 Completion Checklist

- [x] Airtable base with 12 tables

- [x] Slack app with OAuth and event subscriptions

- [x] [Make.com](http://make.com/) account and scenario created

- [x] Webhook verified by Slack

- [x] All API keys collected

- [x] Webhook tested with live message

- [x] Payload structure visible in execution history

**Phase 0 Complete!** ✅

**Next:** Proceed to Phase 1 to build classification logic

## Common Issues & Solutions

### Issue 1: Airtable AI Builder Auto-Launches

**Symptom:** After creating base, AI builder appears instead of blank grid view

**Solution:**

1. Dismiss AI builder dialog

1. Click "Grid View" from base menu

1. Manually create tables one-by-one

1. AI builder cannot replicate this specific schema

### Issue 2: Webhook Verification Fails

**Symptom:** Slack shows "Your URL didn't respond with the challenge" error

**Solution:**

1. Verify Webhook Response module exists in [Make.com](http://make.com/) scenario

1. Check Body is set to `1.challenge` (not plain text "challenge")

1. Ensure module is immediately after Custom Webhook

1. Test webhook URL in browser - should return empty response

### Issue 3: Events Not Flowing After Verification

**Symptom:** Webhook verified successfully but test messages don't trigger scenario

**Solution:**

1. Go to [api.slack.com](http://api.slack.com/) → Your App → OAuth & Permissions

1. Click "Reinstall App" button

1. Authorize app again

1. Event subscriptions activate only after reinstall

### Issue 4: Link Fields Not Connecting

**Symptom:** Link field shows "No linked records" even after configuration

**Solution:**

- Link fields work automatically via Record IDs

- Field names don't need to match between tables

- Create at least one record in each table to test linking

- Use "Link to another record" field type, select correct table

---

## Next Phase

Once Phase 0 is complete, proceed to [**Phase 1: Brain Dump Capture**](https://www.notion.so/0538979e023a46528fb1a70b60ccd4ef) to build the classification and routing logic.
