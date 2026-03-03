# Invariants & Checks (Brain Stem)

**System invariants and validation rules**

Each invariant is a rule that must always hold true. Violations indicate drift between contract and implementation.

---

## Invariant List

### INV-001: Inbox Log Singleton

- **ID:** `inv_inboxlog_singleton`

- **Severity:** Critical

- **Rule:** Every capture yields exactly one Inbox Log record

- **Given:** A Slack message is captured

- **When:** The pipeline executes

- **Then:** Exactly one Inbox Log record exists with matching `(SlackChannel, SlackMessageTS)`

- **Evidence:** Query Inbox Log for duplicates by `(SlackChannel, SlackMessageTS)`

- **Resolution:** Implement idempotency: search before create, use unique key constraint

---

### INV-002: PRO Route Confidence

- **ID:** `inv_pro_confidence`

- **Severity:** Warning

- **Rule:** PRO route must set confidence to 1.0

- **Given:** A message with `PRO:` prefix

- **When:** Routed to Projects

- **Then:** Inbox Log shows `Confidence = 1.0`

- **Evidence:** Query Inbox Log where `FiledTo = "Projects"` and `OriginalText` starts with `PRO:`

- **Resolution:** Verify PRO route module sets confidence explicitly to 1.0

---

### INV-003: Filed Status Has Destination

- **ID:** `inv_filed_has_destination`

- **Severity:** Critical

- **Rule:** Inbox Log with Status=Filed must have DestinationName and DestinationURL

- **Given:** An Inbox Log record

- **When:** `Status = "Filed"`

- **Then:** Both `DestinationName` and `DestinationURL` are non-empty

- **Evidence:** Query Inbox Log where `Status = "Filed"` and (`DestinationName` is empty OR `DestinationURL` is empty)

- **Resolution:** Update filing modules to populate both fields before setting Status=Filed

---

### INV-004: Confidence Range

- **ID:** `inv_confidence_range`

- **Severity:** Critical

- **Rule:** Confidence must be between 0.0 and 1.0

- **Given:** An Inbox Log record

- **When:** Created or updated

- **Then:** `0.0 ≤ Confidence ≤ 1.0`

- **Evidence:** Query Inbox Log where `Confidence < 0.0` OR `Confidence > 1.0`

- **Resolution:** Add validation in parsing module; reject values outside range

---

### INV-005: Original Text Immutable

- **ID:** `inv_original_text_immutable`

- **Severity:** Critical

- **Rule:** OriginalText in Inbox Log must never be modified after creation

- **Given:** An Inbox Log record exists

- **When:** Any update occurs

- **Then:** `OriginalText` remains unchanged from creation

- **Evidence:** Version history audit (manual review for now)

- **Resolution:** Make OriginalText read-only in Airtable interface; never update in Make modules

---

### INV-006: Clean Text Derivation

- **ID:** `inv_clean_text_derivation`

- **Severity:** Warning

- **Rule:** clean_text variable must be derived from OriginalText, never from user input

- **Given:** A capture is processed

- **When:** clean_text is set

- **Then:** clean_text = strip_prefix(OriginalText)

- **Evidence:** Review Make module configuration for clean_text variable

- **Resolution:** Verify variable formula uses `replace()` function on OriginalText field

---

### INV-007: Slack Thread TS Consistency

- **ID:** `inv_slack_thread_consistency`

- **Severity:** Warning

- **Rule:** If message is not threaded, SlackThreadTS should equal SlackMessageTS

- **Given:** A non-threaded Slack message

- **When:** Inbox Log is created

- **Then:** `SlackThreadTS = SlackMessageTS`

- **Evidence:** Review initial capture module configuration

- **Resolution:** Set SlackThreadTS to `event.thread_ts` if present, else `event.ts`

---

### INV-008: Auto-File Threshold

- **ID:** `inv_auto_file_threshold`

- **Severity:** Warning

- **Rule:** Messages with confidence ≥ 0.60 must auto-file; < 0.60 must go to Needs Review

- **Given:** Claude returns confidence score

- **When:** Router evaluates destination

- **Then:** confidence ≥ 0.60 → Status = Filed, confidence < 0.60 → Status = Needs Review

- **Evidence:** Query Inbox Log for mismatches between Confidence and Status

- **Resolution:** Verify router filter conditions use `≥ 0.60` for auto-file routes

---

### INV-009: LLM Output JSON Only

- **ID:** `inv_llm_json_only`

- **Severity:** Critical

- **Rule:** LLM must return raw JSON without markdown code fences

- **Given:** Claude API call completes

- **When:** Response is parsed

- **Then:** Response does not contain ` `json ` or ` ` ` wrappers

- **Evidence:** Review AIOutputRaw in Inbox Log for markdown wrappers

- **Resolution:** Update Claude prompts to emphasize "raw JSON only, no code blocks"

---

### INV-010: Projects Type Enum

- **ID:** `inv_projects_type_enum`

- **Severity:** Warning

- **Rule:** Projects.Type must be one of {Digital, Physical, Hybrid}

- **Given:** A Projects record is created

- **When:** Type field is set

- **Then:** Type ∈ {"Digital", "Physical", "Hybrid"}

- **Evidence:** Query Projects table for Type values not in enum

- **Resolution:** Use Airtable single-select field type with restricted options

---

## Validation Checklist

**Manual checks (run before each phase completion):**

- [ ] Query Inbox Log for duplicate `(SlackChannel, SlackMessageTS)` keys

- [ ] Verify PRO route captures show Confidence = 1.0

- [ ] Check Filed records have non-empty DestinationName and DestinationURL

- [ ] Validate all Confidence values are in [0.0, 1.0] range

- [ ] Review [Make.com](http://make.com/) modules: clean_text uses replace() on OriginalText

- [ ] Verify router filters use `≥ 0.60` for auto-file threshold

- [ ] Spot-check AIOutputRaw for markdown code fence wrappers

- [ ] Query Projects for Type values outside {Digital, Physical, Hybrid}

**Automated checks (future):**

- SQL queries against Airtable via API

- Contract drift detection (spec.yaml vs actual table schemas)

- Prompt version tracking (compare prompt IDs in spec vs deployed prompts)
