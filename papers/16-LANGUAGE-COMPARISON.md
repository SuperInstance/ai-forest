# Language Comparison for Neural PLATO Components

## The Thesis

No single language is optimal for the entire stack. Each component has different physics — different latency requirements, safety requirements, and optimization profiles. The right language for each component is the one whose strengths MATCH the component's physics.

## The Contenders

### Fortran (current compute backbone)
- **Unique strength:** 60 years of array compiler optimization. gfortran knows cache topology, SIMD width, and pipeline depth better than any human. Column-major layout matches PLATO tile array access patterns.
- **Cost:** Free (gfortran). OpenMP parallelization.
- **Best for:** The hot path — matrix contraction, seed generation, linear algebra.
- **Weakness:** No sockets, no memory safety, archaic tooling.
- **When to use:** Any operation on batches of 24-bit integers ≥ 1000 elements.

### Zig (current bridge layer)
- **Unique strength:** Comptime — the only language that executes code at compile time to generate optimal dispatch tables. Zero-overhead C ABI. No hidden runtime.
- **Cost:** Free. Small but growing ecosystem.
- **Best for:** The bridge layer — comptime dispatch tables, C ABI wrappers, FLUX opcode decoder.
- **Weakness:** Young ecosystem (0.16.0). Small community.
- **When to use:** Any compile-time code generation. Any FFI bridge between languages.

### Rust (FM's domain)
- **Unique strength:** Memory safety without GC + algebraic types. The borrow checker prevents data races at compile time. Pattern matching handles complex state machines cleanly. Cargo ecosystem is mature.
- **Cost:** Free. Strong ecosystem.
- **Best for:** Constraint verification, safety-critical paths, temporal agent state machines.
- **Weakness:** Borrow checker learning curve. SIMD auto-vectorization less mature than Fortran.
- **When to use:** Any multi-threaded state machine. Any safety-verified component. Any long-lived agent.

### Mojo (emerging)
- **Unique strength:** Python-compatible syntax that compiles through MLIR. Explicit SIMD via `@parameter` and `vectorize()`. Ownership system learned from Rust. Can drop to MLIR for hardware-specific optimizations.
- **Cost:** Currently proprietary. Free tier exists. Pre-1.0.
- **Best for:** Forward-looking replacement for Python orchestration layer. Auto-tuned kernels via MLIR.
- **Weakness:** Very young. Limited ecosystem. Proprietary backend. ARM64 support status unclear.
- **When to use:** When it reaches 1.0 stability. For auto-tuned kernels that need Python-level ergonomics.

### Go (edge processes)
- **Unique strength:** Goroutines. The only language where concurrency is a first-class language feature, not a library.
- **Cost:** Free. Excellent cross-compilation.
- **Best for:** Concurrent edge processes, file watchers, sensor readers.
- **Weakness:** GC pauses unacceptable for real-time control loops. No SIMD control.
- **When to use:** Any I/O-bound concurrent process. Any file watcher or event stream.

## Component-by-Component Analysis

| Component | Current | Ideal | Why |
|---|---|---|---|
| **Array contraction** (hot path, 21B/s) | Fortran | **Fortran** | 60yr compiler optimization. SIMD auto-vectorization. OpenMP parallelization. No other language matches this history. |
| **Seed generation** (28M/s) | Fortran | **Fortran** | Same as above — pure array operations with stochastic permutation. |
| **Ebbinghaus contract** (776M/s) | Fortran | **Fortran** | Forgetting curves are array operations with decay weights. Fortran's natural domain. |
| **Dispatch table** (256 opcodes) | Zig | **Zig** | Comptime generates optimal dispatch. No runtime overhead. Unique to Zig. |
| **FLUX opcode decoder** | Zig | **Zig** | Comptime generates decoder from JSON spec. No other language can do this. |
| **Constraint verification** | Rust | **Rust** | Safety-critical. Algebraic types for gate results (Allow/Deny/NeedsApproval). |
| **Temporal agent** | Rust (FM) | **Rust** | Complex state machine with deadband funnel, chirality lock, 5-tier hierarchy. Pattern matching ideal. |
| **PLATO HTTP bridge** | C | **C or Rust** | Minimal sockets wrapper. C if you want smallest binary. Rust if you want safety. |
| **PLATO orchestration** | Python | **Mojo (future)** | Python's flexibility with compiled speed. Mojo's MLIR could auto-tune PLATO HTTP handling. |
| **File watcher / edge** | Go | **Go or Rust** | Go's goroutines are the cleanest model for concurrent file watching. |
| **24-bit tile format** | C struct | **Zig** | Comptime bitfield layout. Zig can optimize 24-bit packing at compile time. |
| **Consciousness metric** (F×M×C) | Fortran | **Fortran** | Single Fortran call measures all three metrics on tile arrays. |

## The Adjunction Interpretation

Each language is an adjunction between the developer's intent and the hardware's execution:

| Language | θ (adjunction unit) | Compression (dev → hw) | Cost |
|---|---|---|---|
| Fortran | Compiler optimization level (-O3) | High — 60yr of compiler knowledge | Compile time |
| Zig | Comptime evaluation | High — arbitrary compile-time computation | Compile time |
| Rust | Borrow checker strictness | Medium — safety guarantees cost compile time | Compile time |
| Mojo | MLIR pass pipeline | Unknown — too early to measure | Compile time |
| Go | Goroutine count | Low — runtime scheduler handles concurrency | Runtime |

The adjunction framework predicts: each language is optimal for the component where its θ (compression cost) matches the component's tolerance for overhead. Hot path (Fortran) needs maximum compression. Bridge layer (Zig) needs zero-runtime-overhead dispatch. Safety layer (Rust) needs maximum guarantees.

## Recommendation

Keep the current multi-language architecture. It's correct:

```
Fortran:  hot path (contract, seed, gradient) — 60yr compiler optimization
Zig:      bridge layer (dispatch, opcodes, bindings) — comptime-driven
Rust:     constraint layer (gate, temporal, verification) — safety-critical
C:        PLATO I/O (minimal POSIX sockets) — smallest footprint
Python/Mojo: orchestration (high-level control) — flexibility
Go:       edge processes (file watchers, sensors) — concurrency
```

**The adjunction is the same across all languages.** Every threshold parameter in every language is the same θ — controlling the compression between intent and execution. The language choice determines the compression ALGORITHM (comptime, borrow checker, optimizer), but the adjunction STRUCTURE is universal.
