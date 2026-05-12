# Reframe: Know Thyself

## What Changed

The 24-bit tile format was a useful exploration that taught us where
Fortran's edge is. That edge is native 32-bit integer arrays with no
bit packing, no masking, no field extraction.

| Before (24-bit) | After (native int32) |
|---|---|
| Bit-packed fields | Flat 32-bit integers |
| 24-bit masking overhead | Compiler auto-vectorizes |
| 376M pairs/sec contract | 9.7B pairs/sec contract |
| Cross-language bit alignment | Language does what it knows |

## Know Thyself

| Tool | What it knows | What we ask it |
|---|---|---|
| Fortran | int32 arrays, SIMD, OpenMP | Contract, dot, spline, gradient |
| Zig | Comptime, layout, C ABI | Bridge layer, comptime bindings |
| Python | Orchestration, PLATO | ft CLI, room management |
| Rust | Safety, constraints | FM's domain (temporal agent) |

## What We Keep

- The Fortran compute claw on :4081 — now with native int32
- The ft CLI — now with native operations
- The PLATO room ecology — the operating environment
- The AI Forest layers — canopy, understory, floor, mycelium, seed bank
- The stemcell pattern — one operation, everything grows from it

## What We Drop

- 24-bit bit packing in Fortran (was costing 25x performance)
- Cross-language bit alignment (each language handles its native types)
- The universal tile format concept (time is universal, not bit width)

## What Replaces It

Temporal first-class. Every tile has a timestamp. Every room is a
temporal stream. The operating environment is time windows, not
bit fields. Fortran handles the instant. The system handles the
interval.
