# phases/phase_0_setup.md

# Phase 0: Setup & Configuration

## Objective

Establish and validate the Notion → GitHub mirror system for `sharedterrain/brainstem-docs`, ensuring CI gates work and Notion source pages are ready for Stage 2 exports.

## Preconditions

- [ ]  GitHub account with access to `sharedterrain/brainstem-docs`
- [ ]  Git installed locally
- [ ]  Text editor (VS Code recommended)
- [ ]  Bash shell (macOS/Linux/WSL)
- [ ]  Notion workspace access with export permissions

## Repo Setup

### Clone Repository

```bash
# Clone repo
git clone https://github.com/sharedterrain/brainstem-docs.git
cd brainstem-docs

# Verify remote
git remote -v
```

### Checkout Dev Branch

```bash
# Switch to dev branch
git checkout dev

# Pull latest
git pull origin dev

# Verify current branch
git branch
```

## Verify Publish-Scope Tree

**Check that these paths exist:**

```bash
# List publish-scope directories
ls -la
ls -la contracts/
ls -la protocols/
ls -la phases/
ls -la checks/
ls -la automation/
ls -la changelog/
ls -la reports/
```

**Expected structure:**

```
brainstem-docs/
├── CONTRACT.md
├── README.md
├── contracts/
│   ├── spec.yaml
│   ├── routes.yaml
│   └── AI_COLLABORATION.md
├── protocols/
│   ├── SECURITY.md
│   ├── PUBLISHING.md
│   ├── CHANGE_CONTROL.md
│   ├── MIRRORING.md
│   └── OPERATING.md
├── phases/
│   └── (phase docs)
├── checks/
│   └── scan_secrets.sh
├── automation/
│   └── redaction_patterns.txt
├── changelog/
│   └── (changelog entries)
└── reports/
    └── (QA reports)
```

**Verify exclusions:**

```bash
# examples/ should NOT exist or should be in .gitignore
ls -la examples/ 2>/dev/null || echo "examples/ correctly excluded"
```

## Run Local Checks

### Validate Secret Scan

```bash
# Run secret scan on current content
bash checks/scan_secrets.sh
```

**Expected output:**

```
🔍 Scanning for secrets in public mirror scope...
✅ No secrets found in publish scope
```

**If scan fails:**

- Review pattern file:
    
    ```bash
    cat automation/redaction_patterns.txt
    ```
    
- Check for real secrets in code
- Verify `EXAMPLE_SECRET:` markers on example lines

### Verify Pattern File

```bash
# Review current patterns
cat automation/redaction_patterns.txt
```

**Should include patterns for:**

- Slack tokens (`xoxb-`, `xoxp-`)
- Webhook URLs ([`hook.make.com`](http://hook.make.com), [`https://hook`](https://hook))
- API keys (`sk-ant-`, `Authorization: Bearer`)
- Airtable patterns ([`api.airtable.com/v0/app`](http://api.airtable.com/v0/app))
- Generic secrets (`secret_`, `BEGIN PRIVATE KEY`)

## Notion Source Pages Required

**Under 🏠 Documentation Mirror System, verify these pages exist:**

### Already Created (Stage 1)

- [ ]  `README.md`
- [ ]  `contracts/routes.yaml`
- [ ]  `contracts/AI_COLLABORATOIN.md`

### Stage 2 Protocol Pages

- [ ]  `protocols/CHANGE_CONTROL.md`
- [ ]  `protocols/MIRRORING.md`
- [ ]  `protocols/OPERATING.md`

### Stage 2 Phase Pages

- [ ]  `phases/phase_0_setup.md` (this page)
- [ ]  Additional phase pages as needed

**Each page must have:**

- Title matching exact repo path
- Mirror status banner: `[Mirrored to GitHub]` or `[Notion-only]`
- GitHub path documented if mirrored
- No real secrets (placeholders only: `<<FORMAT>>`)
- Secret examples marked with `EXAMPLE_SECRET:` on same line

## Export + Copy Procedure

### Export from Notion

1. **Select page to mirror**
2. **Click ⋯ menu → Export**
    - Format: Markdown & CSV
    - Include subpages: No
3. **Download and unzip**
4. **Sanitize if needed** (strip linkified filenames)

### Copy to Repo

**Example for protocols:**

```bash
# Assuming exported files in ~/Downloads/Export-*/
cd ~/code/brainstem-docs
git checkout dev

# Copy protocol files
cp ~/Downloads/Export-*/CHANGE_CONTROL.md ./protocols/CHANGE_CONTROL.md
cp ~/Downloads/Export-*/MIRRORING.md ./protocols/MIRRORING.md
cp ~/Downloads/Export-*/OPERATING.md ./protocols/OPERATING.md

# Copy phase files
cp ~/Downloads/Export-*/phase_0_setup.md ./phases/phase_0_setup.md

# Verify placement
ls -la protocols/
ls -la phases/
```

### Validate Before Commit

```bash
# Run secret scan
bash checks/scan_secrets.sh

# Review changes
git status
git diff
```

## PR Procedure (dev → main)

### Commit Changes

```bash
# Stage files
git add protocols/ phases/

# Commit with descriptive message
git commit -m "docs: Phase 0 mirror - add protocols and phase docs

- Added protocols/CHANGE_CONTROL.md
- Added protocols/MIRRORING.md
- Added protocols/OPERATING.md
- Added phases/phase_0_setup.md

Notion sources:
- 🏠 Documentation Mirror System"

# Push to dev
git push origin dev
```

### Create Pull Request

1. **Navigate to:**
    
    ```
    https://github.com/sharedterrain/brainstem-docs
    ```
    
2. **Create PR:**
    - Base: `main`
    - Compare: `dev`
    - Title: `Phase 0: Mirror protocols and phase docs`
    - Description: Link to Notion pages
3. **Wait for CI:**
    - Status check: `scan-secrets` must pass ✅
4. **Merge PR** when green

### Backfill Notion

```bash
# Pull merged changes
git checkout main
git pull origin main

# Verify in log
git log --oneline -5
```

**Update Notion pages:**

- Add `Last Mirror Date: YYYY-MM-DD` to each mirrored page
- Update operational Drift Log
- Mark in "Currently Published" tracker

## Exit Criteria

**Phase 0 is complete when:**

- [ ]  Local repo cloned and `dev` branch active
- [ ]  Publish-scope tree verified (correct directories present)
- [ ]  `examples/` excluded from publish scope
- [ ]  Secret scan passes locally: `bash checks/scan_secrets.sh`→ ✅
- [ ]  Pattern file validated and correct
- [ ]  All required Notion source pages exist under 🏠 Documentation Mirror System
- [ ]  Stage 1 pages mirrored:
    - `README.md`
    - `contracts/routes.yaml`
    - `contracts/AI_COLLABORATION.md`
- [ ]  Stage 2 protocol pages mirrored:
    - `protocols/CHANGE_CONTROL.md`
    - `protocols/MIRRORING.md`
    - `protocols/OPERATING.mc`
- [ ]  Stage 2 phase page mirrored:
    - `phases/phase_0_setup.md`
- [ ]  PR (dev → main) created and merged successfully
- [ ]  CI check `scan-secrets` passed on GitHub ✅
- [ ]  Notion pages updated with mirror dates
- [ ]  Drift Log entries recorded

**Once exit criteria met, Phase 0 is complete.**

## Next Phase

Proceed to Phase 1: Brain Dump Capture (when ready).

## Troubleshooting

**Problem: Secret scan fails**

- Check output for matched pattern and line number
- Replace real secrets with `<<PLACEHOLDER>>`
- Add `EXAMPLE_SECRET:` to intentional examples
- Re-run scan until clean

**Problem: Notion export has linkified filenames**

- Find/replace: `[[filename.md](http://filename.md)](url)` → `filename.md`
- Or manually edit before copying to repo
- Future prevention: use code blocks in Notion content

**Problem: examples/ directory still in repo**

- Check if in publish scope: `cat contracts/spec.yaml`
- If not in scope, remove:
    
    ```bash
    git rm -r examples/
    git commit -m "chore: remove examples/ from publish scope"
    ```
    
- Or add to scope if needed (update spec.yaml first)

**Problem: CI check doesn't run**

- Verify GitHub Actions workflow exists:
    
    ```bash
    cat .github/workflows/validate.yml
    ```
    
- Check repo Settings → Actions → enabled
- Review Actions tab for error logs