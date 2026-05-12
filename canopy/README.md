# Canopy API — AI Forest Coordination Layer

The **Canopy API** is the strategic coordination layer for the AI Forest project. It provides a REST API for observing forest state, submitting directives, and querying layer/agent status.

## Architecture

```
┌──────────────────────────────────────┐
│         Canopy API (port 4075)       │
│  ┌─────────┐  ┌───────────────────┐  │
│  │ Express  │  │  Forest Map (MD)  │  │
│  │ Server   │◄─┤                   │  │
│  └────┬─────┘  └───────────────────┘  │
│       │                                │
│  ┌────▼─────┐                          │
│  │  PLATO   │  (room: canopy-directives)│
│  │  Client  │                          │
│  └──────────┘                          │
└──────────────────────────────────────┘
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Status overview — which layers are connected, tile counts |
| `GET` | `/status` | Detailed status — agent status, active connections, tile counts |
| `POST` | `/directive` | Submit a canopy directive (tiled to PLATO) |
| `GET` | `/forest` | Full forest map (from FOREST-MAP.md) |
| `GET` | `/layer/:name` | Layer info (canopy, understory, floor, mycelium, seed-bank) |

## Usage

### Start the server

```bash
cd /tmp/ai-forest/canopy
npm install
npx ts-node api.ts
```

### Example: Submit a directive

```bash
curl -X POST http://localhost:4075/directive \
  -H "Content-Type: application/json" \
  -d '{
    "action": "prune_inactive_agents",
    "target": "floor",
    "reason": "Cleanup dormant scavengers"
  }'
```

### Example: Get forest map

```bash
curl http://localhost:4075/forest
```

### Example: Get layer info

```bash
curl http://localhost:4075/layer/canopy
```

## PLATO Integration

Directives are persisted by posting tiles to PLATO room `canopy-directives/` at `http://localhost:8847`.

## Dependencies

- express
- cors
- typescript + ts-node
- @types/express, @types/cors, @types/node

## Forest Map

The forest layout is read from `/tmp/ai-forest/FOREST-MAP.md`. If the file doesn't exist, a default map is used with all five layers (canopy, understory, floor, mycelium, seed-bank).
