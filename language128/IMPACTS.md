# 128 Language — Impact Analysis

> *What changes when every word is 128 bits? Everything.*

---

## Impact 1: The Fortran Interop

**Before:** Each Fortran call processes one 32-bit tile at a time. Contract loops over 32-bit values. The ring buffer stores 32-bit tiles.

**After:** Each Fortran call processes four 32-bit tiles packed into one 128-bit word. The same contract loop operates on wider registers.

```
Before (32-bit):      After (128-bit):
  call contract(a)      call contract_128(a)
  a[0] = 0x12345678     a[0] = 0x12345678_9ABCDEF0_11111111_22222222
  a[1] = 0x9ABCDEF0     a[1] = 0x33333333_44444444_55555555_66666666
  a[2] = 0x11111111     (4× fewer iterations for same total throughput)
  a[3] = 0x22222222
  4 iterations           1 iteration
```

**Impact on contract throughput:**

| | 32-bit (current) | 128-bit (projected) | Ratio |
|---|---|---|---|
| Values per register | 1 | 4 | 4× |
| Values per cache line | 16 | 64 | 4× |
| Total throughput (ARM NEON) | 5.2B/s | ~20B/s | 3.8× |
| Total throughput (AVX-512) | ~40B/s | ~150B/s | 3.8× |

The 3.8× (not 4×) comes from packing/unpacking overhead — the price of extracting individual 32-bit values from 128-bit words.

**New subroutine signatures in the Fortran .so:**

```fortran
! 32-bit version (current):
subroutine contract(a, na, b, nb, threshold, nresult)
  integer(c_int32_t), intent(in) :: a(na), b(nb)
  
! 128-bit version:
subroutine contract_128(a, na, b, nb, threshold, nresult)
  integer(c_int128_t), intent(in) :: a(na), b(nb)
  ! Each element of a and b holds 4 packed int32 tiles
  ! Access: extract_lane(a(i), 0:3) → individual tiles
```

---

## Impact 2: The Ring Buffer

**Before:** 1M × 32-bit = 4MB. Fits in L3 cache on ARM (4MB Neoverse). On x86 with 1-2MB L3, it spills.

**After:** 1M × 128-bit = 16MB. Does NOT fit in L3 on most current CPUs (ARM Neoverse has 4MB L3, x86 has 1-60MB). BUT:

| CPU | L3 cache | 32-bit (4MB) | 128-bit (16MB) |
|---|---|---|---|
| ARM Neoverse (this CPU) | 4MB | ✅ fits entirely | ❌ spills to DRAM |
| Apple M1/M2 | 16MB | ✅ fits | ✅ fits entirely |
| AMD EPYC (server) | 32-256MB | ✅ fits | ✅ fits entirely |
| Intel Xeon (server) | 30-60MB | ✅ fits | ✅ fits |

**Impact:** Ring buffer moves from "always on-chip" to "on-chip for large CPUs, DRAM for small ones." The 4× throughput gain from wider words compensates for the DRAM latency penalty — total throughput still increases.

**Buffer structure change:**

```fortran
! Current ring buffer:
integer(c_int32_t) :: buffer(BUFFER_SIZE)  ! 1M × 4 bytes = 4MB

! 128-bit ring buffer:
integer(c_int128_t) :: buffer(BUFFER_SIZE)  ! 1M × 16 bytes = 16MB
! Each entry holds 4 tiles
! Write: 4 tiles per write
! Read: 4 tiles per read
! Contract: 4× fewer iterations
```

---

## Impact 3: PLATO Tiles

**Before:** A PLATO tile is a JSON object: question (string), answer (string), confidence (float), source (string), timestamp (string), tags (list). Typical size: 500-2000 bytes.

**After:** A PLATO tile is a single 128-bit word:

```
Bit:   127      96      64      32      0
       ┌────────┬───────┬───────┬───────┐
       │ answer │question│ conf  │ meta  │
       │ hash   │ hash   │+ src  │+ time │
       └────────┴───────┴───────┴───────┘
        32-bit   32-bit  32-bit  32-bit

- Meta (32 bits): 16-bit timestamp (seconds since epoch, 18h resolution)
                   8-bit confidence (0-255 = 0.0-1.0 in 256 steps)
                   4-bit source ID (16 agents)
                   4-bit tags (16 categories)
- Confidence + Source (32 bits): 16-bit FP confidence, 16-bit source hash
- Question hash (32 bits): CRC32 of question text
- Answer hash (32 bits): CRC32 of answer text
```

**Impact on PLATO storage:** A room of 10,000 tiles:

| | Current (JSON) | 128-bit tile | Ratio |
|---|---|---|---|
| Storage per tile | ~1KB | 16 bytes | **64× smaller** |
| Room of 10K tiles | ~10MB | 160KB | **64× smaller** |
| Read 10K tiles over HTTP | ~10MB transfer | 160KB transfer | **64× faster** |
| Contract 10K×10K tiles | 100M JSON parses | 100M int128 reads | **100× faster** |

The 128-bit tile doesn't replace the JSON tile. It's a DIFFERENT REPRESENTATION for the compute layer. The JSON tile is the human-readable interface. The 128-bit tile is the compute interface. Conversion happens at the PLATO bridge:

```
PLATO room (JSON tiles)
    │
    ├──→ ft cat → human reads JSON
    │
    └──→ 128 compiler → contract/spline/gradient → 128-bit tiles → Fortran .so
```

---

## Impact 4: The FLUX ISA

**Before:** FLUX instructions are 4 bytes: 1-byte opcode + 3 × 1-byte operands. The 256 opcodes each operate on 32-bit values.

**After:** FLUX instructions could be 16 bytes: 1-byte opcode + 15 bytes of operands (128-bit operand space). OR: the existing 4-byte instructions remain, but each operand addresses a 128-bit word instead of a 32-bit one.

```
! Current FLUX (32-bit):
0xF0 0x01 0x02 0x03  →  CONTRACT r1, r2, r3
                          (r1,r2,r3 are 32-bit registers)

! 128-bit FLUX (same opcode, wider operands):
0xF0 0x01 0x02 0x03  →  CONTRACT r1_128, r2_128, r3_128
                          (r1_128,r2_128,r3_128 are 128-bit registers)
                          SAME BYTECODE. Different register width.
```

The ISA stays the same. The register width changes. This is the key design decision: **128 doesn't change the instruction set. It changes the data width that the instructions operate on.** The Zig comptime dispatch table generates different code paths for 32-bit vs 128-bit mode, selected at compile time.

---

## Impact 5: Development Workflow

**Before:** To run on Fortran, write Fortran. To run on CUDA, write CUDA. To run on NEON, write NEON. Three implementations. Three codebases. Three times the bugs.

**After:** Write 128 source once. The compiler generates:

```
128 source (one file)
    │
    ├──→ Fortran .so   (gfortran -O3 -fopenmp)   → production on ARM/x86
    ├──→ CUDA kernel   (nvcc -arch=sm_89)         → RTX 4050 (FM's GPU)
    ├──→ ARM NEON      (gcc -march=armv8.2-a)     → Oracle ARM64 (this CPU)
    ├──→ FLUX bytecode (Zig dispatch)              → FLUX VM
    └──→ JSON output   (debugging, PLATO logging)  → PLATO rooms
```

**Impact on maintenance:** One source file instead of 4 implementations. Changes propagate to all backends automatically. The 5th backend (JSON for PLATO logging) is free.

---

## Impact 6: The Fleet

**Before:** 9 languages, 200+ repos, each choosing its own data width and representation. The 24-bit experiment failed because it fought Fortran's native word size.

**After:** 128 language as the UNIFYING ABSTRACTION. The underlying hardware runs Fortran, CUDA, NEON, or FLUX — but the source is always 128. The language adapts to the hardware:

| Hardware | Backend | When |
|---|---|---|
| Oracle Cloud ARM64 (this CPU) | Fortran .so + NEON | Production |
| RTX 4050 (FM's GPU) | CUDA kernel | GPU acceleration |
| Any x86 server | Fortran .so + AVX | Cloud deployment |
| FLUX VM | Bytecode interpreter | Testing/development |
| Browser | WebAssembly | PLATO frontend |

The same 128 source, 5 backends, zero changes. The language IS the adjunction between developer intent and hardware capability.

---

## Impact 7: The Innovation Heartbeat

**Before:** 7 hypothesis generators running Python experiments against PLATO. Each experiment is hand-coded.

**After:** The innovation heartbeat writes 128 source, compiles it, and runs it against all 5 backends. The same hypothesis tested on ARM NEON AND CUDA AND Fortran simultaneously. If the results differ, that's a finding.

```
Innovation Heartbeat
    │
    ├──→ Generates hypothesis in 128 language
    ├──→ Compiles to all 5 backends
    ├──→ Runs against PLATO
    ├──→ Compares results across backends
    └──→ Generates next hypothesis
```

---

## Summary

| | 32-bit era (current) | 128-bit era (projected) |
|---|---|---|
| Tile storage | ~1KB JSON | 16 bytes (64× smaller) |
| Contract throughput | 5.2B/s | ~20B/s (3.8× faster) |
| Backend count | 4 (Fortran, CUDA, NEON, FLUX) | 1 (128 source → all) |
| Ring buffer L3 fit | Fits on ARM only | Fits on large CPUs |
| Language count | 9 | 9 + 1 unifying layer |
| Innovation velocity | Hand-coded experiments | Self-generating experiments |
| PLATO room capacity | 10MB per 10K tiles | 160KB per 10K tiles |
