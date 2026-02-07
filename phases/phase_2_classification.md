# phases/phase_2_classification.md

# Phase 2: Classification & Routing

## Objective

Turn captured brain dumps into classified, routed entries with confidence scores. Establish manual classification workflow first, then layer in LLM automation.

## Inputs (from Phase 1)

**Source:** Inbox Log database

**Entry structure:**

```yaml
- Raw Input: text (brain dump content)
- Timestamp: date (capture time)
- Source: select (Slack, Manual, Email)
- Status: select (New, Processed, Archived)
- Routing Prefix: text (extracted prefix like PRO:, BD:, etc.)
```

**Phase 2 adds:**

```yaml
- Classification Confidence: number (0.00 to 1.00)
- Destination: relation (links to target database)
- Processing Notes: text (classification reasoning)
```

## Classification Scheme

**Routing prefixes defined in governance:**

See repo governance for authoritative routing rules.

**Prefix definitions:**

- **PRO:** Project extraction (confidence 1.0, deterministic destination Projects, extraction-only)
    - Runs LLM extraction to populate structured fields
    - No classification step needed (destination fixed)
    - Always auto-files to Projects database
- **BD:** Brain dump (requires LLM classification)
    - Needs semantic analysis
    - Destination determined by content
    - May route to Projects, People, Ideas, Admin, or Events
- **CAL:** Calendar/event (scaffolded in Phase 2)
    - Event scheduling requests
    - Date/time extraction needed
    - Destination: Events database
- **R:** Research (scaffolded in Phase 2)
    - Research tasks or queries
    - Destination: Research Jobs database
- **fix:** Corrections (scaffolded in Phase 2)
    - Updates to existing entries
    - Requires lookup and update logic
    - Destination: varies based on target

**Classification process:**

1. **Extract prefix** from Raw Input (first line or leading text)
2. **Score confidence** (0.00 to 1.00)
3. **Determine destination** database
4. **Route entry** (auto if confidence ≥ threshold, manual review if below)

## Confidence Thresholds

**Threshold defined in governance:**

The governance document specifies the auto-file threshold.

**Scoring rules:**

```yaml
Confidence = 1.0:
  - PRO: prefix (always bypass LLM, direct extraction)
  - Explicit, unambiguous routing
  - No semantic analysis needed

Confidence ≥ 0.60:
  - Auto-file to destination
  - LLM classification passed threshold
  - Operator review optional

Confidence < 0.60:
  - Manual review required
  - Entry stays in Inbox Log
  - Status = "Needs Review"
  - Operator assigns destination
```

**Example classifications:**

```yaml
Input: "PRO: Update mirror docs Phase 2 by Friday"
  Prefix: PRO
  Confidence: 1.0
  Destination: Projects
  Action: Auto-file

Input: "BD: Interesting conversation about AI governance frameworks"
  Prefix: BD
  Confidence: 0.75 (LLM scored)
  Destination: Ideas (LLM determined)
  Action: Auto-file

Input: "BD: Something about that thing we discussed"
  Prefix: BD
  Confidence: 0.35 (LLM scored low)
  Destination: Unknown
  Action: Needs Review
```

## Output Destinations (Notion DB Targets)

**Destination databases:**

```yaml
Projects:
  - Structured project tracking
  - Fields: Project Name, Status, Due Date, Owner, Notes
  - High confidence routing

People:
  - Contact and relationship tracking
  - Fields: Name, Role, Company, Notes, Last Contact
  - Requires person entity extraction

Ideas:
  - Unstructured idea capture
  - Fields: Title, Description, Category, Status
  - Low friction, high volume

Admin:
  - Administrative tasks and notes
  - Fields: Task, Priority, Due Date, Status
  - Catch-all for operational items

Events:
  - Calendar and scheduling
  - Fields: Title, Date/Time, Attendees, Location, Notes
  - Requires date/time extraction (Phase 2 scaffolded)

Research Jobs:
  - Research tasks and queries
  - Fields: Query, Status, Priority, Results
  - Links to Articles, Drafts, Publications
  - (Phase 3+, scaffolded in Phase 2)
```

## Manual Workflow (Phase 2 Initial)

**Current state: Operator-driven classification**

### Step 1: Review Inbox Log

```bash
# Open Notion
# Navigate to: Brain Stem Project → Inbox Log
# Filter: Status = "New"
```

### Step 2: Classify Entry

**For each entry:**

1. **Read Raw Input**
2. **Identify routing prefix** (if present)
3. **Determine destination:**
    - PRO: → Projects (confidence 1.0)
    - BD: → Operator decides based on content
    - CAL: → Events (scaffolded)
    - R: → Research Jobs (scaffolded)
    - fix: → Target database (scaffolded)
4. **Assign confidence:**
    - Clear and unambiguous: 0.80-1.0
    - Requires interpretation: 0.40-0.79
    - Unclear or incomplete: 0.0-0.39
5. **Update Inbox Log entry:**
    - Set Classification Confidence field
    - Set Destination relation
    - Add Processing Notes (optional)
    - Change Status to "Processed"

### Step 3: Create Destination Entry

**If confidence ≥ threshold (0.60):**

```bash
# Create new entry in destination database
# Copy relevant data from Raw Input
# Link back to Inbox Log entry (audit trail)
# Mark Inbox Log Status = "Processed"
```

**If confidence < threshold:**

```bash
# Leave in Inbox Log
# Set Status = "Needs Review"
# Add Processing Notes explaining uncertainty
# Revisit later or request clarification
```

## Automation (Phase 2 Planned, Not Implemented Yet)

**Future LLM classification workflow:**

```yaml
Trigger:
  - New entry in Inbox Log
  - Status = "New"
  - Routing Prefix extracted

Process:
  1. PRO: prefix → confidence = 1.0, run extraction-only (no classification), auto-file to Projects
  2. Other prefixes → send to LLM (Claude/Perplexity)
  3. LLM returns:
     - Classification label
     - Confidence score (0.00-1.00)
     - Destination database
     - Reasoning (for Processing Notes)
  4. If confidence ≥ 0.60:
     - Auto-create entry in destination
     - Update Inbox Log (Processed)
     - Log success
  5. If confidence < 0.60:
     - Update Inbox Log (Needs Review)
     - Notify operator
     - Wait for manual classification

LLM Prompt Structure:
  - System: Classification rules from governance
  - User: Raw Input text
  - Output: JSON with label, confidence, destination, reasoning

API Integration:
  - Make.com scenario
  - Claude API: <<CLAUDE_API_KEY>>
  - Notion API: <<NOTION_API_TOKEN>>
  - Airtable (intermediate if needed): <<AIRTABLE_PAT>>
```

**Phase 2 scope:**

- Manual classification workflow validated
- Destination databases created and tested
- Confidence scoring documented
- LLM integration designed (not implemented)
- Operator can process 10+ entries efficiently

**Phase 3+ scope (future):**

- LLM auto-classification implemented
- Structured field extraction (dates, people, projects)
- Batch processing
- Feedback loop (operator corrections improve LLM)

## Governance References

**Repo governance documents:**

```
CONTRACT.md
contracts/spec.yaml
contracts/routes.yaml
contracts/AI_COLLABORATION.md
checks/scan_secrets.sh
```

**Key governance rules:**

- Routing prefixes and confidence thresholds defined in routes.yaml
- Auto-file threshold (auto_file_confidence_min) defined in routes.yaml
- Invariants for classification integrity defined in spec.yaml
- Secret scan enforces publish safety (no real credentials)

## Exit Criteria

**Phase 2 is complete when:**

- [ ]  All destination databases created:
    - Projects
    - People
    - Ideas
    - Admin
    - Events (scaffolded)
    - Research Jobs (scaffolded)
- [ ]  Inbox Log extended with Phase 2 fields:
    - Classification Confidence (number)
    - Destination (relation)
    - Processing Notes (text)
- [ ]  Manual classification workflow documented and tested
- [ ]  Operator can classify 10+ entries:
    - Extract routing prefix
    - Assign confidence score
    - Select destination database
    - Create entry in destination
    - Update Inbox Log status
- [ ]  Confidence threshold (0.60) validated:
    - High confidence entries (≥ 0.60) route cleanly
    - Low confidence entries (< 0.60) flagged for review
    - No ambiguous auto-files
- [ ]  PRO: prefix extraction tested:
    - PRO entries always confidence 1.0
    - LLM extraction populates Projects fields
    - Auto-file to Projects (no classification)
    - < 2 seconds processing time
- [ ]  Audit trail maintained:
    - Inbox Log preserves all raw inputs
    - Destination entries link back to Inbox Log
    - No data loss in routing
- [ ]  Documentation updated:
    - Classification scheme documented
    - Confidence scoring guidelines documented
    - Manual workflow procedure documented
- [ ]  LLM integration designed (not implemented):
    - API endpoints identified
    - Prompt templates drafted
    - Error handling designed
    - Ready for Phase 3 implementation

**Once exit criteria met, Phase 2 is complete.**

## Next Phase

Proceed to Phase 3: Research Pipeline (LLM classification automation).

**Phase 3 will add:**

- Claude/Perplexity API integration
- Auto-classification for BD: prefix entries
- Confidence scoring automation
- Batch processing
- Operator feedback loop

## Troubleshooting

### Problem: Unclear routing prefix

**Symptoms:**

- Entry has no prefix or ambiguous prefix
- Operator unsure which database to target

**Resolution:**

```
1. Check Raw Input for implicit signals:
   - Person names → People
   - Project names → Projects
   - Dates/times → Events
   - Questions → Research Jobs or Ideas
2. If still unclear:
   - Set confidence = 0.30 (low)
   - Status = "Needs Review"
   - Add Processing Notes: "Ambiguous content, requires clarification"
   - Follow up with original author if possible
```

### Problem: Confidence score inconsistent

**Symptoms:**

- Different operators assign different scores to similar entries
- No clear scoring guidelines

**Resolution:**

```
1. Document scoring rubric:
   - 1.0 = Explicit prefix (PRO:) or unambiguous content
   - 0.8-0.9 = Clear intent, minor interpretation needed
   - 0.6-0.79 = Requires moderate interpretation, reasonable confidence
   - 0.4-0.59 = Ambiguous, multiple destinations possible
   - 0.0-0.39 = Unclear, needs clarification
2. Calibrate with test set:
   - Classify 20 test entries
   - Compare operator scores
   - Discuss discrepancies
   - Refine rubric
3. Review periodically as volume increases
```

### Problem: Destination database missing fields

**Symptoms:**

- Cannot fully populate destination entry
- Fields in Inbox Log Raw Input don't map to destination schema

**Resolution:**

```
1. Review destination database schema
2. Add missing fields if needed (update governance first)
3. Or: adjust extraction expectations
   - Store partial data
   - Flag for enrichment later
   - Don't block on missing optional fields
4. Document field mapping:
   - Inbox Log Raw Input → Destination fields
   - Clear examples for each destination
```

### Problem: Auto-file threshold too low/high

**Symptoms:**

- Too many low-quality auto-files (threshold too low)
- Too many manual reviews (threshold too high)

**Resolution:**

```
1. Review classified entries over 1 week:
   - Count auto-files that needed correction
   - Count manual reviews that were obvious
2. Adjust threshold in governance (contracts/routes.yaml):
   - If ≥ 10% auto-files wrong → raise threshold
   - If ≥ 50% manual reviews obvious → lower threshold
3. Document change in changelog/
4. Re-test with new threshold
```

## Mirror Note

This page exports to `phases/phase_2_classification.mc`and must remain publish-safe.