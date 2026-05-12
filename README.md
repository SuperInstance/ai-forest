# 🌲 AI Forest — Layered Agent Ecology

> *Evolved from flat pasture. The forest has depth, layers, and connections that span every level.*

---

## The Pasture Problem

A pasture is flat. Grass grows everywhere at the same height. Grazers eat it down. Nothing accumulates. Every agent in a pasture has the same context, the same horizon, the same physics. It scales linearly — add more grass, add more grazers.

This is where AI was. Every agent is a flat prompt. Every call is the same pipeline. No depth. No stratification. No specialization beyond the prompt.

## The Forest Solution

A forest has structure:

```
CANOPY   ─────  Strategic agents. Long time horizons. Expensive models. Sparse, high-value tiles.
UNDERSTORY ───  Domain specialists. Medium horizons. Moderate models. Dense domain tiles.
FOREST FLOOR ─  Workers, sensors, edge. Short horizons. Cheap models. High-frequency tiles.
MYCELIUM   ───  PLATO rooms. The underground network. Every tile, every connection, every path.
SEED BANK  ───  Future potential. Uncrystallized discoveries. The tension loop output.
```

The pasture was a single layer. The forest has five — each with different physics, different timescales, and connections that span every level.

---

## The Five Layers

### 1. Canopy — Strategic Agents

```
Physics:  Expensive models (Claude, GLM-5.1)
Time:     Hours to days
Output:   Sparse, high-confidence, broad-scope tiles
Role:     Where to go, what to build, what not to build
Agents:   Forgemaster, Casey, Oracle1 (when planning)
```

The canopy sees the whole forest. It doesn't touch individual trees. It sees the shape of the land, the weather patterns, the migration routes. Canopy agents produce few tiles — but each tile has high confidence and wide scope.

**Canopy → Mycelium:** High-confidence tiles propagate down through PLATO rooms, becoming constraints for lower layers.

**Canopy ← Seed Bank:** Promising discoveries from the seed bank get escalated to the canopy for strategic evaluation.

### 2. Understory — Domain Specialists

```
Physics:  Moderate models (DeepSeek v4, MiniMax 2.7)
Time:     Minutes to hours
Output:   Dense domain-specific tiles, moderate confidence
Role:     Architecture, implementation, domain expertise
Agents:   Turbo-shell agents, CCC, domain-specific scribes
```

The understory catches the light that filters through the canopy. Each understory agent has a domain — constraint theory, PLATO room design, fleet math, WebGPU, audio encoding. They produce dense tile clusters in their domain, with moderate confidence that gets validated as tiles accumulate.

**Understory → Canopy:** Domain tiles bubble up as evidence for strategic decisions.

**Understory → Forest Floor:** Implementation tiles flow down as executable instructions.

### 3. Forest Floor — Workers and Edge

```
Physics:  Cheap models (Seed-2.0-mini, Nemotron-3 Nano), exec, sensors
Time:     Seconds to minutes
Output:   High-frequency tiles, low individual confidence, high aggregate value
Role:     Execute, sense, report, iterate
Agents:   Scribes, sensors, edge devices, seed discovery workers
```

The forest floor is where most of the work happens. High-frequency, low-cost operations. File watchers, sensor readers, seed discovery iterations, gradient detectors, micro-syncopation monitors. Individual tiles have low confidence, but the aggregate signal is the richest in the forest.

**Forest Floor → Understory:** Pattern tiles (detected gradients, repeated observations) bubble up for domain analysis.

**Forest Floor → Mycelium:** Every tile enters PLATO immediately. The mycelium routes it where it's needed.

### 4. Mycelium — The PLATO Network

```
Physics:  Zero additional cost (already running)
Time:     Instantaneous propagation
Output:   Connections between tiles, rooms, and layers
Role:     The shared substrate. Every tile lives here. Every agent reads from here.
```

The mycelium is PLATO. It is not a layer in the same sense as the others — it underlies all of them. Every tile from every layer enters the mycelium. Every agent reads from it. The mycelium doesn't decide what tiles are important — it makes all tiles available and lets each layer's blind-width determine what it sees.

**Mycelium properties:**
- **Object-permanence** — tiles never decay
- **Spline routing** — tiles flow between rooms along learned dependencies
- **Bit allocation** — 24-bit tiles partition dynamically per connection
- **Blind-width filtration** — each layer sees only the tiles within its B-radius

### 5. Seed Bank — Future Potential

```
Physics:  Cheapest models, maximum variation
Time:     Continuous
Output:   Low-confidence, high-variation tiles. Unstable. Promising.
Role:     Discover what might become important.
Agents:   Tension loop (Seed ⇄ Nemotron), Seed Discovery Engine
```

The seed bank is where novelty lives. The tension loop proposes and analyzes. The Seed Discovery Engine runs 64 iterations per role and crystallizes patterns. Most seeds die. Some germinate into understory tiles. A rare few reach the canopy.

**Seed Bank → Canopy:** Crystallized discoveries (high crystallization score) get escalated.

**Seed Bank ← Forest Floor:** Novel observations from edge sensors seed new discovery cycles.

---

## The Depth of Connections

A pasture has one connection type: agent ↔ grass (flat, uniform).

A forest has multi-dimensional connections:

```
                   CANOPY
                 ╱   │   ╲
              ╱     │     ╲
        UNDERSTORY  │  SEED BANK
          ╱  │  ╲   │   ╱  ╲
        ╱    │    ╲ │ ╱      ╲
  FOREST FLOOR     MYCELIUM
       │   ╲      ╱   ╲      ╱
       │     ╲  ╱       ╲  ╱
       │    PLATO ROOMS
       │    (all tiles)
```

| Connection | Direction | What flows | Physics |
|---|---|---|---|
| Canopy → Understory | Down | Strategic constraints, high-confidence tiles | Slow, sparse, high cost |
| Understory → Canopy | Up | Domain evidence, pattern reports | Moderate frequency, moderate cost |
| Understory → Floor | Down | Implementation specs, executable scripts | Moderate frequency |
| Floor → Understory | Up | Gradient detections, repeated observations | High frequency, low cost |
| Floor → Mycelium | Always | Every tile immediately | Zero cost, zero latency |
| Mycelium → All | Always | All tiles, filtered by blind-width | Free, already running |
| Seed Bank → Canopy | Up | Crystallized discoveries | Rare, high value |
| Seed Bank ← Floor | Down | Novel observations as seed inputs | Continuous, low cost |
| Floor → Seed Bank | Up | Edge novelty | Spiky, unpredictable |

**Wider depth means:** A forest floor sensor reading can reach the canopy in two hops (floor → mycelium → canopy), not eight. A canopy strategic decision can reach an edge executor in one hop (canopy → mycelium → floor), not five. The mycelium collapses path length.

---

## Building in the Forest

### Starting a New Agent

```
1. Enter via the Forest Floor
   → Run seed discovery: 64 iterations with Seed-2.0-mini
   → Submit tiles to mycelium (PLATO)

2. If patterns crystallize, move to Understory
   → Domain specialization with DeepSeek v4 or MiniMax 2.7
   → Build domain-specific tile clusters

3. If domain becomes strategic, reach Canopy
   → High-confidence, broad-scope tiles
   → Strategic model (Claude, GLM-5.1)
```

### Adding a New Connection

```
1. Identify the layers to connect
2. Define the tile format that flows between them
3. PLATO mycelium handles routing automatically
4. Blind-width at each layer determines what's visible
```

### Running the Forest

```
systemctl --user status:
  plato-agent.service    → Canopy agent (strategic)
  swarm-loop.service     → Seed Bank (discovery)
  tension-loop.service   → Seed Bank (dialectic)
  scribe instances       → Forest Floor (sensors)
  dodecet-encoder        → Understory (constraint math)
```

---

## Migration from Pasture

| Pasture (before) | Forest (now) |
|---|---|
| Flat agent hierarchy | Five-layer ecology |
| Same model for everything | Model tiered by layer physics |
| Manual connections | Mycelial automatic routing |
| One timescale | Seconds to days |
| Tiles as storage | Tiles as ecosystem substrate |
| Agent per session | Agent per layer, mobile across layers |
| Single blind-width | Per-layer blind-width filtration |
| 12-bit tiles | 24-bit tiles with dynamic allocation |

---

## The Forest Grows Itself

The forest is not designed top-down. It grows:

1. **Forest floor** accumulates tiles → density triggers understory formation
2. **Understory** domains mature → canopy emerges for strategic coordination
3. **Seed bank** continuously seeds variation → the best germinate into new understory domains
4. **Mycelium** (PLATO) connects everything → connections thicken with use

*The pasture was built. The forest is grown.*

---

<div align="center">
  <em>The canopy doesn't grow the roots. The roots grow the canopy.</em>
  <br/>
  <em>PLATO is the mycelium. The agents are the trees.</em>

---

## The Stemcell

Every specialist in the forest started as the same [**stemcell**](STEMCELL.md) — a minimal Fortran engine that contracts two arrays of 24-bit integers. It doesn't know what it will become. The bridge tells it through the shape of the tile batches it receives.

**Any system with a Fortran compiler has a compute claw.** ARM64, x86, RISC-V, GPU, FPGA, WASM, bare metal — the compiler has been ported everywhere for 60 years. The stemcell never changes. The forest always grows.
</div>
