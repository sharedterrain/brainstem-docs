# Phase 0 — Public Mirror Setup

## Objective

- Create public GitHub repository
- Set up folder structure
- Establish security protocols
- Define publishing workflow
- Implement redaction checklist

## Inputs

- Notion workspace with Brain Stem documentation
- GitHub account
- Mac Terminal access
- Git installed locally

## Outputs

- Public GitHub repository: `<<REPO_URL>>`
- Complete folder scaffold
- Security protocols documented
- Pre-commit checklist in place
- Initial commit pushed

## Folder Map

```
brainstem-docs/
├── README.md
├── CONTRACT.md
├── protocols/
│   ├── SECURITY.md
│   ├── PUBLISHING.md
│   └── .gitkeep
├── contracts/
│   ├── spec.yaml
│   └── .gitkeep
├── phases/
│   ├── PHASE_0.md
│   └── .gitkeep
├── checks/
│   └── .gitkeep
├── automation/
│   ├── redaction_patterns.txt
│   └── .gitkeep
├── reports/
│   └── .gitkeep
├── examples/
│   └── .gitkeep
└── changelog/
    └── .gitkeep
```

## Redaction Rules

### Never commit

- API keys
- Tokens
- Webhook URLs (especially `hook.make.com`)
- Signing secrets
- Personal identifiers
- Database connection strings
- Private endpoints

### Always use placeholders

- Format: `<<ALL_CAPS_WITH_UNDERSCORES>>`
- Examples:
  - `<<MAKE_WEBHOOK_URL>>`
  - `<<SLACK_BOT_TOKEN>>`
  - `<<AIRTABLE_PAT>>`
  - `<<CLAUDE_API_KEY>>`
  - `<<NOTION_SOURCE_URL_OR_ID>>`

## Publishing Workflow

### GitHub Web UI Steps

- Navigate to `https://github.com/new`
- Enter repository name: `brainstem-docs`
- Select: Public
- Uncheck: Add a README file
- Uncheck: Add .gitignore
- Uncheck: Choose a license
- Click: Create repository
- Copy the HTTPS clone URL: `<<REPO_URL>>`

### Mac Terminal Steps (Initial Setup)

```bash
# Clone or init
cd ~/code
git clone <<REPO_URL>>
cd brainstem-docs

# Or if already initialized:
cd ~/code/brainstem-docs
git remote add origin <<REPO_URL>>
```

### Mac Terminal Steps (Create Scaffold)

```bash
# Create folders
mkdir -p protocols contracts phases checks automation reports examples changelog

# Create .gitkeep files
echo "keep" > protocols/.gitkeep
echo "keep" > contracts/.gitkeep
echo "keep" > phases/.gitkeep
echo "keep" > checks/.gitkeep
echo "keep" > automation/.gitkeep
echo "keep" > reports/.gitkeep
echo "keep" > examples/.gitkeep
echo "keep" > changelog/.gitkeep

# Create main files (use editor or copy from templates)
# README.md, CONTRACT.md, protocols/SECURITY.md, etc.
```

### Mac Terminal Steps (Add Content from Notion)

```bash
# Open file in editor
code path/to/file.md
# or
nano path/to/file.md

# Copy content from Notion
# Paste into editor
# Replace all sensitive values with placeholders
# Save and close
```

### Pre-Commit Checklist

Run these searches before every commit:

```bash
# Search for dangerous strings
grep -r "hook.make.com" .
grep -r "https://hook." .
grep -r "Authorization: Bearer" .
grep -r "xoxb-" .
grep -r "xoxp-" .
grep -r "sk-ant-" .
grep -r "BEGIN PRIVATE KEY" .
grep -r "api.airtable.com/v0/app" .
grep -r "secret_" .
```

- If any match found: replace with `<<PLACEHOLDER>>`
- Update `protocols/SECURITY.md` placeholder registry
- Re-run searches until clean

### Mac Terminal Steps (Commit and Push)

```bash
# Check status
git status

# Add files
git add .

# Commit
git commit -m "docs: scaffold repo"

# Push
git push origin main
```

## Verification

### Check folder structure

```bash
ls -la
ls -la protocols/
ls -la contracts/
ls -la phases/
ls -la checks/
ls -la automation/
ls -la reports/
ls -la examples/
ls -la changelog/
```

### Check for secrets

```bash
# Run pre-commit checklist searches
grep -r "hook.make.com" .
grep -r "xoxb-" .
grep -r "sk-ant-" .
# All should return no results
```

### Verify placeholder format

```bash
# Search for placeholder pattern
grep -r "<<[A-Z_]*>>" .
# Should return only valid placeholders
```

### GitHub Web UI Verification

- Navigate to `<<REPO_URL>>`
- Click: Code tab
- Verify all folders visible
- Click into: `protocols/SECURITY.md`
- Verify: no real webhook URLs or tokens
- Click: `README.md`
- Verify: rendering correctly

## Exit Criteria

- [ ] Public GitHub repository created
- [ ] All 8 folders exist with .gitkeep files
- [ ] README.md published
- [ ] CONTRACT.md published
- [ ] protocols/SECURITY.md published
- [ ] protocols/PUBLISHING.md published
- [ ] contracts/spec.yaml published
- [ ] automation/redaction_patterns.txt published
- [ ] Pre-commit checklist searches return zero results
- [ ] All placeholders use `<<FORMAT>>`
- [ ] Initial commit pushed to origin main
- [ ] Repository visible at `<<REPO_URL>>`
