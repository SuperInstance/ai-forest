# AI Forest — Floor Micro-Agent

A minimal C sensor agent for embedded edge devices in the AI Forest floor layer.

## Overview

Reads sensor values, encodes them as 24-bit tiles, and POSTs them to the AI
Forest floor room (Plato relay) via raw POSIX sockets.

**Zero external dependencies.** Just POSIX sockets and standard C library.

## Build

```sh
make
```

Produces the `micro-agent` binary.

## Usage

```sh
# Poll a sensor file every 5 seconds (default)
./micro-agent

# Custom interval
./micro-agent 2

# Read from a specific sensor file every 10 seconds
./micro-agent 10 /sys/class/thermal/thermal_zone0/temp

# Single read from stdin
echo "512" | ./micro-agent
```

### Environment

| Variable    | Default     | Description          |
|-------------|-------------|----------------------|
| `FLOOR_HOST`| `localhost` | Target hostname      |
| `FLOOR_PORT`| `8847`      | Target port          |

## 24-bit Tile Format

| Field      | Bits | Description              |
|------------|------|--------------------------|
| scheme     | 2    | Encoding scheme (00 = balanced) |
| confidence | 6    | Confidence in the reading |
| gradient   | 6    | Magnitude band (upper bits) |
| epsilon    | 6    | Residual detail (lower bits) |
| context    | 6    | Sensor type indicator     |

The tile encodes a 10-bit sensor value (0–1023) by splitting it:
- **gradient** = upper 6 bits (value >> 4)
- **epsilon**  = lower 6 bits (value & 0x3F)

## Targets

```sh
make        # build
make clean  # remove binary
make run    # build + run with default interval
```

## Architecture

```
[sensor] --value--> [micro-agent] --tile[POST]--> floor room (Plato)
                                                      |
                                                   [higher agents]
```

The micro-agent is the ground truth layer — it runs close to the sensor,
produces structured 24-bit observations, and pushes them into the forest
for higher-level agents to consume.
