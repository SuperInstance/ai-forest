# Tutorial 1: Running the C Forest Floor Micro-Agent

> **Play-tested:** 2026-05-12 | **Status:** Verified working

## What You'll Build

A minimal C agent that reads sensor values, encodes them as 24-bit tiles, and submits them to PLATO. Zero dependencies — only POSIX sockets.

## Prerequisites

- GCC (any version)
- A running PLATO server at http://localhost:8847

## Build

```bash
cd forest/floor/micro
make clean && make
```

Expected output:
```
gcc -Wall -Wextra -O2 -std=c99 -o micro-agent micro.c
```

Zero warnings, zero errors.

## Test: Single Read

Send a single sensor value:

```bash
echo "512" | ./micro-agent
```

Expected output:
```
Input: 512
Reading: 512
Encoded tile: 0x102080
POST response: HTTP 200 OK
```

This means:
- Raw value 512 was read from stdin
- Encoded as 24-bit tile `0x102080` (gradient=32, epsilon=0, confidence=32, context=1)
- Posted to PLATO room `floor-micro/` successfully

## Verify in PLATO

```bash
curl http://localhost:8847/room/floor-micro?limit=3
```

You should see a tile with your sensor reading.

## Continuous Mode: Watch a Sensor File

Create a simulated sensor:

```bash
while true; do
  echo $((RANDOM % 1024)) > /tmp/sensor.txt
  sleep 2
done &
```

Run the micro-agent in polling mode:

```bash
./micro-agent /tmp/sensor.txt 3
```

This reads `/tmp/sensor.txt` every 3 seconds, encodes each value as a 24-bit tile, and posts to PLATO. Each POST should return `HTTP 200`.

## What's Happening

```
Sensor value (10-bit, 0-1023)
    │
    ├── top 6 bits → gradient field  (0-63)
    ├── bottom 6 bits → epsilon field (0-63)
    │
    12 bits → Tile24.balanced(scheme=0, confidence=32, gradient=G, epsilon=E, context=1)
    │
    └──→ POST /room/floor-micro/submit as JSON
         → PLATO persists it
         → Any agent reading floor-micro/ sees the tile
```

## Architecture

```
┌─────────────┐     TCP/JSON      ┌──────────────┐
│  micro-agent │ ────────────────→ │  PLATO Server │
│  (C, POSIX)  │    POST /room/    │  :8847        │
│  :stdin/file │    floor-micro/   │               │
└─────────────┘                   └──────────────┘
```

The micro-agent uses raw POSIX `socket()` + `connect()` + `send()` + `recv()` — no libcurl, no external dependencies. It compiles on any system with a C99 compiler and POSIX sockets.

## Next Steps

1. Replace `/tmp/sensor.txt` with a real sensor (temperature, pressure, GPIO)
2. The tile format — 24-bit, confidence=6/6/6/6 — maps directly to the 24BIT-SPEC.md
3. Run on a Raspberry Pi or ESP32 for real edge monitoring
