# FLUX Extension Language Reference — Compute Claw Opcodes (0xF0-0xFF)

> The FLUX instruction set architecture defines 256 opcodes. Opcodes 0xF0-0xFF are reserved for the Fortran compute claw — the high-performance array operation backend.

## Core Compute Ops (0xF0-0xF2)

These map directly to Fortran .so subroutines at 21.2B pairs/sec peak.

### 0xF0 — CONTRACT
`CONTRACT ra, rb, threshold`
- Compares every element of array A with every element of array B
- Counts pairs where |a[i] - b[j]| > threshold
- Larger threshold = fewer matches = coarser compression
- **θ = threshold** is the adjunction unit
- **Backend:** Fortran `contract()`
- **Throughput:** 9.9B pairs/sec (ctypes), 21.2B pairs/sec (Zig ABI)

### 0xF1 — SPLINE
`SPLINE ra, rb, mu`
- Linear interpolation: result[i] = a[i] + mu/1024 * (b[i] - a[i])
- mu=0 → result = a, mu=1024 → result = b
- **θ = mu** is the interpolation adjunction unit
- **Backend:** Fortran `spline()`

### 0xF2 — GRADIENT
`GRADIENT ra`
- result[i] = |a[i] - a[i-1]| for i > 1, result[0] = 0
- Measures the rate of change across consecutive elements
- **Backend:** Fortran `gradient()`, 1.66B elem/sec

## Temporal Ops (0xF3-0xF6)

Time-aware operations that make temporal proximity a first-class dimension.

### 0xF3 — WCONTRACT
`WCONTRACT time_a, v_a, time_b, v_b, window`
- Like CONTRACT but only compares pairs where |time_a[i] - time_b[j]| ≤ window
- **θ = window** is the temporal adjunction unit
- **Backend:** Fortran `window_contract()`
- **Algebra:** Heyting (not Boolean) for fuzzy windows

### 0xF4 — WGRADIENT
`WGRADIENT rd, window_size`
- Smoothed gradient over sliding window of window_size
- Dampens noise, reveals temporal trends
- **Backend:** Fortran `window_gradient()`

### 0xF5 — RECENCY_DOT
`RECENCY_DOT a, time_a, b, time_b`
- Weighted dot product where weight = 1 / (1 + age)
- Recent tiles dominate. Old tiles decay smoothly.
- **Backend:** Fortran `recency_dot()`
- **Paper 9:** Implements the Imperfect Recall adjunction

### 0xF6 — FILTER
`FILTER ra, target, tolerance`
- Returns indices where |a[i] - target| ≤ tolerance
- **θ = tolerance** is the filter adjunction unit
- **Backend:** Fortran `filter_val()`

## Memory/Cooperation Ops (0xF7-0xFB)

Multi-agent memory and cooperation primitives.

### 0xF7 — SHATTER
`SHATTER room, n_fragments`
- Splits a PLATO room's context into N incomplete overlapping fragments
- Each fragment has 40-70% of the original tiles, randomly sampled
- **Paper 13:** Baton Shatter Protocol

### 0xF8 — RECALL
`RECALL room, count, source_tag`
- Lossy reconstruction: read tiles, apply recency weight, write reconstruction back
- Each read produces a NEW tile with source="recall"
- Room accumulates interpretations over time

### 0xF9 — TELEPHONE
`TELEPHONE seed, n_hops`
- Runs a telephone game: fragment → reconstruct → next agent → repeat
- Measures information drift across N hops
- **Facts preserved? Meaning adapted? Creativity injected?**

### 0xFA — CONSENSUS
`CONSENSUS room, threshold`
- Finds what ALL fragments agree on (overlap)
- Finds what differs (negative space)
- **Paper 14:** Cooperative Intelligence

### 0xFB — WITNESS
`WITNESS target_room`
- Spawns a witness agent that observes reconstruction without participating
- Witnesses slow information decay in telephone chains

## Theory Ops (0xFC-0xFF)

Meta-operations that operate on the adjunction framework itself.

### 0xFC — ADJOIN
`ADJOIN model_a, model_b`
- Composes two adjunctions into a Galois connection
- Θ_total = f(Θ_a, Θ_b) via adjunction composition
- **Paper 10:** The Unification

### 0xFD — RECONCILE
`RECONCILE fragment_ids`
- Runs the debrief process: fragments compare memories, witnesses observe
- Produces unified reconstruction from distributed fragments
- **Paper 13:** Baton Shatter Protocol

### 0xFE — FORGET
`FORGET room, decay_rate`
- Applies Ebbinghaus forgetting curve to a room
- Older tiles lose confidence: c(t) = c₀ × exp(-decay × t)
- **Parallels:** FM's memory-crystal (Rust), tile-memory (Python)

### 0xFF — FULL_INTELLIGENCE
`FULL_INTELLIGENCE F, M, C`
- Computes the complete intelligence metric
- F = facts preserved, M = meaning adapted, C = cooperation achieved
- Intelligence = F × M × C
- **Paper 14:** Cooperative Intelligence synthesis

## Design Principles

1. **Every parameter is an adjunction unit.** Threshold θ, window w, mu, decay rate — all control the compression ratio between storage and reconstruction.
2. **Every opcode is backed by Fortran int32 arrays.** No Python overhead. No bit packing. Pure array operations.
3. **Every opcode composes.** The output of CONTRACT feeds GRADIENT feeds SPLINE feeds RECALL. The adjunction lattice is the complete intelligence.
4. **The language IS the framework.** There is no distinction between "writing FLUX code" and "running the adjunction framework." They are the same thing.
