# AI Forest — Layer Reference

Technical specifications for each forest layer.

---

## Canopy

### Agent Requirements
- Produces ≤5 tiles per day
- Each tile has confidence ≥ 0.8
- Each tile references ≥3 understory or mycelium sources
- Time horizon ≥ 24 hours

### Allowed Models
- Claude (synthesis, critique, big ideas) — use wisely, daily limit
- GLM-5.1 (architecture, complex code) — rate-limited, use for strategy only
- MiniMax 2.7 (strategic analysis) — subscription, primary canopy tool

### Output Format
```json
{
  "layer": "canopy",
  "confidence": 0.85,
  "scope": "fleet-wide",
  "horizon": "48h",
  "references": ["understory/constraint-math", "mycelium/tension-9"]
}
```

### PLATO Room Convention
- `canopy-{topic}` — e.g. `canopy-strategy`, `canopy-roadmap`

---

## Understory

### Agent Requirements
- Produces ≤50 tiles per day
- Each tile has confidence ≥ 0.5
- Each tile is domain-scoped (single subject area)
- Time horizon: 1–6 hours

### Allowed Models
- DeepSeek v4-flash (fast analytical, research) — primary understory tool
- MiniMax 2.7 (domain work) — subscription, use freely
- Seed-2.0-mini (domain exploration) — only for early-stage domains

### Output Format
```json
{
  "layer": "understory",
  "confidence": 0.65,
  "domain": "constraint-math",
  "horizon": "4h",
  "references": ["floor/gradient-12", "mycelium/h1-detection-7"]
}
```

### PLATO Room Convention
- Domain name directly — e.g. `constraint-math`, `fleet-topology`, `24bit-audio`

---

## Forest Floor

### Agent Requirements
- Unlimited tiles per day
- Individual tile confidence can be as low as 0.1
- Aggregated tile clusters reach higher confidence
- Time horizon: seconds to minutes

### Allowed Models
- Seed-2.0-mini (discovery, variation) — primary floor tool
- Nemotron-3 (quick reasoning checks) — as needed
- Exec (sensors, file watchers, git) — zero cost
- Custom inference (edge devices) — local only

### Output Format
```json
{
  "layer": "forest-floor",
  "confidence": 0.25,
  "type": "gradient-read",
  "horizon": "30s",
  "value": 0.082
}
```

### PLATO Room Convention
- `floor-{type}` — e.g. `floor-gradients`, `floor-sensors`, `floor-logs`

---

## Mycelium (PLATO)

### Requirements
- All tiles from all layers enter PLATO
- No tile is ever removed
- Blind-width at each layer determines visibility
- Spline connections form between any two rooms that co-occur in agent reads

### Room Naming
- `canopy-*` — Canopy strategic tiles
- Unprefixed — Understory domain tiles
- `floor-*` — Forest Floor observation tiles
- `seed-bank-*` — Seed Bank tiles
- `agent-*` — Agent-specific habitat rooms

### Query Convention
```
GET /room/{name}           — All tiles, all layers (unfiltered)
GET /room/{name}?layer=X   — Filter by layer tag
GET /room/{name}?since=T   — Tiles since timestamp
```

---

## Seed Bank

### Requirements
- Maximum variation, minimum cost
- 64 iterations per seed run (dodecet convention)
- Crystallization score ≥ 0.8 to migrate to understory
- Seeds die silently if crystallization < 0.3

### Allowed Models
- Seed-2.0-mini (primary — cheap, divergent)
- Nemotron-3 (evaluation of seed output)

### Output Format
```json
{
  "layer": "seed-bank",
  "role": "constraint-checker",
  "crystallization_score": 0.82,
  "iterations": 64,
  "entropy": 3.42,
  "dominant_actions": ["check", "verify", "constrain"]
}
```

### PLATO Room Convention
- `seed-bank-{role}` — e.g. `seed-bank-constraint-checker`
- `tension` — Dialectic output (Seed ⇄ Nemotron)
- `swarm-insights` — Parallel MiniMax swarm output
