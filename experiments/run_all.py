#!/usr/bin/env python3
"""Experiment Suite — Validating the Adjunction Framework Empirically"""

import json, os, sys, time, urllib.request, random, math
import ctypes

PLATO = "http://localhost:8847"

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def load_fortran():
    lib = ctypes.CDLL("/usr/local/lib/libplato_math.so")
    lib.contract.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32)]
    lib.gradient.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32)]
    lib.window_contract.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
    return lib

def exp1_threshold_sweep():
    print("\nEXP 1: Threshold θ Sweep — Adjunction Monotonicity")
    lib = load_fortran()
    n = 100
    a = (ctypes.c_int32 * n)(); b = (ctypes.c_int32 * n)()
    for i in range(n): a[i] = random.randint(0, 10000); b[i] = random.randint(0, 10000)
    results = []
    for theta in [0, 10, 50, 100, 500, 1000, 5000]:
        nr = ctypes.c_int32(0); t0 = time.time()
        lib.contract(a, n, b, n, theta, ctypes.byref(nr))
        results.append((theta, nr.value, time.time() - t0))
        print(f"  θ={theta:5d} → {nr.value:5d} results")
    monotonic = all(results[i][1] >= results[i+1][1] for i in range(len(results)-1))
    print(f"  Monotonic: {'PASS' if monotonic else 'FAIL'}")

def exp2_context_window():
    print("\nEXP 2: Context Window — Blind-width vs Signal Coherence")
    tiles = fetch(f"/room/tension?limit=100").get("tiles", [])
    total = len(tiles); lib = load_fortran()
    vals = (ctypes.c_int32 * total)()
    for i, t in enumerate(tiles): vals[i] = abs(hash(str(t.get("question",""))[:16])) & 0x7FFFFFFF
    print(f"  tension/: {total} tiles")
    for pct in [10, 25, 50, 68, 75, 90, 100]:
        n = max(2, total * pct // 100)
        g = (ctypes.c_int32 * n)()
        sub = (ctypes.c_int32 * n)(); import copy; ctypes.memmove(sub, vals, n * 4); t0 = time.time(); lib.gradient(sub, n, g); dt = time.time() - t0
        avg = sum(g[i] for i in range(n)) / max(n, 1)
        print(f"  B={pct:3d}% ({n:3d} tiles): avg_grad={avg:10.0f} ({dt*1000:.1f}ms)")

def exp3_recency_decay():
    print("\nEXP 3: Recency Decay — Weight Function Comparison")
    n = 200
    for label, fn in [
        ("1/(1+age)", lambda a: 1.0/(1.0+a)),
        ("exp(-age/5)", lambda a: math.exp(-a/5)),
        ("exp(-age/10)", lambda a: math.exp(-a/10)),
        ("linear", lambda a: max(0, 1-a/n)),
    ]:
        w = [fn(i/max(n,1)*10) for i in range(n)]
        total_w = sum(w)
        eff = total_w / max(max(w), 0.001)
        norm = [wi/total_w for wi in w]
        ent = -sum(wi * math.log(wi + 1e-10) for wi in norm)
        print(f"  {label:15s}: effective={eff:.1f} tiles, entropy={ent:.3f}")

def exp4_temporal_window():
    print("\nEXP 4: Temporal Window — window_contract θ Sweep")
    lib = load_fortran(); n = 50
    ta = (ctypes.c_int32 * n)(); va = (ctypes.c_int32 * n)()
    tb = (ctypes.c_int32 * n)(); vb = (ctypes.c_int32 * n)()
    for i in range(n): ta[i]=i; va[i]=i*100+50; tb[i]=i+25; vb[i]=i*100+100
    for w in [0, 5, 10, 25, 50, 100]:
        nr = ctypes.c_int32(0); lib.window_contract(ta,va,n,tb,vb,n,w,50,ctypes.byref(nr))
        print(f"  window={w:3d} → {nr.value:5d} matches")

def exp5_gate_stats():
    print("\nEXP 5: PLATO Gate — θ as Confidence Threshold")
    s = fetch("/status")
    gate = s.get("gate_stats", {})
    rooms = s.get("rooms", {})
    total = sum(r.get("tile_count",0) for r in rooms.values())
    print(f"  Gate: {gate.get('accepted',0)}a/{gate.get('rejected',0)}r")
    print(f"  PLATO: {len(rooms)} rooms, ~{total} tiles")

def exp6_cross_language():
    print("\nEXP 6: Cross-Language Consistency")
    lib = load_fortran()
    zlib = ctypes.CDLL("/usr/local/lib/libft_zig.so")
    zlib.ft_contract.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32]
    zlib.ft_contract.restype = ctypes.c_int32
    n = 50; a = (ctypes.c_int32 * n)(); b = (ctypes.c_int32 * n)()
    for i in range(n): a[i]=i*100; b[i]=i*100+50
    for t in [10, 50, 100, 500]:
        nrf = ctypes.c_int32(0); lib.contract(a,n,b,n,t,ctypes.byref(nrf))
        nrz = zlib.ft_contract(a,n,b,n,t)
        print(f"  θ={t:4d}: Fortran={nrf.value:5d} Zig={nrz:5d} {'OK' if nrf.value==nrz else 'MISMATCH'}")

if __name__ == "__main__":
    print("ADJUNCTION EXPERIMENT SUITE")
    exp1_threshold_sweep()
    exp2_context_window()
    exp3_recency_decay()
    exp4_temporal_window()
    exp5_gate_stats()
    exp6_cross_language()
    print("\nDone.")
