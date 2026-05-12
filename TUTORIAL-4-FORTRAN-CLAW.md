# Tutorial 4: Fortran Compute Claw — Room Tensor Contractions at Hardware Speed

> **Play-tested:** 2026-05-12 | **Status:** Verified working

## What You'll Build

A Fortran shared library that does room-to-room tensor contractions at **400M+ checks/sec** on a single ARM64 core. The bridge calls it as a compute claw — same as any other port.

## The Philosophy

"Little Fortran instances can come and go and have massive compute savings."

Fortran still beats C for array operations. 60 years of BLAS optimization. The compiler knows your cache topology, your SIMD width, your pipeline depth. For PLATO room tensor operations (contracting two rooms of tiles into a similarity matrix), Fortran is the right tool.

## Prerequisites

- gfortran (any version)
- Python 3.8+ with ctypes
- The Fortran code at `forest/fortran/`

## Build

```bash
cd forest/fortran
make
```

Expected:
```
gfortran -O3 -fPIC -fopenmp -march=native -mtune=native -shared -fopenmp -O3 -o libplato_math.so plato_math.f90
```

## Verify

```bash
python3 bench_contract.py
```

Expected output:
```
📋 Physics declaration:
   Latency: 12ns
   FLOPS:   1.2e+10
   SIMD:    16-bit

   📊 10000x10000 tiles: 250.8ms, 32812777 above threshold
      Throughput: 399M checks/sec

📊 Spline interpolation:
   100000 tiles: 0.165ms (605M tiles/sec)

📊 Batch gradient:
   100000 tiles: 0.077ms (1295M tiles/sec)
```

## Operations

### Room Tensor Contraction

Compares every tile in room_a with every tile in room_b. Returns tiles where their confidence×gradient vectors have similarity above threshold.

```python
import ctypes
lib = ctypes.CDLL('./libplato_math.so')

n = 10000
room_a = make_tile_batch(n)   # 10K tiles
room_b = make_tile_batch(n)   # 10K tiles
result = (ctypes.c_int32 * (n * n))()  # up to 100M results
nresult = ctypes.c_int32(0)

lib.contract_tiles(room_a, n, room_b, n, result,
    ctypes.byref(nresult), ctypes.c_float(0.3))

print(f"{nresult.value} similar tile pairs found")
```

### Spline Interpolation

Given two room snapshots (before, after), interpolate the state at time t+δ. Each tile's confidence and gradient are linearly interpolated by mu.

```python
before = make_tile_batch(n)
after = make_tile_batch(n)
result = (ctypes.c_int32 * n)()
lib.spline_interp(before, after, n, 0.5, result)
```

### Batch Gradient

Compute Δ between consecutive tiles — the drift signal for forest floor monitoring.

```python
grads = (ctypes.c_int32 * n)()
lib.batch_gradient(tiles, n, grads)
```

### Physics Self-Report

The library declares its own performance characteristics — the "assembly port declares its physics" principle.

```python
lat, flops, simd = ctypes.c_float(0), ctypes.c_float(0), ctypes.c_int32(0)
lib.get_physics(ctypes.byref(lat), ctypes.byref(flops), ctypes.byref(simd))
print(f"Latency: {lat.value}ns, FLOPS: {flops.value}, SIMD: {simd.value}bit")
```

## Integrating with the Mycelium Bridge

The bridge loads the Fortran library at startup and routes compute-heavy operations to it:

```
Python bridge (:4080)
    │
    ├── /tile REST endpoint          ← text processing
    ├── /route cross-layer           ← routing logic
    └── libplato_math.so            ← tensor contractions (Fortran, 400M/s)
```

The bridge falls back to Python for control flow. But when two rooms need to be contracted (the core PLATO operation), it calls Fortran. Same 24-bit tile format, same data layout.

## Performance Notes

- **ARM64 NEON:** 399M checks/sec (this test)
- **x86 AVX-512:** Estimated 5-10B checks/sec (10-25x faster)
- **GPU CUDA:** Estimated 50-100B checks/sec (125-250x faster)
- **Fortran × 1 core ≈ Python × 1000 cores** for this operation

The 24-bit tile format is designed for this: each tile fits in a single 32-bit register. Pack 16 tiles per SIMD vector (ARM64 NEON) or 32 tiles per vector (x86 AVX-512). The Fortran compiler auto-vectorizes the inner loop.
