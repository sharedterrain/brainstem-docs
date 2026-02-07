# protocols/MIRRORING.md

# Mirroring Procedure (Notion → GitHub)

## Purpose

Step-by-step terminal procedure for mirroring Notion documentation to the `sharedterrain/brainstem-docs` public GitHub repo.

## Publish Scope

Only these paths are mirrored:

- `CONTRACT.md`
- `README.md`
- `contracts/`
- `protocols/`
- `phases/`
- `checks/`
- `automation/`
- `changelog/`
- `reports/`

## Preconditions

- [ ]  Notion pages marked `[Mirrored to GitHub]`
- [ ]  GitHub path documented on each Notion page
- [ ]  No real secrets in content (placeholders only: `<<ALL_CAPS_WITH_UNDERSCORES>>`)
- [ ]  Secret-like examples prefixed with `EXAMPLE_SECRET:` on same line
- [ ]  Local repo clone exists at `~/code/brainstem-docs` (or equivalent)

## Export from Notion

1. **Export page(s)**
    - In Notion, click `⋯` menu → Export
    - Format: **Markdown & CSV**
    - Include subpages: **No** (export each page individually)
    - Download and unzip
2. **Sanitization note**
    - Notion may export `file.md` references as links like `[[file.md](http://file.md)]([http://file.md](http://file.md))`
    - Before copying into the repo, strip link markup so it becomes plain text “file.md” (or put file paths inside fenced code blocks in Notion pages to avoid linkification)

## Copy into Repo

```bash
cd ~/code/brainstem-docs
git checkout dev
```

**Target paths (examples):**

```bash
# Root files
cp ~/Downloads/Export-*/README.md ./README.md
cp ~/Downloads/Export-*/CONTRACT.md ./CONTRACT.md

# Contracts (YAML): copy/paste from Notion code blocks into these files, then save
# contracts/spec.yaml
# contracts/routes.yaml
cp ~/Downloads/Export-*/AI_COLLABORATION.md ./contracts/AI_COLLABORATION.md

# Protocols
cp ~/Downloads/Export-*/SECURITY.md ./protocols/SECURITY.md
cp ~/Downloads/Export-*/PUBLISHING.md ./protocols/PUBLISHING.md
cp ~/Downloads/Export-*/CHANGE_CONTROL.md ./protocols/CHANGE_CONTROL.md
cp ~/Downloads/Export-*/MIRRORING.md ./protocols/MIRRORING.md

# Phases
cp ~/Downloads/Export-*/phase_0_setup.md ./phases/phase_0_setup.md
cp ~/Downloads/Export-*/phase_1_capture.md ./phases/phase_1_capture.md
cp ~/Downloads/Export-*/phase_2_classification.md ./phases/phase_2_classification.md

# Changelog entries
cp ~/Downloads/Export-*/2026-02-*.md ./changelog/
```

**Verify file placement:**

```bash
ls -la contracts/ protocols/ phases/ changelog/
```

## Local Validation

**Run secret scan:**

```bash
bash checks/scan_secrets.sh
```

**Expected output:**

```
🔍 Scanning for secrets in public mirror scope...
✅ No secrets found in publish scope
```

**If scan fails:**

1. Check CI output for line number
2. Fix: replace with `<<ALL_CAPS_WITH_UNDERSCORES>>` or add `EXAMPLE_SECRET:` marker
3. Re-run scan until clean

## Commit and PR

```bash
# Stage changes
git add CONTRACT.md README.md contracts/ protocols/ phases/ changelog/

# Commit with descriptive message
git commit -m "docs: mirror [page names] from Notion

- Updated contracts/spec.yaml
- Added protocols/MIRRORING.md
- Exported Phase 0 and Phase 1 docs

Notion sources:
- [list Notion page URLs or titles]"

# Push to dev
git push origin dev
```

**Create PR on GitHub:**

1. Navigate to [`https://github.com/sharedterrain/brainstem-docs`](https://github.com/sharedterrain/brainstem-docs)
2. Create pull request: `dev` → `main`
3. Title: `Mirror sync: [description]`
4. Body: link to Notion source pages
5. Wait for CI check `scan-secrets` to pass ✅
6. Merge PR

## Post-Merge Backfill

**After merge to main:**

```bash
# Pull latest
git checkout main
git pull origin main

# Confirm published
git log --oneline -5
```

**Update Notion:**

- [ ]  Mark pages with `Last Mirror Date: YYYY-MM-DD`
- [ ]  Add entry to operational Drift Log
- [ ]  Update Currently Published tracker

## Exception: Git-First Changes

**If changes made directly in GitHub (hotfix):**

1. Pull latest from `main`
2. Update corresponding Notion pages within 24 hours
3. Add note in Notion: `[Backfilled from GitHub hotfix YYYY-MM-DD]`
4. Document in operational Drift Log with explanation

## Troubleshooting

**CI scan fails:**

- Check pattern file: `automation/redaction_patterns.txt`
- Verify all secrets use `<<ALL_CAPS_WITH_UNDERSCORES>>` format
- Confirm examples have `EXAMPLE_SECRET:` marker on same line

**File not in publish scope:**

- Verify path matches `contracts/spec.yaml` publish_scope definition
- If needed, update spec.yaml first, then re-export

**Notion export contains sensitive data:**

- **STOP** - do not commit
- Return to Notion, replace with placeholder
- Re-export clean version
- Never commit real credentials to public repo

## Quick Reference

```bash
# Standard mirror workflow
cd ~/code/brainstem-docs
git checkout dev
git pull origin dev

# Copy exported files to correct paths
cp [source] [target]

# Validate
bash checks/scan_secrets.sh

# Commit
git add .
git commit -m "docs: mirror [description]"
git push origin dev

# Create PR on GitHub (dev → main)
# Wait for CI, merge

# Backfill Notion with mirror date
```
Multi-project architecture
- Framework repo holds reusable enforcement boundary + templates:
  - https://github.com/sharedterrain/mirror-framework
- This repo holds Brain Stem project docs only.
- Never place framework-phase docs into this project repo.
