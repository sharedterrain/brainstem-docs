# protocols/OPERATING.md

# Operating Protocol (Mirror System)

## Purpose

Daily runbook for maintaining the Notion ↔ GitHub public mirror system for `sharedterrain/brainstem-docs`.

## Daily/Weekly Operations

**Daily:**

- Check GitHub Actions status for failed CI runs
- Review any open PRs waiting for merge
- Monitor operational Drift Log for unresolved items

**Weekly:**

- Run drift detection reconciliation checklist
- Review "Currently Published" tracker vs actual repo state
- Check for orphaned files (in repo but no Notion source)
- Verify mirror status banners on Notion pages match reality

**Monthly:**

- Full drift audit (compare all Notion pages marked `[Mirrored to GitHub]` to repo files)
- Review and update placeholder patterns if needed
- Archive old changelog entries

## Pre-Publish Checklist

**Before exporting from Notion:**

- [ ]  Content marked `[Mirrored to GitHub]` in Notion
- [ ]  GitHub path documented on page
- [ ]  All sensitive values replaced with placeholders:
    
    ```
    <<SLACK_WEBHOOK_URL>>
    <<AIRTABLE_API_KEY>>
    <<NOTION_TOKEN>>
    ```
    
- [ ]  Secret-like examples prefixed with `EXAMPLE_SECRET:` on same line
- [ ]  File paths inside code blocks (prevents linkification)

**Before committing to dev:**

- [ ]  Exported markdown sanitized (strip any auto-linkified filenames)
- [ ]  Files placed in correct repo paths per publish scope
- [ ]  Local secret scan passes:
    
    ```bash
    bash checks/scan_secrets.sh
    ```
    

**Before merging PR:**

- [ ]  CI check `scan-secrets` passes on GitHub
- [ ]  PR description references Notion source pages
- [ ]  Branch is up-to-date with main

## Troubleshooting

### Secret Scan Failures

**Symptom:** `scan-secrets` fails in CI or locally

**Diagnosis:**

```bash
bash checks/scan_secrets.sh
# Output shows matched pattern and line number
```

**Resolution:**

1. **Real secret detected:**
    - Replace with placeholder: `<<DESCRIPTIVE_NAME>>`
    - Re-run scan
    - Never commit real credentials
2. **Intentional example:**
    - Add `EXAMPLE_SECRET:` marker on same line
    - Example:
    
    ```bash
    curl -H "Authorization: Bearer demo_abc123" EXAMPLE_SECRET: https://api.example.com
    ```
    
    - Re-run scan
3. **False positive:**
    - Review pattern in:
        
        ```
        automation/redaction_patterns.txt
        ```
        
    - If pattern too broad, refine it (requires PR + CI pass)
    - Document in change control

### Linkification in Exports

**Symptom:** Notion export contains linked filenames like `[[README.md](http://README.md)]([http://readme.md/](http://readme.md/))`

**Prevention:**

- Put file paths in code blocks when writing Notion content
- Example:
    
    ```
    See `contracts/spec.yaml` for details.
    ```
    

**Cleanup:**

- Manual find/replace before committing:
    - Find: `[[filename.md](http://filename.md)]([http://filename.md/](http://filename.md/))`
    - Replace: `filename.md`
- Or use inline code: Find `[\`file`](url)`, replace with` `file``

### Drift Detected

**Symptom:** Notion content differs from repo file

**Resolution priority:**

1. **Content/planning drift:** Notion wins → update repo
2. **CI behavior drift:** Repo wins → update Notion to document actual behavior
3. **Timestamp conflict:** Use most recent, document reconciliation

**Steps:**

- Compare Notion page to repo file
- Determine source of truth per resolution priority
- Update lagging system
- Record in operational Drift Log
- Add Public Drift Log entry if repo changed

## Repo Workflow (dev → main PR)

**Standard flow:**

```bash
# 1. Switch to dev and pull latest
cd ~/code/brainstem-docs
git checkout dev
git pull origin dev

# 2. Copy exported files to repo
cp [source] [target]

# 3. Validate locally
bash checks/scan_secrets.sh

# 4. Stage and commit
git add .
git commit -m "docs: [description]

Notion sources:
- [page URLs or titles]"

# 5. Push to dev
git push origin dev

# 6. Create PR on GitHub (dev → main)
# Wait for CI to pass

# 7. Merge PR

# 8. Backfill Notion (see below)
```

**Branch protection rules:**

- PRs required before merge to main
- Status check `scan-secrets` must pass
- Branch must be up-to-date with main

## Notion Backfill Rule (Git-First Changes)

**Normal rule:** Notion is canonical → changes flow Notion → Git

**Exception:** Git-first hotfix (urgent CI fix, repo-breaking issue)

**If you made changes directly in Git:**

1. **Merge the fix** (dev → main)
2. **Within 24 hours, backfill Notion:**
    - Update corresponding Notion page to match repo
    - Add note: `[Backfilled from GitHub hotfix YYYY-MM-DD]`
    - Add entry to operational Drift Log with explanation
3. **Document why** hotfix was necessary
4. **Update pre-publish checklist** if hotfix revealed a gap

**When NOT to use Git-first:**

- Routine content updates (always use Notion → Git flow)
- New features or protocol changes (plan in Notion first)
- Non-urgent corrections (use normal flow)

## Post-Merge Checklist

**After PR merged to main:**

- [ ]  Pull latest from main:
    
    ```bash
    git checkout main
    git pull origin main
    ```
    
- [ ]  Update Notion pages:
    - Add `Last Mirror Date: YYYY-MM-DD`
    - Update operational Drift Log
    - Update "Currently Published" tracker
- [ ]  Verify published at:
    
    ```
    https://github.com/sharedterrain/brainstem-docs
    ```
    

## Emergency Contacts

- **Repo owner:** `<<GITHUB_USERNAME>>`
- **Notion workspace:** `<<NOTION_WORKSPACE_ID>>`
- **Maintainer:** `<<MAINTAINER_NAME>>`

## Quick Reference

**Publish scope paths:**

```
CONTRACT.md
README.md
contracts/
protocols/
phases/
checks/
automation/
changelog/
reports/
```

**Placeholder format:**

```
<<ALL_CAPS_WITH_UNDERSCORES>>
```

**Example secret marker:**

```
EXAMPLE_SECRET:
```

**Secret scan command:**

```bash
bash checks/scan_secrets.sh
```
Operator gate: framework vs project
Before exporting/pushing any doc, decide:
- FRAMEWORK -> belongs in sharedterrain/mirror-framework
- PROJECT -> belongs in this repo
