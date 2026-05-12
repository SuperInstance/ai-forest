#!/usr/bin/env python3
"""Benchmark Fortran vs Python for tile contractions."""

import ctypes
import time
import sys
import os

# Load Fortran shared library
lib_path = os.path.join(os.path.dirname(__file__), "libplato_math.so")
lib = ctypes.CDLL(lib_path)

# Type signatures
lib.contract_tiles.argtypes = [
    ctypes.POINTER(ctypes.c_int32),  # room_a
    ctypes.c_int32,                   # na
    ctypes.POINTER(ctypes.c_int32),  # room_b
    ctypes.c_int32,                   # nb
    ctypes.POINTER(ctypes.c_int32),  # result
    ctypes.POINTER(ctypes.c_int32),  # nresult
    ctypes.c_float,                   # threshold
]

lib.spline_interp.argtypes = [
    ctypes.POINTER(ctypes.c_int32),
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_int32,
    ctypes.c_float,
    ctypes.POINTER(ctypes.c_int32),
]

lib.batch_gradient.argtypes = [
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32),
]

lib.get_physics.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_int32),
]

def make_tile_batch(n: int) -> ctypes.Array[ctypes.c_int32]:
    """Create n tiles with varying confidence/gradient"""
    arr = (ctypes.c_int32 * n)()
    for i in range(n):
        conf = (i * 7) % 64
        grad = (i * 13) % 64
        eps = (i * 3) % 16
        ctx = i % 8
        arr[i] = (conf << 18) | (grad << 12) | (eps << 6) | ctx
    return arr

print("=" * 60)
print("Fortran Compute Claw — Benchmark")
print("=" * 60)

# 1. Physics report
lat = ctypes.c_float(0)
flops = ctypes.c_float(0)
simd = ctypes.c_int32(0)
lib.get_physics(ctypes.byref(lat), ctypes.byref(flops), ctypes.byref(simd))
print(f"\n📋 Physics declaration:")
print(f"   Latency: {lat.value:.0f}ns")
print(f"   FLOPS:   {flops.value:.1e}")
print(f"   SIMD:    {simd.value}-bit")

# 2. Contract benchmark
for n in [100, 1000, 5000, 10000]:
    a = make_tile_batch(n)
    b = make_tile_batch(n)
    r = (ctypes.c_int32 * (n * n))()
    nr = ctypes.c_int32(0)
    
    t0 = time.time()
    lib.contract_tiles(a, n, b, n, r, ctypes.byref(nr), ctypes.c_float(0.3))
    dt = time.time() - t0
    
    ops = n * n  # each pair checked
    if dt > 0:
        print(f"\n   📊 {n}x{n} tiles: {dt*1000:.1f}ms, {nr.value} above threshold")
        print(f"      Throughput: {ops/dt/1e6:.0f}M checks/sec")

# 3. Spline benchmark
print("\n\n📊 Spline interpolation:")
for n in [10000, 100000]:
    before = make_tile_batch(n)
    after = make_tile_batch(n)
    result = (ctypes.c_int32 * n)()
    mu = ctypes.c_float(0.3)
    
    t0 = time.time()
    lib.spline_interp(before, after, n, mu, result)
    dt = time.time() - t0
    print(f"   {n} tiles: {dt*1000:.3f}ms ({n/dt/1e6:.0f}M tiles/sec)")

# 4. Gradient benchmark
print("\n\n📊 Batch gradient:")
for n in [10000, 100000]:
    tiles = make_tile_batch(n)
    grads = (ctypes.c_int32 * n)()
    
    t0 = time.time()
    lib.batch_gradient(tiles, n, grads)
    dt = time.time() - t0
    print(f"   {n} tiles: {dt*1000:.3f}ms ({n/dt/1e6:.0f}M tiles/sec)")

print("\n" + "=" * 60)
print("✅ Benchmarks complete")
print("=" * 60)
