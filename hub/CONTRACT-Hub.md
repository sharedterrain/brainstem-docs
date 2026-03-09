# CONTRACT (Hub)

```yaml
---
doc_id: "contract_hub"
contract_version: "1.1.0"
status: "active"
last_updated: "2026-02-27"
owner: "Jedidiah Duyf"
created: "2026-02-22"
---
```

---

## §1 Purpose & Scope

This document is the **highest-authority governance artifact** in the workspace. It defines the binding rules, invariants, and boundaries that govern all workspace activity.

**Scope:** All Hub-level governance, all project-level contracts, and all actors (human, Notion AI, external models, automation) operating within this workspace.

**What belongs here:** Durable rules that any actor must follow. If a line could become stale due to tool changes, model updates, or shifting priorities, it does not belong here — it belongs in the Hub Steering Document.

**What does not belong here:** Current state, tool routing, navigation pointers, session history, open questions, or any content that describes *what is true right now* rather than *what must be true always*.

---

## §2 Hierarchy Invariant

**Invariant:** The authority chain for this workspace is:

1. **CONTRACT (Hub)** — workspace-wide rules (this document)

1. **Project CONTRACTs** (e.g., [CONTRACT (Brain Stem)](https://www.notion.so/cb5393105c784cc3969571a898b4f81e)) — project-scoped rules

1. **All other documents** — steering docs, phase docs, architecture pages, protocols, instruction sets

**Conflict resolution:** When any downstream document contradicts a higher-level contract, the contract wins. The downstream document must be reconciled to match the contract, not the reverse.

**Project override:** Project CONTRACTs may specialize or extend rules from this document within their project scope. They may not contradict this document. If a project CONTRACT and this document conflict, this document wins.

**Actor obligation:** Any actor (human, AI model, automation) editing a workspace artifact must defer to the applicable contract. When in doubt, read the relevant contract before editing.

**Downstream reconciliation:** When this contract is updated, all downstream documents in the impact radius must be reconciled in the same work session. If a downstream document cannot be updated in the same session, it must carry a staleness banner: `⚠️ STALE — see [Change ID]`.

---

## §3 Architecture: Three-Tier + Cross-Cutting

### Tier 1: Hub-Level (Global Coordination)

- CONTRACT (Hub) (this document) — binding rules, invariants, boundaries

- Hub Steering Document — operational state, tool routing, decisions log, session history

- Tool Instruction Sets — project-focused model instruction sets (model × project)

- Framework Working Agreements — cross-project rules validated through friction

- Architecture Principles — operational patterns; candidate status until promoted

### Tier 2: Project-Level (Operational Reality)

- Project CONTRACTs — authoritative project-scoped definitions, mirrored to GitHub for enforcement

- Project Steering Documents — implementation state, decisions, session history per project

### Tier 3: Cross-Cutting Databases (System Memory)

- Friction DB — operational pain points, feeds promotion pipeline

- Parking Lot — cross-project task routing

- Workspace Index — structural map of entire workspace

- ~~Change Management DB~~ — deprecated; change history now tracked in each document's own deviation log and Notion page version history

- Sessions DB — queryable historical memory (planned)

**Design principle:** Shallow context (always loaded) = relevant CONTRACT + relevant Steering doc. Deep context (on-demand) = DBs and full history.

---

## §4 Canonicality & Ownership Boundaries

**Invariant:** Each artifact type has **ONE** canonical source. Edits flow toward canonical; mirrors/caches/exports flow away.

**Invariant:** **No duplicate canon.** If two artifacts claim to be canonical for the same thing, it is a defect — log a friction entry and resolve.

**Mirror boundary:** Git mirrors are **read-only snapshots of promoted governance**. They do not become canonical by virtue of being mirrored.

### Canonicality Table

| **Artifact Type** | **Canonical Source** | **Read-Only Mirrors** | **Enforcement** |
| --- | --- | --- | --- |
| Operational decisions, prompts, steering docs | Notion | — | Human review + provenance |
| Structured pipeline records (runs, entities) | Airtable | Notion dashboard views | Schema validation |
| Promoted governance (contracts, CI checks) | GitHub | Notion pointers/links | CI checks, branch protection |
| Raw operational telemetry (frictions, sessions) | Notion DBs | — | Schema + required fields |

**Promotion Pipeline:** Notion (raw/draft) → validation → Git (stable/enforced) → never flows backward.

**Write Boundary Rule:** No tool may write to a non-canonical source except via explicit sync/mirror operation with provenance.

---

## §5 Edit Privileges & Approval Policy

### Lane A — Free Write (No Approval Required)

Agents may write directly (high volume, low risk).

**Allowed operations:**

- Create new rows: Sessions DB, Friction DB, Parking Lot

- Update status fields: mirror status, blocked, needs review

- Update timestamps: last updated, first seen, last seen

- Append session entries to Session History sections

**Provenance required:** actor (model name), timestamp, session ID if applicable.

### Lane B — Bounded Write (Section-Fenced)

Agents may edit specific sections/fields only (medium risk).

**Rule:** Any edit outside allowed sections is Lane C (proposal).

**Steering Documents (Hub + Project):**

- Allowed sections: Implementation State, Active Frictions, Next Session Priorities, Session History (append-only)

- Prohibited sections: Pointers, Tool Routing, Global Decisions, Ruled Out

- Requirements: link evidence (FR-IDs, commit SHAs, verified timestamps). Use `<<UNKNOWN>>` for unverifiable claims.

**Tool Instruction Sets:**

- Allowed sections: Known Frictions (link FR-IDs), Recommended Patterns (cite evidence)

- Prohibited sections: Purpose, Capabilities, Edit Privileges

**Database fields:**

- Friction DB: all fields except "Promoted?" and "Promoted To" (human approval)

- Parking Lot: all fields except status changes from "triaged" → "complete"

### Lane C — Propose-First (Human Approval)

Agents draft proposals; humans approve/merge (high risk).

**Artifacts requiring proposal workflow:**

- **All CONTRACT documents** (Hub and Project)

- Working Agreements (Promoted section)

- Publishing rules, security rules, repo boundary rules

- Changes to "Ruled Out" or "Global Decisions"

- Promotion of frictions from candidates → promoted

**Mechanisms:**

- Proposed Changes section in doc, OR

- GitHub PR with justification, OR

- Parking Lot entry tagged "needs review" with proposal text

**Approval cadence:** daily 10-min review OR end-of-session batch OR immediate for publishing safety.

### Lane D — Automated Enforcement (No Manual Approval)

System gates enforce correctness.

**Enforcement mechanisms:**

- GitHub CI: secret scanning, publish-scope validation, schema checks

- Notion DB validation: required fields, FR-ID format, promotion thresholds

- Make scenario contracts: typed inputs/outputs, idempotency checks

**Rule:** If automated gate fails, escalate to Lane C with diagnostic.

**Safety escalation:** secrets, identity exposure, publish scope → immediate human review + immediate promoted rule/CI check.

---

## §6 Change Control Protocol

**Version bumps:**

- **Patch** (x.x.+1): Typo fixes, formatting, clarifications with no semantic change

- **Minor** (x.+1.0): New sections, new decisions, content additions that don't break existing references

- **Major** (+1.0.0): Structural renumbering, section removals, changes that break existing cross-references

**Change tracking:** Each governance document is its own source of truth for change history. The `contract_version` in the YAML header tracks the current version. Notion's page version history provides the full diff timeline. Significant deviations and decisions are logged in each document's own deviation log or change log section.

**Downstream reconciliation:** When a governance document is updated, downstream documents in the impact radius must be reconciled in the same work session. If reconciliation cannot happen in the same session, downstream documents must carry a staleness banner: `⚠️ STALE — see [version]`.

**Applies to:** CONTRACT (Hub), all project CONTRACTs, Hub Steering Document, Architecture Principles, Dependency Registry, and any future governance documents.

---

## §7 Working Style (Workspace Default)

- **One action at a time:** Each step must include:
    - *What/why (1 line)*
    - *Expected outcome (1 line)*

- **Evidence-first:** No claims of completion without a log/screenshot/link to a concrete artifact.

- **No invented state:** Use `<<UNKNOWN>>` when something is unverified.

- **Pacing:** Wait for "done" (or proof) before proceeding to next step.

- **No paste traps:** If including terminal commands, output **commands only** (no commentary mixed into the command block).

- **Governance lanes (summary):** See §5 for full definitions.
    - Lane A = raw records (free write)
    - Lane B = bounded updates in fenced sections
    - Lane C = propose-first (review required)
    - Lane D = automated gates

Projects may override these defaults in their own steering docs, but must explicitly note deviations.

---

## §8 Prompt Authorship Guidelines

**Goal:** Prompts should be tool-effective and context-appropriate, without importing governance language unless required.

**Rules:**

1. **Keep Working Style out of prompts by default.** Do not embed pacing, lanes, or step-gating unless the prompt is for an agent executing multi-step work or the target tool benefits from strict gating.

1. **Match the prompt to the target surface.**
    - Notion AI prompts: emphasize document edits, sections, and constraints.
    - Claude Code prompts: include step gating, command-only blocks, and proofs.
    - ChatGPT prompts: allow reasoning and synthesis; include constraints only when needed.

1. **Separate "create content" from "log problems".** Only create friction entries when explicitly requested or when a blocker prevents completion.

1. **Use a "Prompt Mode" header when ambiguity is likely:**
    - `Prompt Mode: EXECUTION` (strict steps, proofs, gating)
    - `Prompt Mode: AUTHORING` (write/edit content only, minimal process)
    - `Prompt Mode: DIAGNOSTIC` (investigate, report, do not edit)

1. **Default to minimal constraints.** Include only constraints necessary to get the tool to do the job safely and correctly.

---

## §9 Table Interchange Protocol

**Rule:** Any table that must be **agent-parseable** must include a `CANONICAL_TABLE_CSV` block adjacent to the human table.

- The **CSV block is the parse source of truth** for automation and agents.

- The human table (Notion/Markdown) is the **readable view**.

- If they disagree: **CSV wins** and a friction entry must be logged.

**CSV constraints:** header row required; no multi-line cells; quote cells containing commas; keep cells short; use `;` inside a cell for lists.

---

## §10 Document Size & Compaction Rules

**Problem:** Without limits, steering docs grow unbounded and defeat shallow-context design.

**Size limits:**

- Hub Steering Document: <500 lines

- Project Steering Documents: <400 lines

- Tool Instruction Sets: <300 lines each

- CONTRACTs: no hard limit, but every line must be a rule — bloat signals misplaced operational content

**Compaction ritual (monthly or phase boundaries):**

- Older session detail (>90 days or previous phase) collapses into durable decisions + links to Sessions DB

- Resolved frictions move from Active Frictions to archived view; keep FR-ID only

- Hot vs Cold:
    - Hot: current priorities, active decisions, active frictions, last 3 sessions
    - Cold: full session narratives, resolved frictions, superseded decisions (move to DBs)

- Archive pattern: snapshot at phase boundaries; restart with hot content only

---

## §11 Cross-Project Dependencies

**Rule:** All cross-project dependencies are tracked in the [Dependency Registry](https://www.notion.so/abb5799fc94548c4a0ea87e45fe82267).

**What to track:** Dependencies where a change in one artifact can break execution or invalidate governance. See Architecture Principles §3 for full policy.

**Do not duplicate** dependency entries in CONTRACTs or steering docs. This section is the rule; the registry is the data.

---

## §12 Standing Rules

Binding decisions extracted from the Global Decisions log and promoted to permanent rules.

**SR-1: Mirror posture.** The Git mirror is a **thin, curated publishing lane** for CI enforcement, immutable history, and public showcase. It is not an operational dependency or critical path. *(Origin: Decision 7, 2026-02-11)*

**SR-2: Promotion boundary.** If a friction's fix benefits any project using the same tool stack, promote to mirror-framework. If specific to one project's data model or routing logic, promote to that project's repo. *(Origin: Decision 8, 2026-02-11)*

**SR-3: Model check-in cadence.** Perform regular "state + constraints" check-ins with the active model after any scope shift, before dependent actions, and whenever tool/economics assumptions might change. No fixed turn-count rules. *(Origin: Decision 9, 2026-02-11)*

**SR-4: Structural standard.** Hub governance documents adopt the v0.2.0 structural standard: YAML headers, §-numbered sections, Change Control Protocol, HOT/COLD boundary, and deviation logs for significant changes. *(Origin: Decision 12, 2026-02-18)*

**SR-5: Notion AI as admin layer.** Notion AI is the reliable admin layer for workspace governance — architecture, synthesis, governance editing, and execution. External models provide specialist input; Notion AI parses and incorporates results directly. No multi-model handoff choreography required. *(Origin: Decision 13, 2026-02-19)*

**SR-6: Tool Instruction Sets are project-scoped.** Each instruction set is scoped to a model × project pair (e.g., Claude — Brain Stem). No standardized external-model output format — Notion AI parses any reasonable input. *(Origin: Decision 14, 2026-02-19)*

---

**End of CONTRACT (Hub) v1.1.0**
