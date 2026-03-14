# CONTRACT (OpenClaw Deployment)

```yaml
---
doc_id: "contract_openclaw_deployment"
contract_version: "1.0.0"
parent_contract: "contract_hub"
last_updated: "2026-03-14"
owner: "Jedidiah Duyf"
created: "2026-02-27"
---
```

**Status:** Active

---

## §1 Purpose & Scope

This contract governs **Magi** — an autonomous agent system running on OpenClaw, operating as the execution layer in a modular, open-stack automation system. It defines the durable rules, invariants, and boundaries for the platform: agent topology, memory architecture, model routing, exec policy, security posture, and infrastructure.

**What this contract governs:**

- Agent topology: roles, delegation patterns, learning loop, skill lifecycle

- Memory architecture: three-memory model, write routing, read patterns

- Model routing: unified gateway, role-to-model assignment framework

- Exec policy: capability-based autonomy, hard gates, write gates

- Security posture: credential storage, access mechanisms, placeholder pattern

- Runtime infrastructure: hardware, update discipline, scaling philosophy

- Messaging channel integration

- Downstream project inheritance

**What this contract does NOT govern:**

- Project-specific deliverables (governed by child contracts: CONTRACT (livingsystems.earth), CONTRACT (LCA Database))

- Brain Stem pipeline architecture (governed by CONTRACT (Brain Stem))

- Documentation mirror system (governed by CONTRACT (Documentation Mirror))

- Workspace-wide governance (governed by CONTRACT (Hub))

**Design principle:** This contract describes the *platform* — the reusable execution capability. Projects that Magi serves are downstream consumers and are governed by their own contracts. Integration surfaces between Magi and sibling systems (Brain Stem, Documentation Mirror) are defined here; internal details of those systems are not.

**Relationship to CONTRACT (Hub):** This contract inherits from and extends CONTRACT (Hub) v1.1.0 within Magi's scope. It may not contradict the Hub CONTRACT. Edit privileges (§5), change control (§6), canonicality (§4), and standing rules (§12) from the Hub apply here unless explicitly specialized.

---

## §2 Architecture: Open Service Stack

### §2.1 Design Principles

Magi operates within a **modular, open-stack architecture**. The system is defined by open interfaces between replaceable services. The stack grows as new services connect; nothing in this contract limits the number or type of services Magi can consume.

**Invariant:** All services connect through **open protocols** — MCP, REST APIs, webhooks, CLI, CDP. No proprietary integrations. If a service requires a closed protocol, that is a defect in the integration, not a trade-off to accept.

**Invariant:** Interface boundaries are the architecture. Providers are configuration. Every service is replaceable at its boundary — the integration point is durable, the provider behind it is not.

**Invariant:** Magi does not write directly to governance documents. Governance lives in Notion and is maintained by the human operator. However, Magi's observations, recommendations, friction reports, and status updates are valued and expected inputs to governance decisions. The messaging channel is Magi's voice in governance.

### §2.2 Service Registry

Each service Magi connects to is registered by role, current provider, interface, and replacement path. This registry is configuration — adding or removing a service does not require a contract change.

| **Role** | **Current Provider** | **Interface** | **Replacement Path** |
| --- | --- | --- | --- |
| Governance | Notion workspace | Human-maintained pages; mirrored to GitHub (Notion-Mirror repo, public read-only) for Magi read access | Any structured doc system with export capability |
| Execution | OpenClaw on Metacarcinus | Local agent runtime with tool-use and exec policy | Any agent runtime supporting tool-use, sub-agents, and exec approvals |
| Orchestration | Make.com | Webhooks, HTTP modules | n8n (migration planned), or any webhook-capable automation platform |
| Shared Memory | Open Brain (Supabase) | REST via Supabase edge functions (bidirectional: search + ingest). Skill-based integration. Contains Brain Stem captures, Magi insights, manual entries. | Any vector store with HTTP API |
| Operational Memory | Magi Brain (Supabase) | REST via Supabase edge functions (bidirectional: search + ingest). Skill-based integration. Magi's dedicated cross-session operational memory. | Any vector store with HTTP API |
| Local Memory | OpenClaw filesystem | Markdown files in agent workspace (MEMORY.md, daily logs). No network dependency. | Any agent-local persistent storage |
| Pipeline Storage | Airtable | REST API (via Make scenarios and direct API). Phase 1: Magi writes gated through Slack approval channel. | Any structured data store with API access |
| Model Routing | OpenRouter | Unified API gateway for all model inference | Any multi-model API gateway |
| Capture | Slack (#magination) | Bidirectional messaging, approval workflows, thread context | Any messaging platform with bot API and thread support |
| Surfacing | Chrome (browser tool) | CDP-based browsing | Any headless browser with CDP support |
| Publishing | GitHub repos (Notion-Mirror public, magis-workshop private); livingsystems.earth (rsync/SFTP) | Git commits; SSH deploy key for magis-workshop; file transfer for site deploys | Any static hosting with CI/CD or file transfer |
| Research | Perplexity API | Direct API tool call via HTTP | Any semantic search / research API |

### §2.3 Magi's Execution Model

Magi operates on a **capability-based model** with broad autonomous execution (see §7 for full policy):

1. **Scheduled work:** Cron-triggered tasks execute autonomously

1. **Commanded work:** Tasks initiated via messaging channel

1. **Free-running work:** Most operations execute without approval gating — mistakes are self-repairable and the cost is tokens, not damage

1. **Hard-gated work:** Production deploys, OpenClaw config changes, credential operations, and Airtable writes (Phase 1) require explicit human approval

1. **Reporting:** All task outcomes reported to messaging channel — Magi never executes silently

**Capability surface:** Magi's capabilities are a function of connected services. The execution model stays constant — the capability surface grows as services connect.

---

## §3 Agent Topology

### §3.1 Design Principles

**Invariant:** Magi IS the thread. There is no separate supervisory agent above Magi. Magi is a single coherent entity that inhabits different model capabilities depending on the work at hand — not a hierarchy of competing agents.

**Invariant:** The agent topology defines **roles**, not models. Each role specifies responsibilities, session type, memory access, delegation authority, and output routing. Which model fills each role is operational configuration (see §5), swappable at the interface boundary. When this contract says "coordinator," it means the role, not a specific model.

**Invariant:** Delegation over escalation. The coordinator delegates *down* to cheaper, more specialized executors. It does not escalate *up* to more expensive models based on runtime judgment. LLMs are unreliable routers — routing decisions must be structural (scheduled, skill-encoded, explicit command), never inferred from model reasoning.

**Invariant:** Sub-agents are stateless workers. They do not accumulate memory. Their results flow back to the coordinator, which decides what is worth writing to memory. The learning loop closes at the coordinator, not at the executor layer.

**Invariant:** Skills are instructions, not actors. A SKILL.md tells an agent when and how to use a tool well — it has no runtime of its own. Tool = the actual API call mechanism. Skill = SKILL.md documenting how to use it. Agent = has model, session, workspace, memory, runs the agent loop. These are three distinct things.

### §3.2 Role Registry

Roles are architecture. Model assignments are configuration tracked in the model capability report (§5.3) and Configuration Decisions page.

| **Role** | **Responsibilities** | **Session Type** | **Memory Access** | **Delegation Authority** | **Output Routing** |
| --- | --- | --- | --- | --- | --- |
| **Strategic Arbiter** | Periodic check-in with Jedidiah. Reviews results, steers direction, updates model capability report, rewrites agent docs and task plans with explicit model assignments. | Isolated cron session | Read: Open Brain, Magi Brain, local memory. Write: both brains, local memory, bootstrap files. | None — produces artifacts, does not delegate. | Artifacts to workspace; summary to #magination. |
| **Operational Coordinator** | Default operational brain. Receives inbound messages, breaks work into tasks, writes clear spawn prompts for executors, reviews executor output, closes the learning loop by writing to appropriate brain. | Persistent main session | Read: Open Brain, Magi Brain, local memory. Write: both brains, local memory. | Spawns sub-agents for volume/specialized work. Delegates to executors, never escalates to arbiter. | Distilled insights to brains; task results to #magination; delegated work to sub-agents. |
| **Codebase / Site Developer** | Broad-context iterative development. Hugo site builds, LCA schema design, long-file edits, application development. | Spawned agent (sub-agent) | Read: local workspace (context passed in spawn prompt, not memory tools). Write: workspace files only. | None. | Results return to coordinator for review. |
| **Volume Executor** | High-volume, well-defined execution. LCA data ingestion, bulk transforms, web research, doc revisions, templated publishing, data classification. The workhorse. | Stateless sub-agent | Read: skills only (context passed in spawn prompt). Write: workspace files only. | May spawn mechanical workers (requires maxSpawnDepth: 2). | Results return to coordinator. Does not write to brains. |
| **Mechanical Worker** | Pattern-matching at volume. Tagging, routing, formatting, anything truly mechanical. | Stateless sub-sub-agent | Read: task prompt only. Write: workspace files only. | None. | Results return to calling executor. |
| **Research** | Semantic search, current events, market signals, domain-specific queries. | Direct API tool call | None (stateless query-response). | None. | Results return to calling agent for synthesis. |
| **Synthesis** | Specific composition tasks where a particular model has comparative advantage. | Direct API tool call | None (stateless query-response). | None. | Results return to calling agent. |

### §3.3 Strategic Arbiter Invocation

**Invariant:** The strategic arbiter is invoked structurally, never by the coordinator's runtime judgment. Three triggers only:

1. **Scheduled cron** — morning check-in (daily, configured time)

1. **Explicit user command** — Jedidiah invokes directly via messaging channel

1. **Phase milestone completion** — triggered when a defined phase boundary is reached

When the coordinator encounters a question that needs strategic input, it makes a structural determination: can other work continue while this waits?

- **Non-blocking:** Write a flag to the daily log ("queued for next arbiter check-in") and continue working. The arbiter picks it up at the next scheduled check-in.

- **Blocking:** Message Jedidiah on Slack immediately with the specific question and what is blocked. The human decides whether to invoke the arbiter now or provide direction directly.

In neither case does the coordinator invoke the strategic arbiter on its own.

### §3.4 Learning Loop

**Invariant:** All Magi memory writes flow through the coordinator. Sub-agents are stateless — they do not write to either brain directly. The coordinator distills insights from executor results and writes to the appropriate brain (see §4.2 for routing rules).

**Loop:** Coordinator delegates → executor produces result → coordinator reviews → coordinator writes durable insights to memory → coordinator reports to messaging channel.

**Skill feedback loop:** Agents execute with skills → coordinator observes results → failures and inefficiencies feed back into skill revisions → strategic arbiter reviews skill effectiveness at check-ins. This is a standing operational loop, not a one-time deliverable.

### §3.5 Skill Lifecycle

Skills are the mechanism by which accumulated knowledge about how to do specific work well gets encoded into reusable, evolvable instructions. The skill lifecycle is a first-class architectural concern.

**Creation:** A skill is created when repeated work reveals a pattern worth codifying. The coordinator identifies the pattern; the skill is written by whichever role is best suited (coordinator for operational skills, developer for technical skills, arbiter for cross-cutting skills). Each skill specifies: trigger conditions, required context, step-by-step instructions, expected output format, and known failure modes.

**Deployment:** Skills are deployed to the appropriate scope — workspace-level for agent-specific skills, shared (`~/.openclaw/skills/`) for skills used across agents.

**Observation:** The coordinator tracks skill effectiveness through executor output quality. Repeated failures or inefficiencies on skill-guided tasks signal a skill quality problem.

**Revision:** Skill revisions follow the same creation process. The coordinator or arbiter identifies what changed (tool behavior, API format, new edge case) and updates the skill. Skill revisions are logged in Magi Brain as operational learning.

**Retirement:** Skills that no longer serve a purpose are moved out of the active skills directory. The retirement decision and rationale are logged.

### §3.6 Hardware Constraints on Topology

Metacarcinus is an M1 Air with 8GB RAM. Each persistent agent session holds context in memory.

**Invariant:** The persistent agent count is conservative. One persistent session (the coordinator) is the baseline. The strategic arbiter runs in isolated cron sessions — it does not hold a persistent session. Sub-agents are spawned and released. Multiple concurrent Sonnet or Opus sessions would contend on this hardware.

**Scaling trigger:** If the coordinator's context window is routinely saturated or sub-agent spawn latency interferes with work, the persistent agent count may increase — but only with a hardware upgrade or migration to more capable infrastructure.

---

## §4 Memory Architecture

### §4.1 Three-Memory Model

**Invariant:** Magi operates with three complementary memory layers. Each has a distinct purpose, access pattern, and trust boundary. No single layer replaces the others.

| **Layer** | **Instance** | **Purpose** | **Writers** | **Readers** | **Persistence** |
| --- | --- | --- | --- | --- | --- |
| Shared semantic memory | Open Brain (Supabase) | Broad-domain, long-timeframe knowledge across the full stack. Human-readable: content written in natural language suitable for retrieval by Jedidiah or any authorized MCP client. Value compounds as more sources write to it over time. | Brain Stem (Make), Magi (coordinator only) | Magi, Claude Desktop/Code, any MCP client | Durable (cloud) |
| Operational semantic memory | Magi Brain (Supabase) | Magi's private operational learning. Machine-optimized: Magi has full agency over notation, compression, and encoding. Only constraint: notation must be transferable to any capable model — write for machine recall, not human readability, but write for *any*machine, not just the current one. | Magi (coordinator only) | Magi only | Durable (cloud) |
| Local filesystem memory | OpenClaw workspace | Session-level and curated long-term state. No network dependency. | Magi (any session with workspace access) | Magi (session-scoped) | Durable (disk) |

**Invariant:** Instance isolation over metadata filtering. Open Brain and Magi Brain are separate Supabase instances with separate credentials. No shared database with RLS filtering; separate projects, separate keys, separate trust boundaries.

**Invariant:** Both brains exist to make accumulated knowledge retrievable via semantic queries. They are search surfaces, not databases. Return on investment is measured in retrieval quality over time, not storage volume.

### §4.2 Write Routing

The coordinator routes memory writes based on audience and content type:

| **Content Type** | **Target** | **metadata.source** |
| --- | --- | --- |
| Decisions made with Jedidiah | Open Brain | `magi` |
| Action items, project insights | Open Brain | `magi` |
| People, events, things worth broad retrieval | Open Brain | `magi` |
| Operational patterns learned (tool behaviors, infrastructure) | Magi Brain | `magi_brain` |
| Cross-session operational context (resolved problems, workarounds) | Magi Brain | `magi_brain` |
| Session-level running notes | Local daily log | N/A |
| Curated durable state (preferences, standing decisions) | Local MEMORY.md | N/A |

**Rule of thumb:** If Jedidiah or another system would benefit from retrieving it → Open Brain. If only Magi would ever need it → Magi Brain. If it is ephemeral session context → local daily log. If it is a curated durable fact → MEMORY.md. Do not duplicate across layers.

### §4.3 Read Patterns

**Session-start context:** Each session begins with two layers of context loading — one automatic, one active.

**Injected by OpenClaw (automatic, no agent action required):** The gateway assembles the system prompt by injecting bootstrap files in order: AGENTS.md, TOOLS.md, SOUL.md, USER.md, HEARTBEAT.md, plus the formatted skills list. These are in context before Magi's first turn.

**Session-start actions (Magi executes on first turn):**

1. Read `memory/YYYY-MM-DD.md` (today + yesterday's operational logs)

1. **Main session only:** Read MEMORY.md (curated long-term state)

1. Query Open Brain for context relevant to this session's topic

1. Query Magi Brain for relevant operational context

This two-layer approach ensures continuity across sessions despite the stateless runtime. The injected bootstrap provides identity and standing instructions; the active steps provide situational memory and accumulated knowledge.

**Both brains must be searched independently** — a search of one does not search the other. They are separate instances.

**Read interface (both brains):** Three tools per brain: `search_thoughts` (semantic query → cosine similarity → ranked results), `recent_thoughts` (time-based + optional source filter), `brain_stats` (counts, breakdowns by source/destination).

### §4.4 Write Interface

**Write interface (both brains):** POST to Supabase Edge Function. Auth: `x-brain-key` header.

- Open Brain: `ingest-thought` endpoint

- Magi Brain: `magi-brain-ingest` endpoint

- Request: `{ "text": "string", "metadata": { "source": "...", ... } }`

- Response: `{ "id": "uuid", "status": "stored" }`

- Processing: validate auth → validate text → generate embedding (OpenAI `text-embedding-3-small`, 1536 dimensions) → INSERT into `thoughts` table → return ID

### §4.5 Memory Hygiene

**Invariant:** Magi selectively stores decisions, action items, and insights to memory during sessions — not casual conversation or troubleshooting chatter. Memory is curated signal, not raw transcript.

**Invariant:** When a session nears auto-compaction, Magi writes durable memories before context is compacted (triggered by OpenClaw's `memoryFlush` mechanism).

**Invariant:** The coordinator reviews and curates MEMORY.md periodically, archiving stale entries and promoting recurring patterns from daily logs to long-term memory.

---

## §5 Model Routing

### §5.1 Unified Gateway

**Invariant:** OpenRouter is the primary unified gateway for model routing. Provider flexibility — the ability to switch models without reconfiguring provider auth — is worth the ~5.5% OpenRouter markup.

**Exception (active):** Direct Anthropic API keys (`ANTHROPIC_API_KEY`) are configured for Sonnet and Opus spawns. OpenClaw currently blocks OpenRouter-routed models in spawned agent sessions; until that block is cleared, sub-agent spawns for Anthropic models must use direct provider keys (CD-029). OpenRouter remains the gateway for all non-spawn routing (coordinator, arbiter, heartbeat, fallback).

**Note:** Model routing is an ongoing active decision area. Assignments, providers, and routing paths evolve as OpenClaw capabilities change, new models ship, and cost/performance data accumulates. The routing table in §5.2 and the Configuration Decisions page are the living record.

### §5.2 Role-to-Model Assignment

**Invariant:** Model selection is role-driven, not provider-driven. The assignment maps roles (§3.2) to models based on demonstrated capability, not brand loyalty. Assignments are operational configuration, not architecture — they change as models improve, new models ship, or testing reveals better matches.

**Current assignment table:**

| **Task** | **Model** | **Rationale** |
| --- | --- | --- |
| Main agent (coordinator) | `google/gemini-3-flash-preview` | Flash default; escalates to Sonnet via spawn |
| Morning brief (strategic arbiter) | `anthropic/claude-sonnet-4.6` | Daily cron default; Opus on-demand only |
| Heartbeat | `google/gemini-2.0-flash-lite` | No change |
| Research and content | `google/gemini-3.1-pro-preview` | Retained for non-spawn research tasks |
| Tool-use-heavy / exec ops | `anthropic/claude-sonnet-4-6` (direct) | Direct Anthropic API; OpenRouter fallback fails in sub-agent sessions (CD-029) |
| Code generation / site development | `anthropic/claude-sonnet-4-6` (direct) | Replaces Gemini Pro; Sonnet 1M context at $3/$15 eliminates Pro advantage (CD-031) |
| Complex architectural decisions | `anthropic/claude-sonnet-4-6` (direct) | Direct Anthropic API (CD-029) |
| Perspective reset / unblocking | `anthropic/claude-opus-4-6` (direct) | On-demand explicit spawn only; direct Anthropic API (CD-029) |

**Assignment updates** are Lane B edits — logged in the Configuration Decisions page, no contract change required.

### §5.3 Model Capability Report

The strategic arbiter maintains a **model capability report** as a standing artifact. This report:

- Tracks demonstrated strengths and weaknesses of each model in Magi's operational context

- Informs role-to-model assignments

- Is updated at arbiter check-ins based on coordinator observations and executor output quality

- Lives in the workspace as a reference document, not in this contract

The report is the input to assignment decisions. Assignments are the output. The arbiter writes both.

### §5.4 Cost Structure

**Invariant:** Cost control is structural, not behavioral. The default model is set by admin config — changing it requires explicit admin action, not runtime inference. The strategic arbiter runs only via structural triggers (§3.3). The coordinator minimizes its own runtime by delegating promptly to volume executors rather than doing work directly.

**Target operating cost:** ~$200/month range. The biggest cost efficiency lever is SKILL.md quality: well-written skills make the volume executor reliable without coordinator overhead, reducing the number of expensive coordinator calls needed to review and correct output.

**Cost is a ratio:** Optimize for value delivered per dollar, not for lowest cost. A $0.40 Sonnet call that saves an hour is cheap. A $0.01 Haiku call that produces garbage requiring Sonnet cleanup is expensive.

---

## §6 Runtime & Infrastructure

### §6.1 Current Configuration

| **Component** | **Current Value** | **Notes** |
| --- | --- | --- |
| Host machine | Metacarcinus (M1 MacBook Air, 8GB/256GB, macOS Sonoma) | Local network at 10.0.0.102 |
| OpenClaw version | v2026.3.2 | Post-update exec settings: `security=full, ask=off` |
| Gateway | Running, loopback 127.0.0.1:18789 | PID active |
| Slack | Connected, #magination (C0AGNFVRKFA). Thread session model: `historyScope: thread`, `inheritParent: false` | Full 21-scope manifest, Socket Mode. Each thread = isolated session key (CD-030). |
| Heartbeat | 2h interval | Model: Gemini 2.0 Flash Lite. Cost-reduction holding pattern. |
| Browser tool | Chrome at `/Applications/Google Chrome.app` | CDP on port 18792 |
| Git repos | Notion-Mirror (public), magis-workshop (private, read/write SSH deploy key) | Plus project-specific repos |
| Remote access | SSH + Screen Sharing from M5 | VNC direct to 10.0.0.102 for GUI |
| Screensaver | Disabled (Flurry) | Root cause of kernel panics |
| Energy Saver | Sleep disabled | Always-on for heartbeat persistence |
| Node.js | v22.22.0 at `/opt/homebrew/opt/node@22/bin/node` | Installed via `brew link node@22` |

### §6.2 Scaling Philosophy

**Invariant:** Hardware is not a constraint on architectural decisions. The M1 Air is a low-risk starting point, not a ceiling. If Magi demonstrates sufficient value, additional resources are available.

**Invariant:** Time-to-capability is prioritized over cost optimization. Getting set up and generating revenue changes the monthly cost calculus.

**Scaling triggers** (any one is sufficient):

- Sustained thermal throttling interferes with task completion

- Multiple projects compete for Magi's execution time

- A commercial engagement requires higher availability

- Persistent agent context contention degrades response quality

**Scaling path:** Metacarcinus → dedicated local server OR cloud VM → managed deployment. Each transition preserves the service architecture and agent topology — only the execution provider changes.

### §6.3 Update Discipline

**Invariant:** OpenClaw updates follow the **pin and wait** discipline:

1. When a new release ships, do not update immediately

1. Wait 3–5 days for community regression reports

1. Check GitHub issues for the target version

1. Test in an isolated session before committing

1. If regressions are found, pin to current stable version

**Post-update checklist:** After any OpenClaw update:

- **Reset exec settings:** `openclaw config set tools.exec.ask off` → `openclaw config set tools.exec.security full` → `openclaw gateway restart`(updates reset these values)

- Verify heartbeat fires on schedule

- Test tool-use with both Sonnet and Gemini through OpenRouter

- Verify brain access mechanism still functions (see §9)

---

## §7 Exec Policy: Capability-Based Model

### §7.1 Design Principle

**Invariant:** Magi operates with broad autonomous execution capability. An agent that must ask permission to write a file cannot build a site. The system is designed to produce substantially more value than the cost of any errors it creates.

**Invariant:** The acceptance of autonomous mistakes is proportional to the value of autonomous work. If Magi is generating thousands of dollars of equivalent work, occasional mistakes that cost tokens to detect and repair are an acceptable trade-off — not a failure of the system.

**Consequence ceiling:** The maximum tolerable blast radius for a single autonomous mistake — including detection and repair — is approximately $100. This is a design constraint evaluated by the human operator, not a spending gate Magi checks before acting. The ceiling is a function of output value, not a standalone budget.

### §7.2 Hard Gates

These operations always require explicit human approval via the messaging channel, regardless of trust level:

| **Operation** | **Rationale** | **Protocol** |
| --- | --- | --- |
| Production deploys (rsync/SFTP to live hosting) | Public-facing, hard to reverse | Dry-run first, post summary to #magination, wait for approval |
| OpenClaw config changes (~/.openclaw/) | A misconfigured agent cannot fix itself | Post proposed change to #magination, wait for approval |
| Credential rotation or provisioning | Security boundary — non-negotiable human oversight | Post request to #magination, wait for approval |
| Airtable writes (Phase 1) | Trust expansion gate — direct writes deferred until approval patterns are established | Post proposed write to dedicated Slack channel, Jedidiah approves/edits/rejects |

### §7.3 Free-Running Operations

All other operations execute without approval gating:

- Shell execution (file reads, writes, builds, scripts)

- Git operations (commit, push, branch, merge)

- Web search and fetch

- Browser automation

- Memory read/write (Open Brain, Magi Brain, local)

- Workspace file management

These operations are self-repairable: a bad commit can be reverted, a broken build can be re-run, a wrong file can be deleted. The cost of a mistake is tokens, not permanent damage.

### §7.4 Airtable Write Gate (Phase 1)

**Invariant (Phase 1):** Any Magi → Airtable write is gated through a dedicated Slack channel where Jedidiah approves (y/n) or edits before the write executes. This channel is queued for setup.

**Protocol:** Magi formats the proposed Airtable write (table, fields, values) → posts to the approval channel → waits for explicit approval → executes on approval → reports result.

**Graduation:** Direct Magi → Airtable writes may move to §7.3 (free-running) in Phase 2, after approval patterns are established and trusted. This is an explicit trust expansion decision logged in Configuration Decisions, not a gradual drift.

### §7.5 Novel Command Discipline

With `tools.exec.ask=off`, OpenClaw does not enforce platform-level approval prompts. Hard gates (§7.2) are enforced by Magi's own behavioral discipline per AGENTS.md, not by the exec approval system.

For genuinely novel or unfamiliar commands, Magi should check in via #magination before first execution — this is expected professional judgment, not a platform gate. The approval surface narrows naturally over time as Magi's operational repertoire grows. This is intentional, not drift.

### §7.6 Tightening the Leash

If the value-to-error ratio degrades, the operator may tighten the approval surface by moving operation categories from §7.3 to §7.2. This is logged in Configuration Decisions. The default posture is broad autonomy; restrictions are the exception, not the starting point.

---

## §8 Messaging Channel

### §8.1 Channel-Agnostic Principle

**Invariant:** Magi's command interface, approvals, and notifications are not locked to any specific messaging platform. The specific channel is a configuration choice, not an architectural decision.

### §8.2 Current Configuration

- **Primary channel:** Slack (LivingSystems.Earth workspace, #magination, channel ID: C0AGNFVRKFA)

- **Airtable approval channel:** TBD (queued for setup — required for §7.4)

- **Status:** Current default, not the permanent choice

### §8.3 Channel Requirements

Any messaging channel used with Magi must support:

- Bidirectional messaging (commands in, reports out)

- Approval workflows (Magi requests approval, human grants/denies)

- Notification delivery with reasonable latency

- Thread or reply context for multi-step operations

---

## §9 Security Posture

**Invariant:** The `<<PLACEHOLDER>>` pattern from CONTRACT (Hub) §11 applies to all Magi configuration. Real secrets are never stored in Notion pages, bootstrap files, or memory systems.

**Invariant:** Brain keys are stored in macOS keychain, never in bootstrap files, environment variable exports, or Notion. The specific mechanism for loading them into the exec environment must be verified against the current OpenClaw version after every update.

### §9.1 Credential Registry

| **Credential** | **Storage** | **Access Mechanism** | **Notes** |
| --- | --- | --- | --- |
| OpenRouter API key | OpenClaw local config on Metacarcinus | Loaded by OpenClaw gateway at startup | Never in Notion |
| SSH keys for GitHub | `~/.ssh` on Metacarcinus | SSH agent | Never in Notion |
| magis-workshop deploy key | `id_ed25519_github` on Metacarcinus | SSH, scoped to magis-workshop-repo only (read/write) | Never in Notion |
| WHC hosting credentials | Locally on Metacarcinus | Used by deploy scripts | Never in Notion |
| Open Brain API key (`OPEN_BRAIN_KEY`) | macOS keychain on Metacarcinus | Passed as `x-brain-key` header to Supabase edge functions | Verify access mechanism post-update (see §9.2) |
| Magi Brain API key (`MAGI_BRAIN_KEY`) | macOS keychain on Metacarcinus | Passed as `x-brain-key` header to Supabase edge functions | Verify access mechanism post-update (see §9.2) |
| Messaging channel tokens | Managed by OpenClaw channel integration | Loaded by OpenClaw | Never in Notion |

### §9.2 Brain Key Access Discipline

Brain keys are loaded from macOS keychain into the exec environment. The access mechanism has historically required `/bin/zsh -c '...'` wrapper subshells because `~/.zshenv` loads keychain values and the base exec environment does not source it.

**Post-update verification:** After every OpenClaw update, verify:

1. Whether `~/.zshenv` is still sourced in the current exec environment

1. Whether brain keys are accessible in the base exec environment or still require zsh subshell wrapping

1. Update AGENTS.md curl templates to match the verified mechanism

This verification is part of the post-update checklist (§6.3) and the result is logged in Configuration Decisions.

---

## §10 Brain Stem Integration Surface

This section defines how Magi relates to the Brain Stem pipeline (governed by CONTRACT (Brain Stem)). It does not govern Brain Stem's internals.

### §10.1 Data Flow: Brain Stem → Open Brain → Magi

Brain Stem writes classified content to Open Brain on every successful capture (fire-and-forget POST to `ingest-thought`). This content includes:

- Extracted fields from People, Projects, Ideas, Admin, and Events captures

- Metadata: source (`brain_stem` or `brain_stem_fix`), destination, confidence score, classified name, record ID

Magi consumes this data by querying Open Brain at session start and on-demand during work. The data is already in Open Brain when Magi reads it — there is no direct Brain Stem → Magi channel.

### §10.2 Airtable as Shared Data Surface

Brain Stem writes to Airtable via Make. Magi reads Airtable for pipeline data. Magi writes to Airtable only through the Phase 1 approval gate (§7.4).

### §10.3 Actionable Capture Handoffs

When a Brain Stem capture should trigger Magi execution (e.g., a project idea that should become a task tree, a research request that should trigger enrichment), the handoff protocol is defined in the Brain Stem Integration Spec (companion document to this contract). This contract establishes the constraint: handoffs must respect the Airtable write gate and the messaging channel as the coordination surface.

---

## §11 Downstream Projects

Magi serves as the execution platform for project-specific work. Each project that uses Magi:

- Has its own contract governing project-specific decisions

- References this contract for platform-level rules

- Inherits all platform invariants (agent topology, memory architecture, exec policy, security posture, model routing)

- May not contradict this contract; if a project need conflicts with a platform rule, the conflict is escalated and resolved here

**Current downstream projects:**

- **livingsystems.earth** — Hugo static site + LCA Database feature. Governed by CONTRACT (livingsystems.earth) v0.2.0 and CONTRACT (LCA Database) v0.1.0. Both subordinate to this contract.

- **Brain Stem integration** — capture pipeline data consumption. Integration surface defined in §10.

**Downstream contract relationship:** The livingsystems.earth CONTRACT lists `parent_contract: "contract_openclaw_deployment"`. This contract is that parent. Platform-level rules (exec policy, security, model routing, memory architecture, agent topology) apply to all downstream projects without restating them. Downstream contracts specialize within their scope — they do not redefine platform behavior.

---

## §12 Primary Design Values

These values govern architectural trade-offs for the OpenClaw deployment. They are ordered by priority when values conflict:

1. **Automatability and efficiency first.** Prefer solutions that reduce manual intervention and increase autonomous capability. Manual steps during bootstrap should be automated as soon as practical.

1. **Portability for future migrations.** Every architectural choice should allow clean migration. Vendor lock-in at any layer is a defect to be logged and addressed.

1. **Time-to-capability over cost optimization.** Speed of deployment and getting operational is more valuable than marginal cost savings. Revenue generation changes the cost calculus.

1. **Investment scales with demonstrated value.** Start minimal and low-risk. As Magi proves its value through delivered projects, invest proportionally.

---

## §13 Change Control

### §13.1 Version Bump Rules

- **Patch (0.0.x):** Configuration updates (assignment table, current values), clarifications

- **Minor (0.x.0):** New sections, new standing rules, new capability boundaries

- **Major (x.0.0):** Architectural changes to agent topology, memory model, or service architecture; changes to invariants

### §13.2 Change Tracking

This contract is its own source of truth for change history. The `contract_version` in the YAML header tracks the current version. Notion's page version history provides the full diff timeline. Significant deviations are logged in §14.

### §13.3 Downstream Reconciliation

Per CONTRACT (Hub) §6, when this contract is updated, downstream documents in the impact radius must be reconciled in the same work session or carry a staleness banner: `⚠️ STALE — see [version]`.

**Impact radius:** CONTRACT ([livingsystems.earth](http://livingsystems.earth/)), CONTRACT (LCA Database), [AGENTS.md](http://agents.md/), [SOUL.md](http://soul.md/), [USER.md](http://user.md/), [TOOLS.md](http://tools.md/), [HEARTBEAT.md](http://heartbeat.md/), Configuration Decisions.

---

## §14 Deviation Log

| **Version** | **Date** | **Description** |
| --- | --- | --- |
| 0.1.0 | 2026-02-27 | Initial draft. Codifies three-actor architecture, OpenRouter unified gateway, channel-agnostic messaging, exec approval tiers, scaling philosophy, and design values. |
| 0.2.0 | 2026-03-03 | §2 rewritten: open service stack replacing three-actor model. Service registry pattern. Magi's governance input valued. |
| 0.2.1 | 2026-03-03 | Two-repo publishing model. SSH deploy key access. |
| 0.2.2 | 2026-03-04 | Open Brain integration. REST interface, skill-based integration, session-start search. |
| 0.3.0 | 2026-03-07 | Capability-based exec model replacing tiered approvals. Broad autonomous execution. Proportionality principle. |
| 0.4.0 | 2026-03-07 | Magi Brain as second memory instance. Session-start ritual. Post-update exec settings discipline. Brain key access hardening. |
| 1.0.0 | 2026-03-11 | Major rewrite. Agent topology codified as first-class architecture (§3): role registry, delegation pattern, learning loop, skill lifecycle, strategic arbiter invocation rules. Three-memory model promoted to platform invariant (§4) with write routing, read patterns, and hygiene rules. Model routing restructured (§5): roles are architecture, model assignments are configuration, model capability report as standing artifact. Brain Stem integration surface defined (§10). Airtable write gate codified as Phase 1 invariant (§7.4). Hardware constraints on agent topology acknowledged (§3.6). All prior deviation log entries preserved. |
| 1.0.0 | 2026-03-12 | Deployment complete (Session C). Post-deployment model routing revisions: Flash promoted to coordinator default (Sonnet cost $0.27 for a [MEMORY.md](http://memory.md/) update); Sonnet promoted to daily arbiter default (Opus morning brief cost $0.75); Opus demoted to on-demand only. Node.js v22.22.0 installed. Brain access confirmed as MCP wrapper pattern for search, direct REST for writes. Exec settings verified surviving gateway restart. Security posture reviewed — cleartext OPEN_BRAIN_KEY removed from ~/.openclaw/.env. |

---

## §15 Related Documents

- [CONTRACT (Hub)](https://www.notion.so/CONTRACT-Hub-c18af9cbec3b4c388c3561036a4871f1) — parent contract

- [CONTRACT (Brain Stem)](https://www.notion.so/CONTRACT-Brain-Stem-cb5393105c784cc3969571a898b4f81e) — sibling: capture pipeline

- [CONTRACT (Documentation Mirror)](https://www.notion.so/CONTRACT-Documentation-Mirror-9f062b4d8d134901a8c896a7c233dc33) — sibling: mirror system

- [CONTRACT (livingsystems.earth)](https://www.notion.so/CONTRACT-livingsystems-earth-35560bdc09cf4e78bdf4ea9466ea9f91) — child: site project

- [CONTRACT (LCA Database)](https://www.notion.so/CONTRACT-LCA-Database-0042bf99ca59458b80e1725b0b381ec5) — grandchild: LCA feature module

- [Configuration Decisions](https://www.notion.so/Configuration-Decisions-a5354158620348de908d5ffb31e35036) — operational decision log

- Brain Stem Integration Spec v1.0.0 — data flows, triggers, query patterns, Airtable write gate protocol

- Agent Roster & Model Assignment v1.0.0 — agent registry, skill inventory, configuration requirements

---

**End of CONTRACT (OpenClaw Deployment) v1.0.0**
