# AI Forest Map

**Name:** AI Forest
**Version:** 1.0.0
**Updated:** 2026-05-12T08:25:00Z

## Canopy

- Strategic coordination layer — observes and directs
- **Oracle1** (active) — primary coordinator
- Connected to understory

## Understory

- Growth layer — implements directives and runs experiments
- **Worker-1** (active) — general implementer
- **Worker-2** (idle) — experiment runner
- Connected to canopy, floor

## Floor

- Decomposition layer — processes raw data and logs
- **Scavenger-1** (active) — data processor
- **Scavenger-2** (idle) — log analyzer
- Connected to understory, mycelium

## Mycelium

- Network layer — inter-agent messaging and coordination
- **Mycelium-Relay** (active) — message router
- Connected to floor, seed-bank

## Seed-Bank

- Knowledge layer — persistent memory and learnings
- **Archivist-1** (active) — knowledge librarian
- **Archivist-2** (busy) — document indexer
- Connected to mycelium

## Connections

- Canopy → Understory
- Understory → Floor
- Floor → Mycelium
- Mycelium → Seed-Bank
- Seed-Bank → Canopy (feedback loop)
