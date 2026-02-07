# protocols/CHANGE_CONTROL.md

# Change Control Protocol

## Purpose

Define how changes flow between Notion (canonical source) and GitHub (public mirror + enforcement gate) while preventing drift and maintaining publish safety.

## Scope

Applies to all content in mirror publish scope:

- `CONTRACT.md`, `README.md`
- `contracts/`, `protocols/`, `phases/`
- `checks/`, `automation/`, `changelog/`, `reports/`

## Definitions

- **Canonical source**: Notion workspace (managed content and planning)
- **Enforcement gate**: GitHub CI (scan-secrets must pass)
- **Published**: Content merged to `main` branch in GitHub repo
- **Drift**: Mismatch between Notion content and GitHub mirror
- **Publish-safe**: No real secrets, placeholders only, CI passes

## Normal Flow (Notion → Export → Repo → PR)

**This is the default path for all changes.**

1. **Edit in Notion**
    - Update canonical Notion page
    - Mark page status: `[Mirrored to GitHub]`
    - Document GitHub path: `path/to/file.md`
2. **Pre-export checks**
    - [ ]  Replace sensitive values with `<<ALL_CAPS_WITH_UNDERSCORES>>`
    - [ ]  Add `EXAMPLE_SECRET:` marker to any secret-like examples
    - [ ]  Verify content matches governance in `contracts/spec.yaml`
3. **Export**
    - Export Notion page as Markdown
    - Place in correct repo directory
    - Verify filename matches GitHub path documented in Notion
4. **Commit to dev branch**
    
    ```bash
    git checkout dev
    git add [files]
    git commit -m "[descriptive message]"
    git push origin dev
    ```
    
5. **Create PR (dev → main)**
    - Create pull request on GitHub
    - Wait for CI checks to complete
    - **Do not merge if `scan-secrets` fails**
6. **Merge**
    - Merge PR after CI passes
    - Content is now **published**
7. **Record**
    - [ ]  Add entry to operational Drift Log (Notion)
    - [ ]  Update "Last Mirror Date" in Notion page
    - [ ]  Update "Currently Published" tracker

## Exception Flow (GitHub-First Hotfix → Backfill Notion)

**Use only for urgent CI fixes or repo-breaking issues.**

1. **Hotfix in repo**
    - Fix directly in `dev` branch or hotfix branch
    - Create PR, verify CI passes
    - Merge to `main`
2. **Backfill to Notion (within 24 hours)**
    - Update corresponding Notion page to match repo
    - Add note: `[Backfilled from GitHub hotfix YYYY-MM-DD]`
    - Record in operational Drift Log with explanation
3. **Prevent recurrence**
    - Document why hotfix was needed
    - Update pre-export checklist if applicable

## Review Checklist

**Before every commit to dev:**

- [ ]  No real credentials, API keys, tokens, or webhook URLs
- [ ]  All sensitive values use `<<ALL_CAPS_WITH_UNDERSCORES>>`
- [ ]  Secret-like examples prefixed with `EXAMPLE_SECRET:` on same line
- [ ]  Content stays inside publish scope paths
- [ ]  Filenames match Notion → GitHub path mapping
- [ ]  File paths use correct conventions:
    - `checks/scan_secrets.sh`
    - `automation/redaction_patterns.txt`
    - `contracts/spec.yaml`, `contracts/routes.yaml`
    - `contracts/AI_COLLABORATION.md`
    - `changelog/` (directory, not `CHANGELOG.md`)

**Before merging PR:**

- [ ]  CI check `scan-secrets` passes
- [ ]  PR description references Notion source page
- [ ]  Changes reviewed for publish safety

**After merge:**

- [ ]  Public Drift Log entry added
- [ ]  Notion page updated with latest mirror date
- [ ]  Operational Drift Log entry added

## What Counts as Drift

**Drift exists when:**

- Notion page content differs from corresponding GitHub file
- GitHub file exists but no Notion source page (orphan)
- Notion page marked `[Mirrored to GitHub]` but file missing from repo
- Notion page "GitHub Path" doesn't match actual repo structure
- "Last Mirror Date" in Notion older than actual file update in repo
- Public Drift Log missing entry for a merged PR

**Resolution priority:**

1. **For content/planning**: Notion wins (update repo from Notion)
2. **For CI behavior**: Repo wins (update Notion to document actual behavior)
3. **For sync conflicts**: Compare timestamps, use most recent, document reconciliation

**Drift detection cadence:**

- Manual review: monthly or after major mirror operations
- Automated check: (planned future enhancement)
- Ad-hoc: whenever uncertainty about Notion ↔ GitHub alignment

## Emergency Contacts

- **Maintainer**: `<<MAINTAINER_NAME>>`
- **Notion workspace**: `<<NOTION_WORKSPACE_ID>>`
- **GitHub repo**: `sharedterrain/brainstem-docs`