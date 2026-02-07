# Brain Stem Docs (Public Mirror)

This repository is a **public, sanitized Markdown mirror** of Brain Stem documentation authored in Notion.

## Rules
- Public repo = **no secrets, no inbound webhook URLs, no personal identifiers**
- Use placeholders only: `<<LIKE_THIS>>`
- Run the pre-commit checklist in `protocols/SECURITY.md` before every commit

## Structure
- `CONTRACT.md` — blueprint (what must be true)
- `contracts/spec.yaml` — machine-readable anchors
- `phases/` — procedural build steps (how to implement)
- `protocols/` — publishing + security rules
- `checks/` — validation scripts/specs (public-safe)
- `automation/` — redaction patterns and automation notes
- `reports/` — QA outputs and audit notes
- `examples/` — sanitized examples
- `changelog/` — change history (public-safe)

## Notion Source
- Notion workspace/page: `<<NOTION_SOURCE_URL_OR_ID>>`

## Repo role
This is a project mirror repo for Brain Stem (project-only docs).

Reusable governance + CI + secret scanning + templates live in:
- https://github.com/sharedterrain/mirror-framework

Notion structure:
- Documentation Mirror System -> Projects -> Brain Stem Project
