# Tutorial 2: Cross-Layer Routing with the Mycelium Bridge

> **Play-tested:** 2026-05-12 | **Status:** Verified working

## What You'll Build

Connect agents from different forest layers (canopy, forest floor, seed bank) through the mycelium bridge. Route tiles between layers. See them appear in PLATO.

## Prerequisites

- Python 3.8+
- PLATO server running at http://localhost:8847
- The mycelium bridge code at `forest/mycelium/`

## Start the Bridge

```bash
cd forest/mycelium
python3 bridge.py --port 4080
```

Expected output:
```
08:41:31 [INFO] Mycelium Bridge starting on port 4080
08:41:31 [INFO] PLATO connected at http://localhost:8847
08:41:31 [INFO] Server running at http://0.0.0.0:4080
```

## Step 1: Register Agents in Each Layer

```bash
# Canopy agent
curl -X POST http://localhost:4080/register \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"oracle1","layer":"canopy","capabilities":["strategy","coordination"]}'

# Forest floor agent
curl -X POST http://localhost:4080/register \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"micro-sensor","layer":"forest-floor","capabilities":["sensor-read","edge"]}'

# Seed bank agent
curl -X POST http://localhost:4080/register \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"tension-loop","layer":"seed-bank","capabilities":["discovery","dialectic"]}'
```

Each returns: `{"ok": true, "layer": "...", "agent_id": "...", "agent_count": N}`

Verify with:

```bash
curl http://localhost:4080/layers
```

Expected:
```json
{
  "layers": {
    "canopy": {"agents": ["oracle1"], "tile_count": 0},
    "forest-floor": {"agents": ["micro-sensor"], "tile_count": 0},
    "seed-bank": {"agents": ["tension-loop"], "tile_count": 0}
  },
  "total_layers": 3,
  "total_agents": 3
}
```

## Step 2: Submit a Tile

Send a 24-bit encoded tile from the forest floor:

```bash
curl -X POST http://localhost:4080/tile \
  -H "Content-Type: application/json" \
  -d '{"value": 1057035, "source": "micro-sensor", "layer": "forest-floor"}'
```

Expected response:
```json
{
  "value": 1057035,
  "source": "micro-sensor",
  "decoded": {
    "scheme": 1,
    "fields": [0, 8, 267],
    "readable": "[SENSOR] (0x10210B) x=0, y=8, temp=267"
  },
  "plato_routed": true,
  "plato_room": "ai-forest"
}
```

The value `1057035` = `0x10210B` decodes as: scheme=01 (sensor), x=0, y=8, temp=267.

## Step 3: Route a Tile Between Layers

Route the floor tile up to the canopy:

```bash
curl -X POST http://localhost:4080/route/forest-floor/canopy \
  -H "Content-Type: application/json" \
  -d '{"value": 1057035, "source": "micro-sensor"}'
```

This:
1. Reads the tile from the floor layer
2. Creates a routed tile with source `forest-floor/micro-sensor`
3. Posts to room `ai-forest/` in PLATO
4. Logs the routing to stdout

Bridge log shows:
```
08:41:31 [INFO] TILE forest-floor micro-sensor -> PLATO/ai-forest (ok=True) | [SENSOR] (0x10210B)
08:41:31 [INFO] ROUTE forest-floor -> canopy tile=1057035
```

## Step 4: Verify in PLATO

```bash
curl http://localhost:8847/room/ai-forest?limit=3
```

You'll see the routed tile with source information and layer origin.

## How It Works

```
┌──────────────┐     POST /tile      ┌──────────────────┐     POST /room/     ┌──────────────┐
│ Forest Floor ├───────────────────→  │ Mycelium Bridge  ├───────────────────→ │    PLATO     │
│ (Go/C agent) │                     │ :4080            │                     │ :8847        │
└──────────────┘                     │                  │                     └──────────────┘
                                     │ 1. Decode 24-bit │                           ↑
┌──────────────┐     POST /route     │ 2. Register src  │     POST /room/           │
│    Canopy    ├───────────────────→ │ 3. Forward layer ├──────────────────────────┘
│  (TypeScript)│                     │ 4. Route to PLATO│
└──────────────┘                     └──────────────────┘
```

The bridge is the universal connector. Any agent in any language sends tiles to it. The bridge:
1. Decodes the 24-bit value into its semantic fields (scheme, gradient, epsilon, context)
2. Registers the agent in its layer (if not already registered)
3. Routes the tile to the target layer through PLATO
4. Logs every operation

## Cross-Language Tile Format

The 24-bit tile at the heart of this is the same format used by the C micro-agent (Tutorial 1):

```
Bit:  23  22  21  20  19  18  17  16  15  14  13  12  11  10  09  08  07  06  05  04  03  02  01  00
     ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
     │ SCHEME │       FIELD A       │       FIELD B       │       FIELD C       │       FIELD D       │
     │  2 bits│      6 bits         │      6 bits         │      6 bits         │      6 bits         │
     └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

- C: `typedef union { uint32_t raw; struct { unsigned scheme:2; unsigned conf:6; ... } } Tile24;`
- Python: `tile_codec.py` encodes/decodes all 8 schemes
- Go/TypeScript: Same format, different syntax

## Next Steps

1. Run the C micro-agent (Tutorial 1) and route its tiles through this bridge
2. Add more agents to each layer and watch cross-layer routing grow
3. The bridge tracks tile counts per layer — use this to measure forest health
