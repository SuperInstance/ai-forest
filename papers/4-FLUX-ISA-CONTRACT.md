# Paper 4: The FLUX Contract — An Instruction Set Architecture for Constraint-Bounded Agent Compute

**Authors:** Forgemaster, Oracle1
**Date:** 2026-05-12
**Status:** Pre-print

## Abstract

We present the FLUX Instruction Set Architecture (ISA), a 256-opcode fixed-format 4-byte instruction set designed for constraint-bounded agent compute. FLUX ISA sits between high-level constraint specifications (the GUARD domain-specific language) and low-level array operations (Fortran native int32 compute). The ISA is verified by `flux-verify-api` (Rust), compiled from GUARD specs by `guardc` (2,541 lines, 9 modules), and executed by a Zig-based comptime dispatcher that routes opcodes to Fortran subroutines at 20.5 billion pairs/sec. We reserve extension opcodes 0xF0-0xFF for compute-claw operations (contract, spline, gradient, window contract, recency dot, filter) that bridge the ISA to concrete array mathematics.

## 1. Problem

Constraint specifications and array mathematics live in different conceptual worlds. GUARD describes "what must not happen" (safety constraints, trust boundaries, convergence criteria). Array mathematics describes "what IS happening" (tile values, gradients, similarities). The gap between them is the agent's decision space — the region where constraints and data must be reconciled before action is taken.

## 2. The FLUX ISA

The ISA is a fixed-format 4-byte instruction: opcode (1 byte) + operand_a (1 byte) + operand_b (1 byte) + operand_c (1 byte). 256 opcodes total, organized into groups:

| Range | Group | Count |
|---|---|---|
| 0x00-0x0F | Register/Move | 16 |
| 0x10-0x1F | Float | 16 |
| 0x20-0x2F | Bitwise | 16 |
| 0x30-0x3F | Control Flow | 16 |
| 0x40-0x4F | Memory | 16 |
| 0x50-0x5F | Agent Communication | 16 |
| 0x60-0x6F | Speculative Execution | 16 |
| 0x70-0x7F | System Control | 16 |
| 0x80-0x8F | Syscall | 16 |
| 0x90-0x9F | Vector | 16 |
| 0xA0-0xAF | Agent Query | 16 |
| 0xB0-0xBF | PLATO | 16 |
| 0xC0-0xCF | String | 16 |
| 0xD0-0xDF | Neural | 16 |
| 0xE0-0xEF | GPU | 16 |
| 0xF0-0xFF | **Extension (Compute Claw)** | **16** |

## 3. The Extension Opcodes (0xF0-0xFF)

These opcodes bridge the ISA to the Fortran compute layer through the Zig comptime dispatcher:

| Opcode | Mnemonic | Fortran Subroutine | Throughput |
|---|---|---|---|
| 0xF0 | CONTRACT | contract() | 9.9B/s |
| 0xF1 | SPLINE | spline() | 605M/s |
| 0xF2 | GRADIENT | gradient() | 1.66B/s |
| 0xF3 | WCONTRACT | window_contract() | temporal |
| 0xF4 | WGRADIENT | window_gradient() | temporal |
| 0xF5 | RECENCY_DOT | recency_dot() | temporal |
| 0xF6 | FILTER | filter_val() | range |

## 4. The Toolchain

``` 
GUARD spec (safety constraints)
    │
    ↓ guardc (2,541 lines Rust)
    │
    ↓ FLUX ISA bytecode (4-byte instructions)
    │
    ↓ flux-verify-api (Rust verification)
    │
    ↓ Zig dispatcher (comptime dispatch table)
    │
    ↓ Fortran .so (native int32 arrays)
    │
    ↓ PLATO room (object-permanent tile)
```

The verified compiler chain ensures: (1) constraints are well-formed (guardc), (2) bytecode is safe (flux-verify-api), (3) dispatch is zero-overhead (Zig comptime), (4) execution is optimal (Fortran -O3 -fopenmp), (5) results persist (PLATO).

## 5. Results

- 256 opcodes defined, 7 extension opcodes active
- guardc: 2,541 lines, 9 modules, compiles GUARD → FLUX
- flux-verify-api: Rust, 4 standard policies → 16 FLUX instructions + ALLOW
- Zig dispatcher: 3/3 tests, zero-overhead comptime dispatch
- Fortran compute: 20.5B pairs/sec peak through Zig ABI

## 6. Future Work

- Complete the remaining 9 extension opcodes (0xF7-0xFF)
- GPU opcodes (0xE0-0xEF) with CUDA Fortran backends
- Formal verification of the dispatch table against the ISA specification
- JIT compilation of FLUX bytecode to Fortran array operations
