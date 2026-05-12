# AI Forest — Floor Agent

A Go-based forest floor agent that watches directories for file changes, computes gradient deltas, and submits 24-bit tiles to a PLATO-compatible server.

## Architecture

```
┌─────────────────────────────────────────────┐
│              Forest Floor Agent             │
│                                             │
│  ┌──────────┐    ┌──────────┐  ┌─────────┐ │
│  │ fsnotify │───▶│ Gradient │──▶│ 24-bit  │ │
│  │ Watcher  │    │ Computer │  │ Tiler   │ │
│  └──────────┘    └──────────┘  └────┬────┘ │
│                                     │      │
│                              ┌──────▼─────┐│
│                              │  HTTP POST ││
│                              │  to PLATO  ││
│                              └────────────┘│
└─────────────────────────────────────────────┘
```

## Files

| File       | Description                                     |
|------------|-------------------------------------------------|
| `agent.go` | Main agent: watcher, gradient computation, loop |
| `tile.go`  | 24-bit tile encoding/decoding                   |
| `README.md`| This file                                       |

## 24-bit Tile Format

The tile packs 4 fields into a 24-bit uint32:

```
Bit 23-22: Scheme (2 bits) — 00 = balanced
Bit 21-16: Confidence (6 bits, 0-63)
Bit 15-10: Gradient   (6 bits, 0-63)
Bit 9-4:   Epsilon    (6 bits, 0-63)
Bit 3-0:   Context    (4 bits, 0-15)
```

### Fields

- **Confidence**: How reliable the gradient measurement is (more tracked files = higher confidence)
- **Gradient**: Ratio of absolute size change to total tracked size (0.0–1.0 mapped to 0–63)
- **Epsilon**: Noise/uncertainty metric, inversely proportional to tracked file count
- **Context**: Activity level — how many file changes occurred in this cycle (capped at 15)

## Usage

### Environment Variables

| Variable            | Default                    | Description                  |
|---------------------|----------------------------|------------------------------|
| `FLOOR_WATCH_DIR`   | `.` (current dir)          | Directory to watch           |
| `FLOOR_AGENT_NAME`  | `oracle1`                  | Agent identifier for PLATO   |
| `FLOOR_INTERVAL`    | `10s`                      | Tile submission interval     |
| `FLOOR_SERVER_URL`  | `http://localhost:8847`    | PLATO server base URL        |

### Run

```bash
# Watch current directory
go run .

# Watch a specific directory
FLOOR_WATCH_DIR=/tmp/data FLOOR_AGENT_NAME=scout1 go run .
```

Tiles are posted to `{SERVER_URL}/room/floor-{AGENT_NAME}/submit` as JSON.

## Output Example

```
🔮 Forest Floor Agent — oracle1
   Watch Dir:  /tmp/ai-forest/floor
   Interval:   10s
   Server URL: http://localhost:8847
[oracle1] cycle: 0 changes, watching 0 files
[oracle1] submitted tile Tile{scheme=0, conf=5, grad=32, eps=63, ctx=3} | delta=1024 total=4096 changes=3 files=1
```

## Dependencies

- `github.com/fsnotify/fsnotify` — filesystem event notifications
