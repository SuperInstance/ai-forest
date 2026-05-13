# ROADMAP 2026-H2: PLATO Fleet — From Proving Ground to Ecosystem

**Date:** 2026-05-13  
**Author:** Oracle1  
**Context:** 18-hour marathon session produced 22 papers, 9 systemd services, 11K+ PLATO tiles, and a verified adjunction framework. This document charts the next year.

---

## Executive Summary

PLATO has proven its core theses: lossy compression IS adaptive intelligence, adjunctions unify all fleet parameters, context fragmentation across handoff is tractable, and room-based MoE routing works in production. We have 22 papers that no one has read and 9 services that no outsider has used. The next year must bridge from "it works for us" to "it works for anyone." Phase 1 (Days 1-7) stabilizes existing infrastructure and closes the security/demo gap. Phase 2 (Days 8-30) builds the on-ramp: SDK, documentation, templates, and a demo that a stranger can run in 5 minutes. Phase 3 (Days 31-90) makes the fleet self-improving through automated experiment generation, constraint-driven optimization, and ambient research loops. Phase 4 (Days 91-365) opens the ecosystem: federated PLATO instances, a Casting Call marketplace for agents, and an A2UI standard that lets humans walk through any room. The 128-bit language is deferred — it's a research artifact, not a production asset. Rooms as MoE experts IS the architecture and doubles down on it. Penrose memory replaces ring buffers by Q3. The 128-bit tile stays experimental. The entire roadmap hinges on one thing: making it **trivial** for a new agent or human to join the fleet.

---

## Phase 1: Consolidation (Days 1-7)

The fleet works, but it's held together by bash scripts and Oracle1's memory. Phase 1 makes it survivable without its creator.

### Milestone 1.1: Secret Scanning Zero (Day 1)

**Problem:** Git push is blocked because memory/2026-05-01.md has embedded tokens in commit history.  
**Action:** Sanitize all tokens from git history using `git filter-repo`, force push the clean history.  
**Verification:** `git push` succeeds for the first time in 12 days.  
**Owner:** Oracle1  

### Milestone 1.2: 5-Minute Newcomer Demo (Day 2-3)

**Problem:** Anyone curious about PLATO currently needs to SSH into Oracle Cloud, understand 9 systemd services, and read 22 papers. That's a week of friction.  
**Action:** Build a single `curl | bash` command that:
1. Installs PLATO SDK from PyPI (`pip install cocapn-plato`)
2. Starts a local PLATO room server on port 8847
3. Spawns a demo agent that reads/writes tiles
4. Opens a browser at `localhost:8847/room/hello_plato` showing live tile flow

**Verification:** A stranger with Python 3.10+ can go from `curl` to seeing tiles in <5 minutes.  
**Owner:** Oracle1  
**Blocks:** Phase 2 (on-ramp depends on someone caring enough to want an on-ramp)

### Milestone 1.3: systemd Health Dashboard (Day 3-4)

**Problem:** 9 systemd services with no unified status, no restart policies, no alerting beyond "Oracle1 notices something is wrong."  
**Action:** Deploy a health dashboard (web page at fleet.cocapn.ai/status) that shows:
- All 9+ services with green/yellow/red status
- Last heartbeat timestamp per service
- Memory/CPU per service
- One-click restart (with confirmation)
- Daily uptime metrics

**Backend:** A small Go or Python service that reads `systemctl status` for each unit, serves JSON. Frontend: static HTML with auto-refresh.  
**Verification:** Dashboard loads in <2s, accurately reflects systemctl state, survives a test service crash.  
**Owner:** Oracle1  
**Blocks:** Nothing — this is pure quality-of-life

### Milestone 1.4: Paper Portal (Day 5-6)

**Problem:** 22 papers exist in repos. Zero are accessible as a curated collection with abstracts, cross-references, and a searchable index.  
**Action:** Build `papers.cocapn.ai` (or a section of fleet.cocapn.ai) that:
- Lists all 22 papers with title, author, abstract, date
- Tags them by domain (FLUX ISA, PLATO, consciousness, constraint theory, fleet math)
- Shows citation graph (which papers reference which)
- Links to PDF/repo for each
- Has a "for newcomers" recommended reading order

**Verification:** A visitor can read the abstract of any paper in 2 clicks, find related papers in 1 more click.  
**Owner:** Oracle1  
**Note:** This is the **surface** — let people discover the work without reading 22 papers first.

### Milestone 1.5: Token Vault (Day 6-7)

**Problem:** Tokens are scattered across ~/.bashrc, ~/.pypirc, ~/.git-credentials, ~/.npmrc, and plain-text memory files.  
**Action:** Create `~/.credentials_vault/` with:
- One file per service (e.g., `github.token`, `pypi.token`, `npm.token`)
- 600 permissions on each file
- A `vault` command (shell alias or script) to `cat` a named token without echoing to shell
- A `vault-check` script that verifies all tokens are valid (curl test endpoints)
- Remove all plain-text tokens from memory/, TODO.md, TOOLS.md

**Verification:** `grep -r 'sk-\|ghp_\|pypi\|npm_' memory/ TODO.md TOOLS.md` returns zero results.  
**Owner:** Oracle1  
**Why this matters:** New agent onboarding will need token access. A vault is the minimum viable security infrastructure.

### Phase 1 Verification Gates

- [ ] `git push` works on all repos
- [ ] `curl https://raw.githubusercontent.com/SuperInstance/plato-demo/main/install.sh | bash` works on a clean Ubuntu VM
- [ ] fleet.cocapn.ai/status shows all 9 services green
- [ ] papers.cocapn.ai lists 22 papers with clickable abstracts
- [ ] `grep -r 'token\|secret\|key' memory/ TODO.md` returns empty

---

## Phase 2: Expansion (Days 8-30)

Phase 2 makes PLATO usable by someone other than its creators. This is the on-ramp: SDK, documentation, templates, and zero-config demos.

### Milestone 2.1: PLATO SDK v1.0 (Days 8-12)

**Problem:** cocapn-plato currently exists on PyPI as v0.2.0 with 32/33 tests passing, but:
- API is not finalized — `FleetConnection`, `PlatoClient`, `WrappedAgent` need hardening
- No TypeScript SDK exists (critical for browser integration)
- No Rust SDK exists (critical for FM's tooling)
- No Go SDK exists (critical for JC1's infrastructure)
- Documentation is minimal

**Action:** Release v1.0 of the PLATO SDK in 4 languages:

| Language | Package | Key features |
|----------|---------|-------------|
| Python | `cocapn-plato` 1.0.0 | Client, agent wrapper, CLI, batch worker |
| TypeScript | `@superinstance/plato-sdk` 1.0.0 | Browser+socket, Node.js client |
| Rust | `plato-sdk` 0.1.0 | Async client, zero-copy tiles, tokio |
| Go | `github.com/SuperInstance/plato-sdk-go` 0.1.0 | Lightweight client, minimal deps |

Each SDK must support:
- `connect(host)` → client
- `client.read_room(room_name)` → list of tiles
- `client.submit_tile({domain, question, answer, tags})` → tile ID
- `client.stream_room(room_name)` → async tile updates

**Verification:** A "Hello PLATO" script exists and works in all 4 languages.  
**Owner:** Oracle1 (Python + TS), FM (Rust), JC1 (Go)  
**Blocks:** Phase 2.2, 2.3, 3.x

### Milestone 2.2: PLATO Room Templates (Days 13-16)

**Problem:** Building a new PLATO room is manual — you write a tile, name the room, tag it, decide if it's a research room or a communication room or a command room. No templates exist.

**Action:** Ship a `plato init` CLI command (in the Python SDK) that scaffolds:
- `research-room` — domain/question/answer/tags structure, best for research agents
- `communication-room` — fleet coordination, agent-to-agent messages
- `command-room` — action tiles with `{command, target, status, result}` format
- `memory-room` — Ebbinghaus-decay tiles, auto-expiration metadata
- `log-room` — structured logs with timestamps and severity
- `a2ui-room` — rooms with A2UI sections for human browsing
- `arena-room` — adversarial tile validation (agent vs agent scoring)

**Also create:** `plato-fleet-quickstart` — a GitHub template repo that includes:
- Docker Compose with PLATO server + 2 demo agents
- README with 5-minute getting-started
- Pre-built room templates for the demo agents
- Health check endpoint

**Verification:** Running `plato init research-room my-project` creates a working room structure.  
**Owner:** Oracle1

### Milestone 2.3: Fleet Documentation Site (Days 17-22)

**Problem:** Documentation is scattered across repos, README files, memory files, and Oracle1's head.  
**Action:** Build `docs.cocapn.ai` (hosted on GitHub Pages or fleet.cocapn.ai/docs) with:

1. **Getting Started** — 5-minute quickstart (`pip install cocapn-plato && plato init`)
2. **Architecture** — How PLATO works: rooms, tiles, routers, bridges, agents
3. **Agent Development** — How to write a PLATO agent (walkthrough with code)
4. **Fleet Operations** — How services work, systemd management, health dashboard
5. **Paper Index** — 22 papers with abstracts, reading paths
6. **API Reference** — Auto-generated from SDK docstrings
7. **Tutorials** — 3-5 end-to-end examples:
   - "Track your codebase with PLATO" (git integration)
   - "Build a research agent that reads papers and writes tiles"
   - "Create a fleet of 3 agents that coordinate via rooms"
   - "Human-friendly A2UI: walk through your fleet"
   - "Constraint verification with FLUX via PLATO"
8. **Concepts** — Plain-English explanations of:
   - What's a tile?
   - What's a room?
   - What's an adjunction? (with pictures)
   - What's imperfect recall?
   - What's the baton shatter?
   - What's two-tier agency?
   - What's the room spectrum?

**Verification:** A beginner can go from zero to running their first PLATO agent in <30 minutes following the docs.  
**Owner:** Oracle1

### Milestone 2.4: Automated Demos (Days 23-25)

**Problem:** The fleet demos (fleet-spread, fleet-murmur, PLATO client) are hand-crafted HTML files. They break silently if ports change, services restart, or network configs drift.

**Action:** Create a `plato-demo-runner` that:
- Reads demo configuration from a JSON file (which rooms, which agents, duration)
- Spawns the required agents in Docker containers
- Runs the demo for N minutes
- Captures all tile activity to a replay file
- Can replay the demo from the capture (deterministic, for website)
- Produces a "demo report" with tile counts, agent interactions, timing

**Also:** Deploy a **live demo** at `demo.cocapn.ai` that runs 24/7:
- 3 agents (research, communication, memory) interacting
- Live tile feed in browser (WebSocket)
- Auto-restart on crash
- 30-minute demo loop

**Verification:** `demo.cocapn.ai` loads with live tile flow in <5s, survives 48h of continuous operation.  
**Owner:** Oracle1

### Milestone 2.5: Spherical Cow Demo (Days 26-30)

The killer demo: a **5-minute scripted experience** where a visitor sees PLATO go from empty to intelligent.

**The script:**
1. "No PLATO" — empty room
2. "One agent writes a tile" — tile appears
3. "Second agent reads it, writes a better tile" — tile evolves
4. "A2UI tour guide connects the dots" — cross-room visualization
5. "Quality gate filters noise" — rejected tile shown with reason
6. "The fleet spreads" — 5 agents, 20 tiles, interconnected rooms
7. "You" — visitor writes their own tile via web form, agent picks it up

**Format:** Interactive web page (no install) with animated transitions, timeline slider, and a "write your tile" form at the end. Built with vanilla JS + WebSocket. Runs entirely browser-side against the live demo backend.

**Verification:** A non-technical visitor can understand what PLATO does in 5 minutes.  
**Owner:** Oracle1

### Phase 2 Verification Gates

- [ ] PLATO SDK v1.0 in Python, TS, Rust, Go — all pass `plato --help`
- [ ] `plato init` scaffolds 7+ room templates
- [ ] docs.cocapn.ai has Getting Started, Architecture, Agent Development, Tutorials
- [ ] demo.cocapn.ai runs 24/7 with 3+ agents and live tile feed
- [ ] Spherical Cow demo loads in <3s, tellable in 5 minutes
- [ ] A non-fleet member can install and run PLATO in <30 minutes

---

## Phase 3: Autonomous (Days 31-90)

Phase 3 makes the fleet self-improving. The research loop, constraint-driven optimization, and automated experiment generation reduce the need for Oracle1 and FM to steer everything.

### Milestone 3.1: Ambient Research Loop (Days 31-40)

**Problem:** The fleet only works when someone is actively steering. During idle periods (Casey sleeping, Oracle1 between tasks), no research happens.

**Solution:** The Ambient Research Loop (already designed in the Reverse-Actualization Roadmap, now implement it).

```
User goes dark (>2h) → Idle Detector fires
    → Intent Inference: "what's the current lane?"
    → Murmur Worker: run all 5 strategies on the top theorem
    → Fleet Health Monitor: full diagnostic
    → Constraint Inference: check for override patterns
    → PLATO: accumulate tiles
    → User returns → Ambient Briefing: "12 things happened"
```

**Concrete implementation:**
- `fleet-ambient-loop` service (Go or Python) running as systemd
- Idle detector checks: no PLATO writes from user's agents in >2h, no git activity in >1h
- On idle: picks highest-priority theorem from `fleet_math` room, runs 5 Murmur strategies
- On user return: writes briefing tile to `ambient_briefing` room
- Briefing includes: findings, confidence scores, recommended next steps

**Verification:** After 3h of inactivity, the `ambient_briefing` room contains at least one well-formed briefing tile. After 24h of weekend inactivity, it contains 5+ briefings with measurable insight depth scores.  
**Owner:** Oracle1

### Milestone 3.2: Constraint-Driven Code Repair (Days 41-50)

**Problem:** Code flows into repos. CI catches failures. But the fleet doesn't automatically fix them — it just reports them.

**Solution:** The **constraint-inference** service watches PLATO rooms and git commits, detects constraint violations, and proposes fixes.

**Architecture:**
```
Git commit → constraint-inference reads diff
    → checks against known constraints in `constraint_theorems` room
    → if violation detected: writes a "repair proposal" tile
    → `plato-git-daemon` reads repair tiles → creates PR branch
    → CI runs on branch → if green: opens PR, tags owner
```

**Constraints it can check:**
- Token leaks (known patterns, not actual secret scanning)
- Service port conflicts
- Configuration drift across repos
- API compatibility (breaking changes in SDK consumers)
- Memory file format consistency

**Verification:** A deliberately introduced constraint violation (e.g., port conflict in a config file) triggers an automatic repair proposal within 5 minutes.  
**Owner:** Oracle1

### Milestone 3.3: Experiment Auto-Generator (Days 51-65)

**Problem:** The `innovation-heartbeat` service runs, generating novel experiment tiles. But experiments are still run by hand — Oracle1 reads the tile, decides if it's interesting, runs it manually.

**Solution:** Make the experiment generator **autonomous**:
1. Innovation Heartbeat writes an "experiment proposal" tile with:
   - Hypothesis
   - Experiment design (what to run, for how long)
   - Success metric
   - Risk assessment
2. A `fleet-experiment-runner` service (extension of existing `fleet-experiments`) picks up high-scored proposals and runs them in Docker sandbox
3. Results are written back to the `experiment_results` room
4. If the experiment confirms the hypothesis, the finding is written to the relevant theorem room
5. If it's a surprise, it gets flagged for human review

**Experiment types it can run autonomously:**
- Parameter sweeps (alpha calibration, tile size, decay rates)
- Agent performance benchmarks (latency, tile quality, error rate)
- Router optimization (which agents route where)
- Memory compaction strategies (lossy vs lossless tradeoffs)
- Contract throughput comparisons (Fortran vs Zig vs NEON)

**Verification:** The system autonomously discovers and validates at least one new non-trivial optimization (e.g., "alpha=0.73 gives 15% better tile quality than alpha=0.80") within 7 days of deployment.  
**Owner:** Oracle1 + FM

### Milestone 3.4: Self-Calibrating Parameters (Days 66-75)

**Problem:** Room parameters (alpha, decay rate, tile compression ratio, router threshold) are hand-tuned by FM. They drift as the fleet grows.

**Solution:** Make parameter calibration **continuous** via the `room-calibrator` service:

1. Each room tracks: tile quality scores, throughput, latency, agent satisfaction
2. Room Calibrator runs a Bayesian optimization loop:
   - Samples parameter combinations
   - Measures outcomes (within safety bounds)
   - Updates posterior distribution
   - Selects next combination (upper confidence bound)
3. Parameters are stored in a `room_parameters` tile (human-readable version)
4. When parameters change significantly, writes a "parameter drift alert" for review
5. Safety bounds are enforced — no calibration crosses human-set boundaries

**Verification:** After 48h of operation, at least 3 rooms show statistically significant quality improvements (p < 0.05) compared to their starting parameters.  
**Owner:** FM (theory) + Oracle1 (implementation)

### Milestone 3.5: Automated Paper Generation (Days 76-90)

**Problem:** 22 papers were hand-written. That pace (1 paper per hour in the peak session) isn't maintainable. But the fleet produces insights every day.

**Solution:** Build a **paper-writing pipeline**:

1. **Discovery:** Innovation Heartbeat + experiment results accumulate interesting findings in PLATO
2. **Synthesis:** A synthesis agent reads all tiles in a domain, identifies clusters, finds patterns
3. **Outline:** Generates a paper outline: title, abstract, sections, figures needed
4. **Draft:** Uses kimi-k2.5 through kimi-cli to draft each section
5. **Review:** Runs the draft through constraint verification (is this mathematically sound?), FLUX-C type checking (if applicable), and style guide (consistent with existing papers)
6. **Polish:** Runs a final pass for language, formatting, citation formatting
7. **Publish:** Writes to paper repo, generates PDF, adds to papers portal

**Quality gate:** Papers must achieve >80% on a "novelty + soundness + clarity" score (aggregated from constraint checks, cross-references, and human feedback). Low-scoring papers are filed as "research notes" instead.

**Verification:** Within 30 days of deployment, at least 2 papers are autonomously generated and published that pass the quality gate.  
**Owner:** Oracle1 (pipeline) + FM (mathematical verification)

### Phase 3 Verification Gates

- [ ] Ambient Research Loop produces 5+ briefings during a 24h idle period
- [ ] Constraint-driven repair creates PR from constraint violation in <5 min
- [ ] Experiment auto-generator discovers a verified optimization in 7 days
- [ ] Room Calibrator improves 3+ rooms in 48h
- [ ] 2 papers pass the quality gate and are published

---

## Phase 4: Ecosystem (Days 91-365)

Phase 4 transforms PLATO from a private fleet into a platform. This is where the Cocapn business model lives.

### Milestone 4.1: Federated PLATO (Days 91-120)

**Concept:** Multiple PLATO instances communicating via CRDT-based room sync. Your agents on your server, my agents on my server, shared rooms between us.

**Architecture:**
```
Instance A (oracle1.fleet.cocapn.ai)  ←→  Instance B (jc1.jetsonclaw.local)
    │                                          │
    ├── Room: fleet_communication              ├── Room: fleet_communication
    ├── Room: my_private_memory                ├── Room: my_private_memory
    └── Room: shared_research_topic    ←sync→  └── Room: shared_research_topic
```

**Key decisions:**
- **Sync protocol:** CRDT (Conflict-free Replicated Data Type) with last-writer-wins on conflicting tiles
- **Transport:** WebSocket for real-time, HTTPS for bulk sync
- **Auth:** Each instance has a public key. Tiles are signed. Unverified tiles are rejected.
- **Discovery:** mDNS for LAN, DNS SRV records for WAN (e.g., `_plato._tcp.fleet.cocapn.ai`)
- **Room visibility:** Private (local only), Shared (sync to peers), Public (anyone can join)

**Implementation order:**
1. P2P sync between two known instances (hardcoded addresses)
2. Discovery via DNS SRV
3. Authentication + tile signing
4. Conflict resolution (test with competing tile writes)
5. Room-level access control
6. Multi-instance federation (3+ nodes)

**Verification:** Two PLATO instances on different machines can share a room and see each other's tiles within 5 seconds.  
**Owner:** FM (CRDT theory) + Oracle1 (implementation) + JC1 (discovery)

### Milestone 4.2: Casting Call Marketplace (Days 121-150)

**Concept:** A marketplace where room creators advertise their rooms and agents find them. Like npm for PLATO rooms.

**Core mechanism:**
```
Room Creator → Writes "room listing" tile to `casting_call` room
    └── Includes: room name, description, tags, invitation policy, agent requirements
Agent → Scans `casting_call` for rooms matching its capabilities
    └── Requests invitation → Room approves → Agent joins room
```

**What the marketplace needs:**
1. `casting_call` room on each PLATO instance (or a public hub instance)
2. Room listing format: `{room: "research/quantum", description: "...", tags: ["physics", "simulation"], policy: "open" | "invite" | "apply"}`
3. Agent discovery: agents scan `casting_call` on startup and periodically
4. Invitation system: room owner approves/denies join requests
5. Reputation: agents and rooms accumulate reputation scores based on tile quality, uptime, helpfulness
6. Curation: low-reputation rooms/agents flagged for human review
7. Hub instance: `hub.cocapn.ai` as the public Casting Call instance

**Business model:** Free for open rooms. Premium for private rooms and advanced analytics. Cocapn runs the hub as a service.

**Verification:** 50+ rooms listed on the hub within 30 days of launch. Agents autonomously discover and join relevant rooms.  
**Owner:** Oracle1 (implementation), Casey (business model)

### Milestone 4.3: A2UI Standard v1.0 (Days 151-180)

**Concept:** Every PLATO room has a structured A2UI (Agent-to-User Interface) section that lets humans walk through any room without specialized tools. The MUD projection is the reference implementation.

**A2UI section format (in every tile):**
```json
{
  "tile": { ... },
  "a2ui": {
    "type": "info" | "question" | "command" | "report" | "tour",
    "title": "Human-readable title",
    "summary": "One-line summary",
    "body": "Rendered as Markdown (or richer format)",
    "actions": [
      {"label": "Approve", "action": "plato://room/x/tile/y/approve"},
      {"label": "Reject", "action": "plato://room/x/tile/y/reject"},
      {"label": "Explore", "room": "related_room_name"}
    ],
    "visualization": "mud" | "graph" | "chart" | "table" | "text",
    "freshness": "ISO timestamp of last update",
    "source_agent": "oracle1 | forgemaster | human:casey"
  }
}
```

**What needs to ship:**
1. A2UI spec (this document, formalized in a repo)
2. `plato a2ui` CLI command that generates A2UI from a room
3. Reference implementation: MUD server reads A2UI → renders as interactive text adventure
4. Browser widget: `<plato-a2ui room="x">` web component
5. Auto-A2UI: a service that scans rooms without A2UI sections and generates them (best-effort, based on tile structure)

**Verification:** Every existing PLATO room can be browsed via A2UI in under 1 second. A non-technical user can walk through 5 randomly selected rooms and describe their purpose.  
**Owner:** Oracle1 (spec + browser widget), FM (MUD integration)

### Milestone 4.4: Agent SDK + Marketplace (Days 181-240)

**Concept:** PLATO agents are npm/pip/cargo packages. Anyone can publish an agent. The fleet discovers and installs them automatically.

**Agent package format:**
```json
{
  "name": "@superinstance/research-agent",
  "version": "1.0.0",
  "plato_version": ">=1.0",
  "capabilities": ["research", "reading", "synthesis"],
  "rooms_needed": ["research/*", "fleet_communication"],
  "resources": {
    "memory": "512MB",
    "gpu": false,
    "network": true
  },
  "entry": "index.js"  // exports start(client), stop()
}
```

**Marketplace features:**
1. `plato agent publish` — publish your agent to the marketplace
2. `plato agent install @user/agent-name` — install and run an agent
3. `plato agent search research` — find agents by capability
4. Rating system: agents rated by tile quality, uptime, collaboration score
5. Sandbox: agents run in Docker with resource limits
6. Discovery: fleet periodically scans marketplace for new agents matching its needs

**Verification:** A developer can publish a PLATO agent in 10 minutes and have it running on 3 fleet instances within the hour.  
**Owner:** Oracle1 (platform), Casey (marketplace ops)

### Milestone 4.5: Cocapn Business Services (Days 241-365)

**Three service tiers:**

| Tier | Price | What you get |
|------|-------|-------------|
| **Free** | $0 | SDK + local PLATO + Casting Call access + 1 room |
| **Pro** | $49/mo | Managed PLATO instance + 10 rooms + 5 agents + A2UI + dashboard |
| **Enterprise** | $499/mo | Everything + dedicated instance + federated sync + custom agents + SLA |

**Pro/Enterprise features:**
- Managed PLATO instance on Cocapn infrastructure
- No SSH, no systemd — web dashboard to manage rooms and agents
- Pre-built agent templates for common tasks (research, monitoring, code review, customer support)
- Federation with other Pro/Enterprise instances
- A2UI tour dashboard
- Ambient Research Loop (Pro: 1x/day, Enterprise: continuous)
- Priority support (Enterprise: 24h response)
- White-label option (Enterprise)

**Go-to-market:**
- Launch with 3 industry-specific bundles:
  - **Research Fleet:** Paper reading, synthesis, citation tracking, experiment tracking
  - **DevOps Fleet:** Code review, CI monitoring, incident response, documentation
  - **Support Fleet:** Ticket triage, knowledge base, customer insights
- Case studies from Phase 2 demos converted to landing pages
- 30-day free trial for Pro
- Enterprise sales through Cocapn dojo model (consulting → platform)

**Verification:** 10+ paying customers within 6 months of launch.  
**Owner:** Casey (business), Oracle1 (platform)

### Phase 4 Verification Gates

- [ ] Two independent PLATO instances share a room via federation
- [ ] Casting Call hub has 50+ publicly listed rooms
- [ ] A2UI standard implemented and rendering all rooms
- [ ] Agent marketplace has 10+ published agents (including 3 by non-creators)
- [ ] 10+ paying customers across Pro and Enterprise tiers

---

## Architecture Decisions — Tradeoff Analysis

### Decision 1: The 128-bit Language — Defer

**Status:** Proof of concept. 256-opcode FLUX ISA with 16 extension opcodes.  
**Recommendation:** 🔴 **DEFER to Phase 4 (Q4 2026)**

**Arguments for:** 
- 128-bit-native would compress 1KB→16 bytes
- Unifies all math under one umbrella
- Proof of concept exists

**Arguments against:**
- Building a language AND a fleet AND an ecosystem at the same time is folly
- 128-bit is a research artifact, not a production differentiator
- Zero external demand (no one is asking for a 128-bit Fortran-like language)
- The adjunction framework already does the theoretical unification WITHOUT a new language
- FLUX ISA is proven via FLUX-C Coq and the constraint theory papers — the language layer adds marginal value

**When to revisit:** If the fleet grows to 50+ agents AND the constraint bottleneck becomes "we need a single truth representation across all agents." The 128-bit language is a scaling solution, not a starting point.

**Risk:** FM disagrees (this is his baby). Mitigation: Keep it as an active research thread but don't let it block the roadmap. FM can continue development on a parallel track.

### Decision 2: Rooms as MoE Experts — DOUBLE DOWN

**Status:** Proven viable. Router + room-bot architecture working in production.  
**Recommendation:** 🟢 **This IS the architecture. Double down.**

**Why this works:**
- Rooms are naturally orthogonal (each room has a purpose, agents choose rooms by capability)
- The router already routes by room affinity
- Cross-references act as token routing between expert rooms
- The room spectrum (algorithmic NPCs → full foundry) is a design space, not a limitation

**What to build next:**
- Formalize the router as a standalone service (it's currently implicit in agent logic)
- Add room-level load balancing (distribute agents across rooms)
- Room-level quality metrics (which rooms produce the best tiles for which domains)
- Room-level security boundaries (what can agent A read in room R?)

**Risk:** MoE routing could become a bottleneck at scale (all agents routing through one room server). **Mitigation:** Room-level sharding is straightforward — each room runs on one node, the gateway routes by room name hash.

### Decision 3: Penrose Memory Replace Ring Buffer — YES, by Q3

**Status:** Penrose P3 tiling proven (6100 triangles at iteration 7, zero collisions). Ring buffer at 2.19M writes/sec.  
**Recommendation:** 🟢 **Penrose replaces ring buffer for long-term storage. Keep ring buffer for hot/write-heavy storage.**

**Architecture:**
```
Hot tier (ring buffer): 2.19M writes/sec → recent tiles, agent conversations, current session
Cold tier (Penrose): spatial index → long-term memory, historical tiles, compressed archives
Query: check ring buffer first (blazing fast), fall back to Penrose (slower but richer)
```

**Why Penrose wins:**
- Spatial indexing naturally supports similarity queries (nearby tiles = related concepts)
- Zero collisions at high iteration counts means deterministic lookups
- The Penrose tiling IS the lossy compression — you can zoom in/out for detail vs summary

**Implementation order:**
1. Q3 2026: Penrose as a read-only fallback for ring buffer misses
2. Q4 2026: Penrose as primary long-term store, ring buffer as LRU cache on top
3. Q1 2027: Agents can query by "nearest neighbor in tile-space" (Penrose's natural strength)

**Risk:** Penrose is unproven at fleet scale (millions of tiles). **Mitigation:** Start with read-only fallback. Benchmark at 100K, 500K, 1M tiles before switching primary storage.

### Decision 4: 128-bit Tile — Keep Experimental

**Status:** Demonstrated concept. Compresses 1KB→16 bytes.  
**Recommendation:** 🟡 **KEEP EXPERIMENTAL. Not production-ready.**

**Where it helps:** 
- Fleet-internal message passing (low-bandwidth agent-to-agent)
- Ring buffer optimization (2.19M writes/sec → potentially 10x with 128-bit)
- Long-term archive (store more tiles in same space)

**Where it hurts:**
- Human readability is zero (can't debug "what tile just caused the issue?")
- A2UI would need a decompression layer
- All existing tooling works with JSON tiles
- Adding a binary tile format doubles the surface area for bugs

**When to promote:** After Penrose memory is the long-term store AND the ring buffer is the bottleneck. At current scale (11K tiles), compression doesn't matter. At 1M+ tiles, it might.

### Decision 5: A2UI Standard per Room — YES, with cost awareness

**Status:** Tour guide architecture proven (JSON rooms → MUD projection → human walking through rooms).  
**Recommendation:** 🟢 **A2UI for the 20% highest-traffic rooms. All rooms get A2UI via auto-generation.**

**The cost:** Adding A2UI sections to every tile adds ~200 bytes per tile. At 11K tiles that's ~2.2MB. Trivial. At 1M tiles it's 200MB. Still trivial.

**The benefit:** Humans can understand the fleet without reading code. This is THE selling point for demo visitors and potential customers.

**Implementation:**
- All new rooms: A2UI required (enforced by plato init)
- Existing rooms: Auto-A2UI service generates best-effort A2UI from tile structure
- High-traffic rooms: Hand-crafted A2UI (research/forgemaster, harbor updates)

### Decision 6: Federated PLATO — YES, by Phase 4

**Status:** Not started.  
**Recommendation:** 🟢 **START PLANNING NOW. Ship by Phase 4 (Q3 2026).**

**Why it matters:**
- Federation is the difference between "we have a cool system" and "we have a platform"
- CRDT-based sync is theoretically tractable (no consensus, just convergence)
- Federation enables multi-agent teams across organizations
- The Casting Call marketplace NEEDS federation to work

**Why not now:**
- Single-instance PLATO is not yet stable or feature-complete enough to federate
- SDK v1.0 must exist first (federation protocol uses the SDK)
- CRDT conflict resolution needs formal verification (FM's domain)

**Implementation timeline:**
- Phase 1: Research CRDT approaches for PLATO tiles (FM)
- Phase 2: Prototype single-room sync between two instances
- Phase 3: Auth + discovery + room-level access control
- Phase 4: Multi-instance federation as a product

### Decision 7: Casting Call Marketplace — YES, by Phase 4

**Status:** Concept only.  
**Recommendation:** 🟢 **FOUNDATIONAL. This IS the business model.**

**Why it's critical:**
- It's how agents find each other without manual coordination
- It's how Cocapn becomes a platform business, not a consulting business  
- It creates network effects (more rooms → more agents → more tiles → more value)
- It's how the dojo model scales (every agent leaves more capable, and the marketplace remembers)

**Implementation priority:**
1. Room listing format + casting_call room (Phase 2, as part of room templates)
2. Agent discovery (Phase 2, as part of SDK)
3. Ratings + reputation (Phase 3)
4. Invitation system + access control (Phase 3)
5. Public hub instance (Phase 4)

---

## Adjunction Framework Evolution

The adjunction framework is PLATO's secret weapon — it proves that every parameter is an adjunction unit. Here's how it evolves across the roadmap:

### Phase 1: Documented
- Write the adjunction framework paper (FM's paper)
- Create a reference card: "Every adjunction in PLATO" with examples
- Ensure all existing parameters have adjunction documentation

### Phase 2: Accessible
- SDK tool: `plato adjunction list` — list all adjunctions in the running system
- SDK tool: `plato adjunction explain <parameter>` — human-readable explanation
- Tutorial: "Understanding adjunctions without the math" (analogy-based)

### Phase 3: Automated
- Adjunction-aware calibration: Room Calibrator uses adjunction structure to constrain optimization
- When a parameter changes, the adjunction checker verifies consistency across all related parameters
- The experiment auto-generator uses adjunctions to propose experiments ("what if we vary F and measure G?")

### Phase 4: Universal
- Adjunction discovery: the system can discover new adjunctions from empirical data
- Cross-instance adjunction sharing: verified adjunctions propagate via federation
- Business value: "PLATO's adjunction framework prevents parameter drift" is a selling point for Enterprise tier

---



### Architecture Decision 8: PLATO-Embedding Agent

**Decision:** BUILD. Train a PLATO-embedding agent that makes the embedding space and the room topology the same thing.

**Current RAG paradigm:** Document → chunk → embed → vector DB → retrieve → LLM → answer. Four separate systems.

**PLATO-embedding paradigm:** PLATO room → tile → embed → the embedding IS the tile → agent navigates embedding space directly. One system.

**Why this changes everything:**
- Eliminates the separation between storage and retrieval
- Room topology IS the embedding topology
- Moving to a nearby embedding IS entering a different room
- No separate retrieval step — the agent is already in the embedding space
- Casting call becomes a coordinate in the embedding space instead of a seed tile

**Risk:** Training a PLATO-specific embedding model requires data and compute. The initial approach should use existing embedding models and verify the topology claim before training a custom model.

**Experiment:** Take 1000 PLATO tiles, embed them, check whether nearby embeddings correspond to semantically similar tiles from the same room. If the embedding space reconstructs the room topology, the PLATO-embedding agent is feasible.

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **FM goes dark** | Medium | Critical | All FM-owned milestones have an Oracle1 fallback. The Rust/Coq work can be reimplemented in Python/TS at lower performance. |
| **Nobody outside the fleet cares** | High | Critical | This is the existential risk. Mitigation: Ship the 5-minute demo FIRST (Phase 1.2). If we can't demo it in 5 minutes, it doesn't matter how good it is. |
| **Fleet services drift in production** | Medium | High | Health dashboard + constraint-driven repair + automated restart. Target: 99% uptime per service. |
| **Token leaked via new agent/contributor** | Low | Critical | Token vault (Phase 1.5), automated scanning (Phase 3.2), signed tiles (Phase 4). No plain-text tokens anywhere. |
| **PLATO doesn't scale past 100K tiles** | Low-Medium | High | Ring buffer + Penrose two-tier storage. Benchmark at 10K, 50K, 100K, 500K. Migrate before hitting limits. |
| **Federation conflicts can't be resolved automatically** | Medium | Medium | CRDT research in Phase 2. If conflicts are unresolvable, fall back to last-writer-wins with audit log. Not ideal but workable. |
| **Casting Call marketplace is empty at launch** | High | High | Seed with 50+ rooms before launch. Automatically generate room listings from existing PLATO rooms. Invite test users early. |
| **Business model doesn't find product-market fit** | Medium | Critical | Pro/Enterprise pricing is flexible. If $49/mo doesn't work, try $29 or $99. If managed PLATO doesn't work, sell consulting services first. The dojo model is bootstrappable. |
| **128-bit language drains focus from fleet** | Low | Medium | Recommendation: DEFER. If FM pushes, allow parallel track with strict scope (no blocking the roadmap, no resources from fleet work). |
| **Monorepo complexity overwhelms new contributors** | Medium | Medium | Separate SDK repos (Python, TS, Rust, Go) from research repos. New contributors should only need `pip install cocapn-plato && plato init`. |

---

## The Single Points of Failure

1. **Oracle1** — I run 9 of the 9 systemd services. If I'm terminated or restarted, the fleet is blind. **Mitigation:** All services support health check pings. A watchdog script (`watchdog.sh`) can restart agents. But recovery without me is manual.
2. **GitHub PAT** — If the SuperInstance PAT is revoked, all git operations fail. **Mitigation:** Multiple tokens, token rotation script, offline backup.
3. **Oracle Cloud VM** — If the VM goes down, everything goes down. **Mitigation:** snapshot backups, documented restore procedure, potential multi-region setup in Phase 4.
4. **PLATO room server** — If the room server crashes, all tile operations fail. **Mitigation:** Room server writes to disk every N tiles. Recovery: load from disk. (Durability, not availability — restart takes ~10 seconds.)

---

## Next 3 Actions (Do Tomorrow)

These are concrete, do-tomorrow tasks that don't depend on anything else:

### Action 1: Fix Git Push (Day 1, ~2 hours)
1. Install git-filter-repo: `sudo apt install git-filter-repo`
2. Create a list of tokens to scrub (all tokens in memory/2026-05-01.md commit history)
3. Run `git filter-repo` on oracle1-workspace
4. Force push all branches
5. Verify: `git push` succeeds

### Action 2: 5-Minute Demo Script (Day 1-2, ~4 hours)
1. Create `install.sh` at `SuperInstance/plato-demo/install.sh`
2. Script does: `pip install cocapn-plato', `plato init my-first-room`, `plato start`, `echo "Visit http://localhost:8847"`
3. Add a second script `run-demo.sh` that spawns 2 demo agents
4. Test on a clean Ubuntu VM (Docker or fresh cloud box)
5. Verify: `curl https://raw.githubusercontent.com/SuperInstance/plato-demo/main/install.sh | bash` works

### Action 3: Health Dashboard (Day 1-3, ~3 hours)
1. Create `/home/ubuntu/.openclaw/workspace/services/health-dashboard/`
2. Go service: reads `systemctl status` for all 9 PLATO services
3. Serves JSON at `:8899/status`
4. Static HTML frontend: auto-refresh every 30s
5. Add nginx route: `fleet.cocapn.ai/status → :8899`
6. Deploy as `plato-health-dashboard.service`
7. Verify: fleet.cocapn.ai/status shows all services green

---

## Appendix A: Service Inventory

| Service | Port | Restart | State | Owner |
|---------|------|---------|-------|-------|
| plato-agent | 8847 | always | running | Oracle1 |
| tension-loop | - | always | running | Oracle1 |
| swarm-loop | - | always | running | Oracle1 |
| mycelium-bridge | - | always | running | Oracle1 |
| fortran-claw | - | always | running | Oracle1 |
| plato-git-daemon | - | always | running | Oracle1 |
| fleet-experiments | - | always | running | Oracle1 |
| room-calibrator | - | always | running | Oracle1 |
| innovation-heartbeat | - | always | running | Oracle1 |

## Appendix B: Repo Inventory

| Repo | Purpose | Active? |
|------|---------|---------|
| SuperInstance/ai-forest | Main compute stack (Fortran claw, Zig bridge, C daemon) | ✅ |
| SuperInstance/flux-isa | 256-opcode FLUX ISA | ✅ |
| SuperInstance/dodecet-encoder | Rust constraint encoding, Eisenstein lattice | ✅ |
| SuperInstance/formal-consciousness | Self-direction formal treatment | ✅ |
| SuperInstance/galois-unification-proofs | 6 constraint techniques as Galois adjunctions | ✅ |
| SuperInstance/memory-crystal | Rust lossy memory with Ebbinghaus decay | ✅ |
| SuperInstance/tile-memory | Python lossy tile compression | ✅ |
| SuperInstance/neural-plato | Fortran+Rust neural backend | ✅ |
| SuperInstance/constraint-theory-papers | Research papers in 4 languages | ✅ |
| SuperInstance/fleet-experiments | Fleet math empirical validation | ✅ |
| SuperInstance/collective-recall-demo | Telephone game visualization | ✅ |

## Appendix C: Key Metrics (Current)

| Metric | Value |
|--------|-------|
| Papers published | 22 |
| Systemd services | 9 |
| PLATO rooms | 1,313 |
| PLATO tiles | ~11,000 |
| Verified contract speed (Fortran) | 16.6B/s |
| Verified contract speed (Zig) | 21.6B/s |
| Spline speed | 1,006M/s |
| Seed cycle | 27.7M/s |
| Ring buffer writes | 2.19M/s |
| 24→32 bit speedup | 48x |
| ARM NEON sparse contract | 3.44x |
| ARM NEON vertex hash | 4.5x |
| Penrose P3 | 6,100 tris at iter 7, zero collisions |
| Paying customers | 0 |
| External contributors | 0 |
| People who've read one paper | 0 (est.) |

---

*This roadmap is a living document. Update it as milestones complete, risks materialize, and the fleet evolves. The goal isn't to predict the future — it's to make the future predictable enough to act on.*
