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

---

## Hybrid governance (Notion home base, Git integration point)

This system operates as a hybrid:

- **Notion is the home base** for planning, drafting, and database-managed knowledge.
- **GitHub is the integration point** for external agents/models and the canonical **published bytes** for the public mirror.

### Two lanes

**Lane A — Notion → Git (normal publishing lane)**
- Humans and Notion-native AI edit in Notion.
- When a doc is ready to publish, export/render it into the repo at the exact mirror path.
- Changes land via PR to `dev` and merge to `main` only when CI passes.

**Lane B — Git → Notion (agent/automation lane)**
- External agents/models propose changes only via PRs to `dev`.
- After merge to `main`, the corresponding Notion page must be updated (manually for now; automated later).
- If a Git change was made without Notion backfill, that is **drift** and must be reconciled.

### Source-of-truth by artifact type

- **Planning, tasks, database fields, and drafts:** Notion is canonical.
- **Public mirror published documents in publish scope:** GitHub `main` is canonical bytes.
- **CI behavior and security enforcement:** repo scripts + CI are canonical.

### Drift definition

Drift exists when:
- A publish-scope file in GitHub does not match its Notion source page, or
- A publish-scope file exists in GitHub with no Notion source page, or
- A Notion page claims a mirror path that does not exist in the repo.

### Resolution rule (when they disagree)

1) For **planning/drafts**: Notion wins.
2) For **published mirror bytes and CI behavior**: GitHub `main` wins.
3) Always document reconciliation in the operational drift log (Notion) when it occurs.
