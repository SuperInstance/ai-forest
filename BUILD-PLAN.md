# AI Forest — Multi-Language Build Plan

> Every layer optimizes for different physics. Every language targets different hardware.

---

## Language Selection by Layer

| Layer | Primary Language | Why | Secondary |
|---|---|---|---|
| **Canopy** | TypeScript/Node.js | Async coordination, API servers, strategic routing | Python |
| **Understory** | Rust | Performance-critical math, constraints, fleet protocols | Go, Python |
| **Forest Floor** | Go + C | Edge devices, sensors, high-frequency watchers | Rust, WASM |
| **Mycelium** | Python | PLATO server (existing), tile storage, room routing | — |
| **Seed Bank** | Python + Rust | Tension loop (Python), Seed Discovery (Rust) | — |
| **Bridge** | All | Common 24-bit tile format across every language | — |

## Build Order

1. **Cross-language 24-bit tile spec** — The common format every layer speaks
2. **Go forest floor agent** — Fast edge watcher/sensor for floor layer
3. **TypeScript forest canopy API** — Canopy coordination server
4. **Forest unified API** — Every layer reachable from every other in 1 hop
5. **Rust forest understory module** — Understory math/constraint agent
6. **C forest floor micro-agent** — Minimal edge sensor for embedded

---

## Implementation Plan

### Phase 1: 24-bit Tile Spec (cross-language)
File: `ai-forest/24BIT-SPEC.md`
Languages: All

### Phase 2: Go Forest Floor Agent
File: `ai-forest/floor/agent.go`
Optimizes for: concurrency, edge deployment, high-frequency sensors

### Phase 3: TypeScript Canopy API
File: `ai-forest/canopy/api.ts`
Optimizes for: async coordination, REST/WebSocket endpoints

### Phase 4: Rust Understory Module
File: `ai-forest/understory/agent.rs`
Optimizes for: constraint checking, fleet math, performance

### Phase 5: Python Mycelium Extension
File: `ai-forest/mycelium/bridge.py`
Optimizes for: PLATO integration, cross-layer routing

### Phase 6: C Forest Floor Micro-Agent
File: `ai-forest/floor/micro.c`
Optimizes for: embedded, minimal dependencies, sensors
