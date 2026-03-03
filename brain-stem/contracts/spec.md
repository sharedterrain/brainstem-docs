# contracts/spec (Brain Stem)

**Machine-readable specification for Brain Stem**

This is the automation anchor. Markdown [CONTRACT.md](http://contract.md/) is human-readable; this spec is machine-parseable.

---

## spec.yaml

```yaml
project: "brainstem"
contract_version: "0.2.0"

# Functional pipeline → current provider mapping (see CONTRACT §3)
providers:
  capture: { current: "slack", interface: "capture_interface" }
  orchestration: { current: "make.com", interface: "scenario_runner" }
  intelligence: { current: "claude", interface: "classification_interface" }  # also covers extraction_interface
  research: { current: "perplexity", interface: "enrichment_interface" }
  storage: { current: "airtable", interface: "storage_interface" }
  publishing: { current: "TBD", interface: "publishing_interface" }

routes:
  - name: "PRO"
    prefix: "PRO:"
    destination: "Projects"
    confidence: 1.0
    llm_mode: "extract_only"
    implementation: "implemented"
    prompt_id: "projects_extract_v1"
    
  - name: "BD"
    prefix: "BD:"
    destination: "TBD"
    llm_mode: "classify_and_extract"
    implementation: "implemented"
    prompt_id: "brain_dump_classifier_v1"
    
  - name: "CAL"
    prefix: "CAL:"
    destination: "Events"
    llm_mode: "extract_only"
    implementation: "scaffolded"
    prompt_id: "events_extract_v1"
    
  - name: "R"
    prefix: "R:"
    destination: "Research"
    llm_mode: "extract_only"
    implementation: "scaffolded"
    prompt_id: "research_extract_v1"
    
  - name: "fix"
    prefix: "fix:"
    destination: "NeedsReview"
    llm_mode: "none"
    implementation: "scaffolded"

thresholds:
  auto_file_confidence_min: 0.60

data_contracts:
  tables:
    InboxLog:
      required_fields:
        - OriginalText
        - FiledTo
        - Confidence
        - Status
        - SlackChannel
        - SlackMessageTS
        - CapturedAt
      optional_fields:
        - SlackThreadTS
        - DestinationName
        - DestinationURL
        - AIOutputRaw
        - ErrorDetails
        
    Projects:
      required_fields:
        - Name
        - Type
        - Status
        - NextAction
        - LastTouched
        - Tags
      optional_fields:
        - Notes
        
    People:
      required_fields:
        - Name
        - LastTouched
      optional_fields:
        - Context
        - FollowUps
        - Tags
        
    Ideas:
      required_fields:
        - Name
        - LastTouched
      optional_fields:
        - OneLiner
        - Notes
        - Tags
        
    Admin:
      required_fields:
        - Name
        - Status
        - Created
      optional_fields:
        - DueDate
        - Notes
        
    Events:
      required_fields:
        - Name
        - Created
      optional_fields:
        - EventType
        - Notes

llm_contracts:
  prompts:
    - id: "projects_extract_v1"
      route: "PRO"
      model: "claude-3-5-haiku-20241022"
      temperature: 0
      max_tokens: 500
      input_fields: ["clean_text"]
      output_schema_ref: "schemas.projects_extract_v1"
      
    - id: "brain_dump_classifier_v1"
      route: "BD"
      model: "claude-3-5-sonnet-20241022"
      temperature: 0.3
      max_tokens: 500
      input_fields: ["clean_text"]
      output_schema_ref: "schemas.brain_dump_classifier_v1"

schemas:
  projects_extract_v1:
    type: object
    required: ["name", "type", "status", "next_action", "notes", "tags", "reason"]
    properties:
      name: { type: ["string", "null"] }
      type: { type: ["string", "null"], enum: ["digital", "physical", "hybrid", null] }
      status: { type: ["string", "null"], enum: ["active", "waiting", "blocked", "someday", "done", null] }
      next_action: { type: ["string", "null"] }
      notes: { type: ["string", "null"] }
      tags: { type: "array", items: { type: "string" } }
      reason: { type: "string" }
      
  brain_dump_classifier_v1:
    type: object
    required: ["destination", "confidence", "data", "reason"]
    properties:
      destination: { type: "string", enum: ["people", "projects", "ideas", "admin", "events", "needs_review"] }
      confidence: { type: "number", minimum: 0.0, maximum: 1.0 }
      data:
        type: object
        properties:
          name: { type: "string" }
          context: { type: ["string", "null"] }
          follow_ups: { type: ["string", "null"] }
          status: { type: ["string", "null"] }
          next_action: { type: ["string", "null"] }
          notes: { type: ["string", "null"] }
          one_liner: { type: ["string", "null"] }
          due_date: { type: ["string", "null"], pattern: "^\\d{4}-\\d{2}-\\d{2}$" }
          tags: { type: "array", items: { type: "string" } }
          project_type: { type: ["string", "null"], enum: ["digital", "physical", "hybrid", null] }
      reason: { type: "string" }

invariants:
  - id: "inv_inboxlog_singleton"
    severity: "critical"
    description: "Every capture yields exactly one Inbox Log record"
    
  - id: "inv_pro_confidence"
    severity: "warning"
    description: "PRO route must set confidence to 1.0"
    
  - id: "inv_filed_has_destination"
    severity: "critical"
    description: "Inbox Log with Status=Filed must have DestinationName and DestinationURL"
    
  - id: "inv_confidence_range"
    severity: "critical"
    description: "Confidence must be between 0.0 and 1.0"
    
  - id: "inv_original_text_immutable"
    severity: "critical"
    description: "OriginalText in Inbox Log must never be modified after creation"

change_control:
  last_change_id: "MOD-005"
  contract_version: "0.2.0"
  change_log_source: "Change Management DB"
```
