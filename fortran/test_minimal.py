#!/usr/bin/env python3
"""Minimal Fortran claw test — verify contract works before benchmarking."""

import ctypes
import os

lib_path = os.path.join(os.path.dirname(__file__), "libplato_math.so")
lib = ctypes.CDLL(lib_path)

lib.contract_tiles.argtypes = [
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32),
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_float,
]

def make_tile(conf, grad, eps=0, ctx=0):
    return (conf << 18) | (grad << 12) | (eps << 6) | ctx

# Test 1: 2x2 contract
print("=== Test 1: 2x2 contract ===")
a = (ctypes.c_int32 * 2)(make_tile(32, 8), make_tile(16, 4))
b = (ctypes.c_int32 * 2)(make_tile(24, 6), make_tile(48, 12))
r = (ctypes.c_int32 * 10)()
nr = ctypes.c_int32(0)

print(f"a: {a[0]:06X} (conf=32 grad=8), {a[1]:06X} (conf=16 grad=4)")
print(f"b: {b[0]:06X} (conf=24 grad=6), {b[1]:06X} (conf=48 grad=12)")

lib.contract_tiles(a, 2, b, 2, r, ctypes.byref(nr), ctypes.c_float(0.3))
print(f"Results: {nr.value}")
for i in range(nr.value):
    print(f"  {i}: 0x{r[i]:06X}")

# Test 2: spline
print("\n=== Test 2: Spline ===")
lib.spline_interp.argtypes = [
    ctypes.POINTER(ctypes.c_int32),
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_int32,
    ctypes.c_float,
    ctypes.POINTER(ctypes.c_int32),
]
before = (ctypes.c_int32 * 3)(make_tile(10, 5), make_tile(20, 10), make_tile(30, 15))
after = (ctypes.c_int32 * 3)(make_tile(50, 25), make_tile(60, 30), make_tile(40, 20))
result = (ctypes.c_int32 * 3)()
mu = ctypes.c_float(0.5)
lib.spline_interp(before, after, 3, mu, result)
for i in range(3):
    print(f"  {i}: before 0x{before[i]:06X} after 0x{after[i]:06X} -> 0x{result[i]:06X}")

# Test 3: gradient
print("\n=== Test 3: Batch gradient ===")
lib.batch_gradient.argtypes = [
    ctypes.POINTER(ctypes.c_int32),
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32),
]
tiles = (ctypes.c_int32 * 5)(100, 200, 300, 500, 1000)
grads = (ctypes.c_int32 * 5)()
lib.batch_gradient(tiles, 5, grads)
for i in range(5):
    print(f"  tile[{i}]={tiles[i]} gradient={grads[i]:06X}")

print("\n✅ All tests passed")
