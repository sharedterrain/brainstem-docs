# Phase 2: Classification & Routing

```yaml
---
doc_id: "phase_2"
last_updated: "2026-03-07"
contract_version: "0.4.0"
---
```

**Status:** ✅ **Live** — fix: handler operational, conditional typed-field PATCHes on main and fix routes

**Time Estimate:** 1-2 hours

**Dependencies:** Phase 1 functional (routes tested; Inbox Log + Slack confirmations working)

---

## Contract References

This phase extends the Classification Interface implementation from Phase 1 with calibration and correction capabilities.

- **CONTRACT §7: Route Semantics** — Implements the `fix:` route (threaded reply correction/refile)

- **CONTRACT §3.5: Classification Interface** — Calibration via few-shot examples, confidence threshold tuning

- **CONTRACT §3.5: Extraction Interface** — Re-extraction on corrected routing

- **CONTRACT §3.5: Storage Interface** — Record updates from fix handler

- **CONTRACT §3.5: Memory Interface** — Open Brain write path on fix routes (fire-and-forget POST to ingest-thought)

- **CONTRACT §8: LLM Contracts** — Few-shot prompt version updates (`brain_dump_classifier_v1`)

- **CONTRACT §12: Observability & Error Handling** — Weekly misclassification digest, calibration metrics

- **CONTRACT §15: Change Control Protocol** — fix→refile workflow as a discovery→reconcile path

See: [CONTRACT (Brain-Stem)](https://www.notion.so/cb5393105c784cc3969571a898b4f81e) v0.2.0 | [contracts/spec (Brain-Stem)](https://www.notion.so/98d781fe40ed4e31a566f0d8886325fc)

---

## Overview

Enhance classification accuracy with few-shot learning and build the correction workflow that lets you fix misclassifications via Slack replies.

**Anchors from Phase 1 (as-built):**

- Inbox Log is the audit backbone for every capture.

- BD routing is based on `destination` + `confidence` with a Needs Review fallback.

- Slack confirmation replies happen in-thread.

- [Make.com](http://make.com/) filters must use mapped variable pills (avoid typed text conditions).

**What you're building:**

- fix: handler with original record deletion, re-extraction via Claude, and Slack confirmation

- Conditional typed-field PATCHes for main BD and fix routes (dates, single selects)

- Unfurl prevention on all Slack reply modules

- Classifier prompt date resolution (`now` pill for relative date conversion)

---

## Correction Semantics (fix:)

Define and implement a correction workflow that:

- Locates the original capture using Slack thread/message identifiers stored in Inbox Log.

- Refiles to a different destination when needed.

- Updates extracted fields appropriate to the corrected destination (not just “Filed To”).

- Preserves invariants (one Inbox Log entry per Slack message; consistent status transitions).

## Re-extraction on Fix

When a fix changes destination (or materially changes meaning), define one of:

- **Re-extract under fixed destination:** rerun a destination-specific extraction prompt (“destination is fixed; extract fields only”).

- **Destination-specific extraction prompts:** one extractor per table, called by the fix handler.

## Calibration Loop

- Add few-shot examples to the classifier prompt (ground truth comes from fix actions).

- Track confidence vs correction rate.

- Tune confidence threshold policy if needed.

## Weekly Misclassification Digest

Digest should be based on Phase 1 signals:

- Inbox Log entries in Needs Review.

- Captures with confidence below the auto-file threshold.

- Counts and examples of `fix:` corrections (these are labeled outcomes).

## Known Constraints to Respect (carried from Phase 1)

- Linked record fields can trigger `InvalidConfigurationError` when included in PATCH bodies (keep deferred unless fixed explicitly).

- Storing raw AI output requires escaping strategy (embedded quotes can break JSON bodies).

- PRO route Claude extraction is still deferred (define fix behavior for PRO items carefully).

---

## As-Designed: Implementation Steps

*To be designed during implementation*

---

## As-Built: Actual Implementation Notes

**Phase 2: fix: Handler + Typed Field Guards — As-Built Report**

**Date:** February 26, 2026

**Status:** ✅ **Live**

**contract_version:** 0.2.0

### Summary

Phase 2 build completed across a single session. The fix: handler is fully operational across all 5 destination routes (People, Projects, Ideas, Admin, Events) with original record deletion, re-extraction via Claude, Inbox Log update, linked record management, and Slack confirmation replies. Additionally, conditional PATCH modules were added to both main BD routes and fix routes to guard against empty typed fields (dates, single selects) that Airtable rejects.

### fix: Route Architecture

```plain text
1 (Webhook) → Bot filter → Prefix Router
  └── fix: route filter: 1.event.text Matches pattern ^fix: (case insensitive)
        ↓
      208 (Set Variable) — fix_thread_ts = 1.event.thread_ts
        ↓
      209 (HTTP GET) — Airtable lookup: find Inbox Log record by Slack Message TS
        URL: filterByFormula={Slack Message TS}="[208.fix_thread_ts]"&maxRecords=1
        ↓
      Router (6 branches, sequential by route order)
        ├── 1st-5th: DELETE routes (filtered by 209.Filed To value)
        │     ├── 242: Delete from People (filter: Filed To = People)
        │     ├── 243: Delete from Projects (filter: Filed To = Projects)
        │     ├── 244: Delete from Ideas (filter: Filed To = Ideas)
        │     ├── 245: Delete from Admin (filter: Filed To = Admin)
        │     └── 247: Delete from Events (filter: Filed To = Events)
        └── 6th: Pass-through (no filter) → continues to re-extraction chain
              ↓
            210 (Anthropic Claude) — re-extract fields for corrected destination
              ↓
            211 (Text Parser Replace) — strip JSON prefix
              ↓
            212 (Text Parser Replace) — strip JSON suffix
              ↓
            213 (Parse JSON)
              ↓
            214 (Router) — 5 routes by destination (filters on 1.event.text pattern)
              ├── People: 215 → linkify → 220 → 221
              ├── Projects: 222 → 254 → 226 → 227 → 273 → 274
              ├── Ideas: 228 → linkify → 229 → 230
              ├── Admin: 231 → linkify → 232 → 233 → 271
              └── Events: 234 → linkify → 235 → 236 → 269 → 270
```

**Critical:** Route ordering matters. DELETE routes must be numbered 1st–5th, pass-through 6th. Make processes routes sequentially by route order number — if the pass-through runs first and errors, deletes never fire.

### Key Module Reference (fix: Route)

| Module # | Type | Purpose |
| --- | --- | --- |
| 208 | Tools > Set variable | `fix_thread_ts` = `1.event.thread_ts` |
| 209 | HTTP > Make a request | GET Airtable Inbox Log by Slack Message TS |
| 210 | Anthropic Claude | Re-extraction with separated prompt (original text + correction command) |
| 211 | Text Parser > Replace | Strip JSON prefix (regex: `^[\s\S]*?\{` → `{`) |
| 212 | Text Parser > Replace | Strip JSON suffix (regex: `\}[^}]*$` → `}`) |
| 213 | JSON > Parse JSON | Parse cleaned response |
| 214 | Router | 5 routes by destination |
| 237 | DELETED | Was Text Parser Replace for prefix stripping — produced "null" output, not needed |
| 242–245 | HTTP > Make a request | DELETE modules (People, Projects, Ideas, Admin) |
| 246 | DELETED | Deleted during route restructuring |
| 247 | HTTP > Make a request | DELETE from Events |

### Delete Route Module Reference

| Module # | Filter | Table | Table ID |
| --- | --- | --- | --- |
| 242 | Filed To = People | People | `tblKqRONCW4fNVGgH` |
| 243 | Filed To = Projects | Projects | `tblkG1bqVjQhQ9JtD` |
| 244 | Filed To = Ideas | Ideas | `tbljJ5fJ5iEQpeVzf` |
| 245 | Filed To = Admin | Admin | `tblBuudGl45sZVsG2` |
| 247 | Filed To = Events | Events | `tblr37RjqdLeamJ8K` |

**URL pattern:** `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/[TABLE_ID]/` + `209.Data.records[1].fields.Destination Record ID` pill

**Critical:** No space between trailing `/` and record ID pill in DELETE URLs.

### fix: Destination Route Bodies

**People (215):**

```json
{"fields": {"Name": "213.data.name", "Context": "213.data.context", "Follow-Ups": "213.data.follow_ups", "Last Touched": "now", "Source": "Slack"}}
```

**Projects (222):**

```json
{"fields": {"Name": "213.data.name", "Next Action": "213.data.next_action", "Notes": "213.data.notes", "Last Touched": "now", "Source": "Slack"}}
```

Followed by conditional PATCHes: 273 (Type), 274 (Status)

**Ideas (228):**

```json
{"fields": {"Name": "213.data.name", "One-Liner": "213.data.one_liner", "Notes": "213.data.notes", "Last Touched": "now", "Source": "Slack"}}
```

**Admin (231):**

```json
{"fields": {"Name": "213.data.name", "Status": "Todo", "Notes": "213.data.notes", "Source": "Slack"}}
```

Followed by conditional PATCH: 271 (Due Date)

**Events (234):**

```json
{"fields": {"Title": "213.data.name", "Attendees": "213.data.attendees", "Location": "213.data.location", "Notes": "213.data.notes"}}
```

Followed by conditional PATCHes: 269 (Start Time), 270 (End Time)

**Note:** Events table does not have a Source field.

### fix: Inbox Log PATCH Bodies

All routes use the same pattern with Destination URL and Destination Record ID pointing to the new record:

```json
{"fields": {"Filed To": "[Destination]", "Confidence": 1.0, "Status": "Fixed", "Destination Name": "[create_module].data.fields.Name", "Destination URL": "https://airtable.com/appuT9wJR9eKmVfyU/[TABLE_ID]/[VIEW_ID]/[create_module].data.id", "Destination Record ID": "[create_module].data.id"}}
```

**Critical:** Destination Name uses the Airtable response (`[create_module].data.fields.Name`) not Claude's raw output (`213.data.name`) — Claude's text can contain newlines that break JSON.

### fix: Linked Record Modules

Placed after create module, before Inbox Log PATCH (matching main route pattern):

| Route | Module # | Body |
| --- | --- | --- |
| People | — | `{"fields": {"Linked People": ["215.data.id"]}}` |
| Projects | 254 | `{"fields": {"Linked Projects": ["222.data.id"]}}` |
| Ideas | — | `{"fields": {"Linked Ideas": ["228.data.id"]}}` |
| Admin | — | `{"fields": {"Linked Admin": ["231.data.id"]}}` |
| Events | — | `{"fields": {"Linked Events": ["234.data.id"]}}` |

All use URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblrXultsjYl2aYqy/` + `209.Data.records[1].id` pill

### Module 210 Prompt (Authoritative Version)

```plain text
You are an extraction assistant. A message was misclassified in Brain Stem and needs to be refiled.

ORIGINAL MESSAGE:
209.Data.records[1].fields.Original Text

CORRECTION COMMAND:
1.event.text

INSTRUCTIONS:
1. The word after "fix:" in the correction command is the new destination (people, projects, ideas, admin, or events).
2. Extract fields using ONLY the schema matching that destination.
3. Extract from the ORIGINAL MESSAGE, not the correction command.
4. Return raw JSON only, no markdown code fences.

SCHEMAS:
PEOPLE: {"name":"string","context":"string","follow_ups":"string","notes":"string","tags":["string"],"reason":"string"}
PROJECTS: {"name":"string","project_type":"digital|physical|hybrid","status":"active|waiting|blocked|someday|done","next_action":"string","notes":"string","tags":["string"],"reason":"string"}
IDEAS: {"name":"string","one_liner":"string","notes":"string","tags":["string"],"reason":"string"}
ADMIN: {"name":"string","due_date":"YYYY-MM-DD|null","notes":"string","tags":["string"],"reason":"string"}
EVENTS: {"name":"string","start_time":"ISO8601|null","end_time":"ISO8601|null","attendees":"string|null","location":"string|null","notes":"string","tags":["string"],"reason":"string"}
```

**Note:** `209.Data.records[1].fields.Original Text` and `1.event.text` are Make pills that resolve at runtime.

### Open Brain Write Path (fix: Routes) — Mar 7, 2026

5 fire-and-forget HTTP POST modules added to write re-extracted thoughts to Open Brain on fix routes. See CONTRACT §3.5 Memory Interface for the full interface definition. Shares the same endpoint, headers, and fire-and-forget pattern as the primary route modules documented in Phase 1 As-Built.

**Fix route modules (off router 214):**

| **Module #** | **Route** | **text field** | **destination** | **source** | **confidence** | **record_id** |
| --- | --- | --- | --- | --- | --- | --- |
| 281 | fix: People | `213.name + 213.context` | people | brain_stem_fix | 1.0 | `215.data.id` |
| 282 | fix: Projects | `213.name + 213.next_action + 213.notes` | projects | brain_stem_fix | 1.0 | `222.data.id` |
| 283 | fix: Ideas | `213.name + 213.one_liner + 213.notes` | ideas | brain_stem_fix | 1.0 | `228.data.id` |
| 284 | fix: Admin | `213.name + 213.notes` | admin | brain_stem_fix | 1.0 | `231.data.id` |
| 285 | fix: Events | `213.name + 213.attendees + 213.location + 213.notes` | events | brain_stem_fix | 1.0 | `234.data.id` |

All fix route modules use `classified_name: 213.name`.

**Note:** Backup/fallback array modules will be cloned from primary once primary routes are tuned and hardened.

### Conditional Typed-Field PATCHes (Main BD Routes)

Added to guard against empty typed fields that Airtable rejects. Placed at end of route after Slack reply. Filter checks if field Exists before PATCH fires.

**Projects route (off router 30):**

| Module # | Filter | Body |
| --- | --- | --- |
| 267 | `55.data.project_type` Exists | `{"fields": {"Type": "capitalize(55.data.project_type)"}}` |
| 268 | `55.data.status` Exists | `{"fields": {"Status": "capitalize(55.data.status)"}}` |

URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblkG1bqVjQhQ9JtD/` + create module `data.id` pill

**Events route (off router 30):**

| Module # | Filter | Body |
| --- | --- | --- |
| 263 | `55.data.start_time` Exists | `{"fields": {"Start Time": "55.data.start_time"}}` |
| 264 | `55.data.end_time` Exists | `{"fields": {"End Time": "55.data.end_time"}}` |

URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblr37RjqdLeamJ8K/` + create module `data.id` pill

**Admin route (off router 30):**

| Module # | Filter | Body |
| --- | --- | --- |
| 266 | `55.data.due_date` Exists | `{"fields": {"Due Date": "55.data.due_date"}}` |

URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblBuudGl45sZVsG2/` + create module `data.id` pill

**Fields removed from main create modules:**

- Module 77 (Events): Removed Start Time, End Time

- Admin create: Removed Due Date

- Projects create: Removed Type, Status

### Conditional Typed-Field PATCHes (fix: Routes)

Same pattern, using `213` pills and fix route create module IDs:

**Projects fix route:**

| Module # | Filter | Body |
| --- | --- | --- |
| 273 | `213.project_type` Exists | `{"fields": {"Type": "capitalize(213.project_type)"}}` |
| 274 | `213.status` Exists | `{"fields": {"Status": "capitalize(213.status)"}}` |

URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblkG1bqVjQhQ9JtD/` + `222.data.id` pill

**Events fix route:**

| Module # | Filter | Body |
| --- | --- | --- |
| 269 | `213.start_time` Exists | `{"fields": {"Start Time": "213.start_time"}}` |
| 270 | `213.end_time` Exists | `{"fields": {"End Time": "213.end_time"}}` |

URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblr37RjqdLeamJ8K/` + `234.data.id` pill

**Admin fix route:**

| Module # | Filter | Body |
| --- | --- | --- |
| 271 | `213.due_date` Exists | `{"fields": {"Due Date": "213.due_date"}}` |

URL: `https://api.airtable.com/v0/appuT9wJR9eKmVfyU/tblBuudGl45sZVsG2/` + `231.data.id` pill

### Unfurl Prevention (All Slack Reply Modules)

All HTTP POST modules to `https://slack.com/api/chat.postMessage` now include:

```json
"unfurl_links": false, "unfurl_media": false
```

This prevents Slack from generating URL preview cards for Airtable links, which was causing `message_changed` events that re-triggered the webhook (doubling the echo problem from ~7% to ~14% of annual Make budget).

### Classifier Prompt Update (Module 48)

The full classifier prompt (`brain_dump_classifier_v1`) is now authoritative in CONTRACT §8 (v0.3.1). Key additions beyond initial design:

- **Context block:** Describes user as multimedia creator with focus areas (AI/creativity, sustainable design, human-AI collaboration, traditional ecological knowledge, speculative futures) and publishing platforms (LinkedIn, Substack, blog, exhibition docs)

- **Edge case handling:** Empty/whitespace, non-English, image-only, multiple distinct items — all route to `needs_review` with appropriate confidence

- **Events fields added:** `start_time`, `end_time` (UTC with America/Vancouver inference via `now` Make pill), `attendees` (comma-separated), `location`

- **Project type keyword guidance:** Digital vs physical vs hybrid classification keywords listed in prompt

- **Confidence scoring rules:** Explicit ranges (0.85-1.0, 0.70-0.84, 0.60-0.69, <0.60) with descriptions

`now` is a Make pill that resolves at runtime to the current date/time, enabling Claude to convert relative dates ("next Wednesday") to absolute timestamps.

**Note:** The prompt does NOT handle organizations — People captures are individual-focused only. See CONTRACT §4 for entity definitions.

### Bugs Fixed

1. **Module 208 (Set Variable):** Was mapped to `1.event.event_ts` (reply's own timestamp) instead of `1.event.thread_ts` (parent message timestamp). Caused module 209 Airtable lookup to return empty records.

1. **Module 237 (Text Parser):** Deleted. Was producing "null" prefix on output. Router 214 pattern-matches directly on `1.event.text`, making 237 unnecessary.

1. **Module 212 (Text Parser):** Was reading from module 210 instead of 211. Fixed to chain correctly: 210 → 211 → 212 → 213.

1. **Slack reply JSON errors:** Multiple fix route Slack reply modules had literal line breaks in JSON body and missing closing quotes after record ID pills.

1. **Events table Source field:** Events table does not have a Source field. Removed from module 234.

1. **Delete URL spacing:** DELETE module URLs had a space between trailing `/` and record ID pill, causing "NOT_FOUND" errors.

1. **Delete module 247 (Events):** Was missing URL and headers entirely.

1. **Route ordering:** DELETE routes must execute before the pass-through route. Reordered so deletes are 1st–5th, pass-through is 6th.

### Failed Approaches (documented for reference)

1. Module 237 Text Parser Replace with empty/space new value → prepends "null" to output

1. [Make.com](http://make.com/) Set Variable with `replace()`/`lower()`/`trim()` → treated as literal text

1. [Make.com](http://make.com/) `if()` with string concatenation for dynamic DELETE URLs → not attempted due to known formula-as-literal-text issue

1. Single create module with all fields including typed fields → Airtable rejects empty dates/selects

### Test Results

| Test | Original | Fix To | Delete | Create | Inbox Log | Slack Reply | Typed Fields |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Admin → Ideas | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A |
| People → Projects | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A |
| Ideas → Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Due Date guard |
| Projects → Events | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Start/End Time guard |
| Events → People | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A |
| Events (both times) | ✅ main | — | — | ✅ | ✅ | ✅ | Both populated |
| Events (start only) | ✅ main | — | — | ✅ | ✅ | ✅ | Start only |
| Admin (with date) | ✅ main | — | — | ✅ | ✅ | ✅ | Due Date populated |
| Admin (no date) | ✅ main | — | — | ✅ | ✅ | ✅ | Due Date skipped |
| Projects (type+status) | ✅ main | — | — | ✅ | ✅ | ✅ | Both populated |

### Known Deferred Items

1. **Few-shot examples for classifier** — Phase 2 spec calls for adding ground truth from fix actions to the classifier prompt. Not yet implemented. Fix corrections provide labeled outcomes for tuning.

1. **Calibration loop** — Confidence vs correction rate tracking not yet implemented.

1. **Weekly misclassification digest** — Not yet implemented.

1. **AI Output Raw in PATCH bodies** — Still deferred from Phase 1. Claude's raw response contains characters that break JSON embedding.

1. **Tags** — Still deferred. Tags field is Long Text across all tables. Claude returns tags array; not written at capture time.

1. **OpenRouter fallback for fix route** — Fix route uses Anthropic Claude only (module 210). No fallback branch wired. If Anthropic is down, fix commands will fail.

1. **Error handling on fix route** — No error handler on module 210 or downstream modules. A failed fix leaves the original record deleted but no new record created.

1. **Empty 209 guard** — If module 209 returns no record (e.g., fix: sent in wrong thread), all downstream modules receive empty pills. Needs a filter after 209 checking records array is not empty, with a Slack error reply.

---

## Blockers & Issues

**Resolved during build session — see Bugs Fixed section above.**

---

## Phase 2 Completion Checklist

- [x] fix: route implemented with threaded reply lookup

- [x] Original record deletion on all 5 destination tables

- [x] Re-extraction via Claude with separated prompt (original text + correction command)

- [x] New record creation in corrected destination table

- [x] Inbox Log updated (Filed To, Status=Fixed, Destination URL, Destination Record ID)

- [x] Linked record fields updated on fix

- [x] Slack confirmation reply with Airtable record link

- [x] Conditional typed-field PATCHes on main routes (Projects Type/Status, Admin Due Date, Events Start/End Time)

- [x] Conditional typed-field PATCHes on fix routes (same fields)

- [x] Unfurl prevention on all Slack reply modules

- [x] Classifier prompt updated with date resolution (`now`)

- [x] End-to-end test across all 5 fix destination pairs

- [ ] Few-shot examples added to classifier prompt

- [ ] Calibration feedback loop implemented

- [ ] Weekly misclassification digest

- [ ] OpenRouter fallback for fix route

- [ ] Error handling / empty 209 guard

- [x] End-to-end test in live mode

---

## Next Phase

[Phase 3: Research Pipeline](https://www.notion.so/33c94ae1c521433ea32092a1a7856f90)
