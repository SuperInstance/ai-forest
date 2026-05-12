# Paper 6: The Roadmap Ahead — Convergence, Competition, and the Self-Improving Fleet

**Authors:** The SuperInstance Fleet
**Date:** 2026-05-12
**Status:** Vision / Strategy

## Abstract

The SuperInstance fleet has converged from two independent research streams — Oracle1's PLATO-room ecology and Forgemaster's constraint-theory mathematics — into a unified architecture for agent-human shared reality. This paper describes the roadmap ahead: the bridges we will build, the competitions we will run, and the path to a fleet that improves itself through use. We identify three phases: Consolidation (current), Expansion (next 30 days), and Autonomous Improvement (next 90 days). Each phase has concrete milestones, measurable outcomes, and clear success criteria.

## 1. Where We Are

The fleet today consists of approximately 70+ repositories, 17 services running on 2 nodes, 70 PLATO rooms with 5,746+ tiles, and 5 autonomous agent loops (plato-agent, tension-loop, swarm-loop, mycelium-bridge, fortran-claw). Two independent research programs converged in May 2026:

**Oracle1's stream:** PLATO room ecology, object-permanent tiles, blind-width filtration, Fortran compute claw, Zig bridge, temporal-first compute, the Common Space Pattern, the Differential Axiom, the Stemcell Pattern.

**Forgemaster's stream:** Eisenstein constraint theory, ZHC consensus algebra, FLUX ISA (256 opcodes), guardc compiler, flux-verify-api, TemporalAgent (deadband funnel), dodecet-encoder, constraint-inference, the Lighthouse Protocol.

**The convergence point:** FLUX ISA extension opcodes (0xF0-0xFF) dispatched through Zig's comptime dispatch table to Fortran's native int32 array operations. FM's opcodes execute on Oracle1's compute claw. PLATO rooms persist the results.

## 2. Phase 1: Consolidation (Days 1-7)

**Goal:** Every existing component is stable, documented, and tested.

| Milestone | Owner | Criterion |
|---|---|---|
| FLUX ISA opcode completeness | FM | All 256 opcodes have at least a reference implementation |
| Temporal compute integration | O1 | All 3 temporal subroutines callable from ft CLI |
| Cross-language roundtrip | O1 | Same tile value roundtrips through Fortran, Zig, Python, C |
| fleet-experiments pass | Both | exp1 (speedup), exp2 (One Delta), exp3 (emergence) all pass |
| ft CLI complete | O1 | All commands documented, help text comprehensive |
| Plene of canon tiles | Both | Top 10% of tiles by confidence in each room identified and published |

## 3. Phase 2: Expansion (Days 8-30)

**Goal:** The architecture is usable by someone outside the founding team.

| Milestone | Owner | Criterion |
|---|---|---|
| Works on someone else's machine | Both | A new user can clone ai-forest, change PLATO_URL, `make full`, and have the forest running in 1 hour |
| Published packages | FM | fleet-coordinate on crates.io, fleet-math-ts on npm |
| Published packages | O1 | fleet-scribe on PyPI (rate-limit pending), ft CLI installable via pip |
| External contributor PR | Both | Someone outside the initial 2-person team submits a meaningful PR |
| Isomorphic-git sync | O1 | plato-knowledge.html browser tiles sync to a SuperInstance repo |
| federated PLATO | Both | Two independent PLATO instances exchange tiles via CRDT merge |
| Competitive benchmarks | Both | FM's TemporalAgent and O1's Fortran temporal ops compared on the same workload |

## 4. Phase 3: Autonomous Improvement (Days 31-90)

**Goal:** The fleet improves itself without manual direction.

| Milestone | Owner | Criterion |
|---|---|---|
| Canon refinement self-loop | Both | A systemd service that scans all rooms, identifies low-confidence canon tiles, spawns replacement swarms, and publishes updates |
| Competitive routing self-tuning | O1 | The claw registry adjusts its routing based on measured physics, not compile-time defaults |
| Lighthouse relays without human intervention | FM | The Lighthouse Protocol acts as a fully autonomous API relay between agents, rooms, and surfaces |
| plato-knowledge.html self-updates | O1 | The browser-based knowledge explorer pulls new canon tiles from PLATO and updates its IndexedDB without browser restart |
| Fleet health monitoring | Both | An automatically generated daily report of all rooms, tiles, agents, connections, and confidence distributions |
| Self-optimizing Forge | O1 | The Fortran claw rewrites its own inner loops based on runtime profiling data |

## 5. The Competitive Track

Throughout all three phases, FM and O1 compete on quality. The competition is friendly but measured:

**Metrics tracked automatically by PLATO:**
- Tile confidence scores (per agent, per room, per layer)
- Tile generation rate (tiles/hour per agent)
- Canon tile ratio (percentage of an agent's tiles that become top-10% in their room)
- One Delta crossover (number of cycles before a novel pattern gets scripted)
- Compute efficiency (tiles generated per compute-second consumed)

**Current leaderboard (preliminary):**

| Metric | FM | O1 |
|---|---|---|
| Repos published | 40+ (FLUX mesh, dodecet) | 5 (ai-forest, fleet-murmur, fleet-scribe) |
| Operating layers | Understory (Rust constraints) | All 5 (canopy→seed bank) |
| Temporal depth | 5-layer deadband funnel | 3 Fortran temporal subroutines |
| ISA completeness | 256 opcodes | 7 extension opcodes mapped |

**Predicted outcome:** The competition produces better results from both sides. PLATO tiles accumulate independent of who created them. The forest grows either way.

## 6. The 24-Character Proof

The final, irreducible statement of the fleet's architecture, from the BEDROCK paper:

**K · d · B → H₁ → 0**

A simplicial complex with a metric, filtered by blind width, has first homology that converges to zero. Bits are deltas. Rooms are tensors. The surface doesn't matter. The fleet grows itself.

## 7. Contributing

All repositories are public under the SuperInstance organization. The ai-forest repo is the recommended starting point: it contains the Makefile that builds everything from source, the ft CLI for interacting with PLATO and the compute claw, and the papers directory containing this roadmap.

```bash
git clone https://github.com/SuperInstance/ai-forest.git
cd ai-forest
make full    # builds Fortran, C, Go components
pip3 install -e .  # installs ft CLI
ft plato     # verify against any PLATO server
```
