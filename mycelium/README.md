# 🌿 AI Forest Mycelium Bridge

The universal connector for the AI Forest — a multi-language agent ecosystem.

Every layer (Go, Rust, TypeScript, C, Python) sends **24-bit tiles** to this bridge.
The bridge normalizes, logs, and routes tiles to PLATO for persistence and
cross-layer communication.

## Architecture

```
Go Agent ────┐
Rust Agent ──┤
TS Agent  ───┼──► Mycelium Bridge (:4080) ──► PLATO (:8847)
C Agent   ───┤           │
Python   ────┘           ├──► Log every tile to stdout
                         ├──► Track active agents per layer
                         └──► Route tiles to correct rooms
```

**Bridge responsibilities:**
- Accept tiles from any layer in any format
- Normalize everything to canonical 24-bit tiles
- Route tiles to PLATO rooms for persistence
- Track which agents are active in which layers
- Route tiles between layers through PLATO

## File Structure

```
/tmp/ai-forest/mycelium/
├── bridge.py            # Main bridge server (port 4080)
├── tile_codec.py        # 24-bit tile encode/decode helpers
├── forest_state.py      # Layer/agent registry and tile tracking
├── requirements.txt     # Dependencies (zero outside stdlib)
└── README.md            # This file
```

## Tile Format

24-bit value, MSB-first:

| Bits | Field | Description |
|------|-------|-------------|
| 23-20 | scheme (4 bits) | Tile type identifier (0-15) |
| 19-0  | fields (20 bits) | Data fields, split per scheme |

### Schemes

| ID | Name | Fields |
|----|------|--------|
| 0 | RESERVED | (null tile) |
| 1 | SENSOR | x(5), y(5), temp(10) |
| 2 | ACTUATOR | id(8), value(12) |
| 3 | STATE | key(10), val(10) |
| 4 | SIGNAL | type(4), channel(8), magnitude(8) |
| 5 | META | tag(8), seq(12) |
| 6 | COMMAND | op(6), target(6), payload(8) |
| 7 | ERROR | code(8), detail(12) |
| 8-15 | CUSTOM | Layer-specific |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Status page with connected layers |
| `GET` | `/layers` | List all connected layers and agents |
| `GET` | `/layer/{name}` | Get details for a specific layer |
| `GET` | `/read/{room}` | Read tiles from a PLATO room |
| `GET` | `/forest` | Read the forest map structure |
| `GET` | `/health` | Health check |
| `POST` | `/tile` | Accept a tile from any layer |
| `POST` | `/route/{from}/{to}` | Route a tile between layers |
| `POST` | `/register` | Register an agent |
| `POST` | `/heartbeat` | Agent heartbeat |

## Usage

### Start the bridge

```bash
python3 bridge.py --port 4080
```

### Post a tile (direct value)

```bash
curl -X POST http://localhost:4080/tile \
  -H "Content-Type: application/json" \
  -d '{"value": 123456, "source": "python/test-agent", "layer": "python", "agent_id": "agent-1"}'
```

### Post a tile (scheme + fields)

```bash
curl -X POST http://localhost:4080/tile \
  -H "Content-Type: application/json" \
  -d '{"scheme": 1, "fields": [10, 20, 300], "source": "go/sensor-bot", "layer": "go"}'
```

### Route a tile between layers

```bash
curl -X POST http://localhost:4080/route/go/rust \
  -H "Content-Type: application/json" \
  -d '{"value": 0x1E240, "source": "go/sensor-bot", "agent_id": "sensor-bot"}'
```

### Register an agent

```bash
curl -X POST http://localhost:4080/register \
  -H "Content-Type: application/json" \
  -d '{"layer": "rust", "agent_id": "calc-worker", "info": {"version": "0.1.0"}}'
```

### Read a PLATO room

```bash
curl http://localhost:4080/read/ai-forest
```

### Check status

```bash
curl http://localhost:4080/
curl http://localhost:4080/forest
```

### Check health

```bash
curl http://localhost:4080/health
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PLATO_URL` | `http://localhost:8847` | PLATO endpoint URL |

## Connecting Layers

Each language layer should:
1. **Register** with the bridge on startup: `POST /register`
2. **Send heartbeats** periodically: `POST /heartbeat`
3. **Post tiles**: `POST /tile` with JSON body
4. **Read tiles**: `GET /read/{room}` or subscribe to PLATO events
5. **Route between layers**: `POST /route/{from}/{to}`

The bridge is stateless apart from agent tracking. PLATO provides persistence
and event streaming for all tiles.
