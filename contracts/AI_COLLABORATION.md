# AI Collaboration Contract (Brainstem Docs)

This repo is a public mirror. Any agent (ChatGPT, Claude, Notion AI, scripts) MUST follow these rules when producing or editing content that may be published here.

## Scope

- This contract applies to all content in publish scope:
  - CONTRACT.md, README.md
  - contracts/, protocols/, phases/, checks/, automation/, changelog/, reports/

## Non-negotiable invariants

1) **No secrets in public mirror**
- Never include real credentials, API keys, tokens, private keys, session cookies, or real webhook URLs.

2) **Placeholders only**
- Any sensitive value must be represented as a placeholder:
  - Format: `<<ALL_CAPS_WITH_UNDERSCORES>>`
  - Examples: `<<NOTION_TOKEN>>`, `<<MAKE_WEBHOOK_URL>>`, `<<SLACK_BOT_TOKEN>>`

3) **Examples must be marked**
- If documentation needs to show secret-like example strings (e.g., token prefixes, key headers, webhook domains), the line MUST be prefixed with:
  - `EXAMPLE_SECRET:`
- CI secret scanning ignores lines containing `EXAMPLE_SECRET:`. Unmarked secret-like strings will fail CI.

## How agents should propose changes

- Prefer small, reviewable diffs.
- Do not rename/move files without updating references in docs and contracts.
- If CI fails, first fix the smallest change that makes CI green (do not widen exclusions unless necessary).

## Definition of “publish safe”

A change is publish safe if:
- It stays inside publish scope
- It introduces no real secrets
- Any secret-like example strings are explicitly marked with `EXAMPLE_SECRET:`
- `checks/scan_secrets.sh` passes on PR
