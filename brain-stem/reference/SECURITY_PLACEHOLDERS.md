# Security & Placeholders (Brain Stem)

**Security rules and placeholder registry**

This page defines what must never be published and maintains a registry of all placeholders used in documentation.

---

## Never Publish Categories

**The following must NEVER appear in Git mirror or public documentation:**

- **API keys, tokens, credentials**
    - Claude API keys (sk-ant-...)
    - Airtable Personal Access Tokens (pat...)
    - Perplexity API keys (pplx-...)
    - Notion integration tokens (secret_...)

- **Inbound webhook URLs**
    - [Make.com](http://make.com/) webhook URLs ([hook.us2.make.com/](http://hook.us2.make.com/)...)
    - Any endpoint that can be called from the internet without authentication

- **Signing secrets**
    - Slack signing secret
    - HMAC keys
    - Verification tokens

- **Personal identifiers**
    - Email addresses
    - Phone numbers
    - Physical addresses

- **Database identifiers** (treat as sensitive metadata)
    - Airtable Base IDs (app...)
    - Airtable Table IDs (tbl...)
    - Airtable View IDs (viw...)

- **Connection strings**
    - Database URLs
    - Service endpoints with authentication

---

## Placeholder Format

**Standard:** `<<PLACEHOLDER_NAME>>`

**Rules:**

- All caps with underscores

- Descriptive name

- Must be registered in table below

---

## Placeholder Registry

**Every placeholder must be documented here. Automation will flag unregistered placeholders.**

| Placeholder | Example Format | Where Used | Rotation Schedule | Date Generated | Notes |
| --- | --- | --- | --- | --- | --- |
| `<<MAKE_WEBHOOK_URL>>` | [`https://hook.make.com/`](https://hook.make.com/)`...` | Phase 0, Phase 1 | N/A | — | Never publish real value |
| `<<AIRTABLE_PAT>>` | `patXXXXXXXX` | Phase 0, connections | 90 days |  | Stored device-only |
| `<<AIRTABLE_BASE_ID>>` | `appXXXXXXXX` | Phase docs, API calls | N/A | — | Treat as sensitive metadata |
| `<<AIRTABLE_TABLE_ID_PROJECTS>>` | `tblXXXXXXXX` | Phase 1, record creation | N/A | — | Sensitive metadata |
| `<<AIRTABLE_TABLE_ID_PEOPLE>>` | `tblXXXXXXXX` | Phase 1, record creation | N/A | — | Sensitive metadata |
| `<<AIRTABLE_TABLE_ID_IDEAS>>` | `tblXXXXXXXX` | Phase 1, record creation | N/A | — | Sensitive metadata |
| `<<AIRTABLE_TABLE_ID_ADMIN>>` | `tblXXXXXXXX` | Phase 1, record creation | N/A | — | Sensitive metadata |
| `<<AIRTABLE_TABLE_ID_EVENTS>>` | `tblXXXXXXXX` | Phase 1, record creation | N/A | — | Sensitive metadata |
| `<<AIRTABLE_TABLE_ID_INBOX_LOG>>` | `tblXXXXXXXX` | Phase 1, logging | N/A | — | Sensitive metadata |
| `<<CLAUDE_API_KEY>>` | `sk-ant-...` | Phase 1, HTTP modules | 90 days |  | Device-only |
| `<<SLACK_BOT_TOKEN>>` | `xoxb-...` | Phase 0, Slack connection | 90 days |  | Device-only |
| `<<SLACK_SIGNING_SECRET>>` | `********` | Phase 0, verification | 90 days |  | Never publish |
| `<<PERPLEXITY_API_KEY>>` | `pplx-...` | Phase 3, research | 90 days |  | Device-only |
| `<<NOTION_TOKEN>>` | `secret_...` | Git mirror automation | 90 days |  | Device-only |
| `<<GITHUB_TOKEN>>` | `github_pat_...` | Git mirror automation | 90 days | 2026-02-24 | Expires May 25, 2026. Device-only |

---

## Pre-Publish Sanitization Checklist

**Before exporting to Git, verify:**

- [ ] All tokens replaced with registered placeholders

- [ ] All inbound webhook URLs replaced with `<<MAKE_WEBHOOK_URL>>`

- [ ] No personal identifiers present (emails, phone numbers)

- [ ] All Airtable IDs replaced with appropriate placeholders

- [ ] All placeholders registered in table above

- [ ] Run automated pattern scan (see `/automation/redaction_patterns.txt`)

- [ ] Manual skim for "looks like a secret" strings (long alphanumeric, base64-like)

- [ ] No "disable verification" or "skip authentication" instructions

---

## Automated Scan Patterns

**Patterns that should trigger publish failure:**

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

**If any match found:** Block export, report match location, require manual review.
