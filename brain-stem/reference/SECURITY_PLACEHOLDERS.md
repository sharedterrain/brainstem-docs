<!-- Auto-generated from Notion. Do not edit directly. -->


**Security rules and placeholder registry**

This page defines what must never be published and maintains a registry of all placeholders used in documentation.


---


## Never Publish Categories


**The following must NEVER appear in Git mirror or public documentation:**

- **API keys, tokens, credentials**

- **Inbound webhook URLs**

- **Signing secrets**

- **Personal identifiers**

- **Database identifiers** (treat as sensitive metadata)

- **Connection strings**


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
