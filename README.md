```markdown
# Notion-Mirror

Automated documentation mirror for the Notion Hub workspace.

## How it works

Notion is the canonical source. This repo is a read-only mirror — do not edit files here directly.

**Pipeline:**
1. Make scenario fetches raw block JSON from Notion via API
2. JSON committed to `_raw/` directory
3. GitHub Action converts block JSON to clean markdown
4. Markdown files published alongside source JSON

## Structure

```
_raw/          # Raw Notion block JSON (auto-generated, do not edit)
README.md      # This file
```

Content directories will appear here as the GitHub Action processes `_raw/` files. Directory structure mirrors the Notion Hub workspace organization.

## Governance

- **Canonical source:** Notion Hub workspace
- **Orchestration:** Make.com (Mirror Bulk Publish scenario)
- **Conversion:** GitHub Action (Python converter, triggers on `_raw/**/*.json` changes)
- **Credentials:** Never stored in this repo — managed in approved vaults

## Status

Mirror operational as of March 2026. GitHub Action (block JSON → markdown conversion) pending build.
```
