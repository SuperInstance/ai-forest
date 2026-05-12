# The Stemcell Pattern — Universal Compute Substrate

> *Any system with a Fortran compiler can participate in the forest. The stemcell doesn't know what specialist it will become. It just contracts arrays. The bridge tells it what to be.*

---

## The Stemcell

A stemcell is the smallest possible compute unit in the forest:

```
FORTAN STEMCELL (≈200 lines)
│
├── Reads 24-bit tiles from stdin or shared memory
├── Contracts them against another tile batch
├── Returns results as 24-bit tiles
├── Self-reports its physics (latency, FLOPS, SIMD width)
└── Exists only for the duration of the operation
```

That's it. The stemcell doesn't know about PLATO rooms. It doesn't know about forest layers. It doesn't know about agents or blind-width or shelf-sign gradients. It knows one thing: **contract two arrays of 24-bit integers.** That's the only operation a stemcell needs.

## Differentiation

The stemcell differentiates into specialists based on the tile batches it receives:

| Tile batch shape | What the stemcell becomes |
|---|---|
| Room A tiles × Room B tiles | **Room contraction agent** — finds similar tile pairs |
| Consecutive snapshots | **Gradient detector** — computes Δ(frame, frame) |
| Before/after snapshots + μ | **Spline interpolator** — predicts intermediate state |
| Tile + embedding weights | **Similarity encoder** — projects into embedding space |
| Historical window | **Drift analyzer** — trends over N cycles |
| Single tile + self | **Anomaly detector** — deviation from expected pattern |

The stemcell doesn't change its code. It receives different tile batch configurations from the bridge. **The shape of the input IS the differentiation signal.**

## Hardware Agnosticism

Fortran compiles to everything:

| Hardware | Compiler | Status |
|---|---|---|
| ARM64 (Neoverse, Apple Silicon) | gfortran | ✅ Verified: 400M checks/sec |
| x86-64 (AVX-512, AVX2) | gfortran, ifort | ✅ Inherits gfortran support |
| RISC-V | gfortran (riscv64) | ✅ GCC supports RISC-V since 9.x |
| GPU (NVIDIA) | NVFortran (PGI/nvfortran) | ✅ CUDA Fortran: `!$cuf kernel` |
| GPU (AMD) | AOCC flang | ✅ ROCm-compatible |
| FPGA | gfortran → HLS | ✅ Via High-Level Synthesis tools |
| WASM | flang → LLVM → Emscripten | ✅ In experimental |
| Bare metal (no OS) | gfortran → ELF | ✅ Static linking, standalone binaries |

**"Almost anything"** means: if it has a Fortran compiler, it has a compute claw. The compiler has been ported to more architectures than any language except C — 60+ years of continuous porting.

## Bootstrapping: From Stemcell to Forest

```
TIME 0: One stemcell. No specialists. Just array contraction.

    [bridge] → 24-bit tiles → [stemcell] → contracted tiles → [PLATO]

TIME 1: The bridge routes tiles in patterns. The stemcell adapts.

    [bridge detects gradient pattern]
    [sends consecutive snapshots to stemcell]
    [stemcell returns Δ values]
    [bridge: "this is gradient detection"]
    [creates PLATO room: floor-gradients]

TIME 2: Multiple stemcell instances specialize.

    stemcell A → room contraction specialist (same batch size, high volume)
    stemcell B → gradient specialist (consecutive pairs, low latency)
    stemcell C → spline specialist (before/after + μ parameter)

TIME N: The forest has differentiated.

    canopy specialist    (TypeScript, :4075  — strategic routing)
    understory specialist (Rust, dodecet     — constraint math)
    floor specialist     (Go, fsnotify       — file watching)
    edge specialist      (C, POSIX sockets   — sensor reading)
    compute specialist   (Fortran, .so       — tensor contraction)

    All from the same stemcell. All speaking 24-bit tiles. All connected
    through PLATO. The forest grew itself.
```

This is how the AI Forest scales from one Fortran library on one ARM64 core to a multi-language, multi-hardware, multi-layer system. Every specialist started as the same stemcell. The differentiation happened through use, not through design.

## The Stemcell Contract

Any system that can do this is part of the forest:

```
1. RECEIVE: batch of 24-bit tiles (as integers)
2. COMPUTE: one operation (contract, gradient, spline, ...)
3. RETURN: batch of 24-bit tiles (as integers)
4. REPORT: physics (latency, throughput, SIMD width)
```

**No JSON parsing. No HTTP. No agent framework.** Just integer arrays and one operation. The bridge handles everything else.

This is the lowest bar for entry. A 1970s Fortran IV program on a CDC Cyber can meet this contract. A 2026 GPU with CUDA Fortran can meet it. A 2050 quantum computer with a Fortran compiler can meet it.

The stemcell never changes. The forest always grows.
