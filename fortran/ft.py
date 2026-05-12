#!/usr/bin/env python3
"""ft — PLATO compute toolkit. Native int32, no bit packing.

Built on Fortran native array operations + PLATO rooms.

Usage:
  ft plato               — PLATO server status
  ft physics             — Compute claw physics  
  ft contract <a> <b>    — Contract arrays through Fortran
  ft gradient <room>     — Gradient across room tile history
  ft spline <room> <mu>  — Interpolate room state forward
  ft cat <room>          — Read room tiles as native ints
  ft bench               — Benchmark Fortran compute paths
  ft help                — This help

Environment:
  PLATO_URL     (default: http://localhost:8847)
  CLAW_URL      (default: http://localhost:4081)
"""

import json, os, sys, time, urllib.request
PLATO = os.environ.get("PLATO_URL", "http://localhost:8847")
CLAW = os.environ.get("CLAW_URL", "http://localhost:4081")

def _fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def _claw_post(endpoint, data):
    req = urllib.request.Request(f"{CLAW}{endpoint}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def cmd_plato(args):
    s = _fetch("/status")
    rooms = s.get("rooms", {})
    tiles = sum(r.get("tile_count",0) for r in rooms.values())
    print(f"PLATO: {len(rooms)} rooms, ~{tiles} tiles")

def cmd_physics(args):
    try:
        with urllib.request.urlopen(f"{CLAW}/physics", timeout=5) as r:
            p = json.loads(r.read())
            print(f"Claw: {p.get('latency_ns')}ns, {p.get('flops'):.1e} flops, {p.get('simd_bits')}-bit SIMD")
    except:
        print("Claw not reachable at", CLAW)

def cmd_contract(args):
    if len(args) < 2: return print("Usage: ft contract <room_a> <room_b>")
    a_name, b_name = args[0], args[1]
    rooms = _fetch("/status").get("rooms", {})
    tiles_a = rooms.get(a_name, {}).get("tile_count", 0)
    tiles_b = rooms.get(b_name, {}).get("tile_count", 0)
    r = _claw_post("/contract", {"room_a": list(range(tiles_a)), "room_b": list(range(tiles_b)),
        "na": tiles_a, "nb": tiles_b, "threshold": int(args[2]) if len(args) > 2 else 100})
    print(f"Contracted {tiles_a}×{tiles_b}: {r.get('nresult',0)} pairs above threshold")

def cmd_gradient(args):
    if not args: return print("Usage: ft gradient <room>")
    room = args[0]
    tiles = _fetch(f"/room/{room}?limit=100").get("tiles", [])
    vals = [hash(str(t.get("question",""))[:16]) & 0x7FFFFFFF for t in tiles]
    r = _claw_post("/gradient", {"tiles": vals, "n": len(vals)})
    print(f"Gradient across {len(vals)} tiles")
    for i, g in enumerate(r.get("gradients",[])[:10]):
        print(f"  [{i}] Δ={g:8d}  {tiles[i].get('question','')[:40]}")

def cmd_spline(args):
    if len(args) < 1: return print("Usage: ft spline <room> [mu]")
    room, mu_s = args[0], args[1] if len(args) > 1 else "512"
    mu = int(mu_s)
    tiles = _fetch(f"/room/{room}?limit=50").get("tiles", [])
    vals = [hash(str(t.get("question",""))[:16]) & 0x7FFFFFFF for t in tiles]
    r = _claw_post("/spline", {"before": vals, "after": [v*2 for v in vals],
        "n": len(vals), "mu": mu})
    print(f"Spline {room} with mu={mu}/1024: {len(r.get('result',[]))} tiles interpolated")

def cmd_cat(args):
    if not args: return print("Usage: ft cat <room>")
    room = args[0]
    tiles = _fetch(f"/room/{room}?limit=30").get("tiles", [])
    if not tiles: return print(f"No tiles in {room}/")
    for i, t in enumerate(tiles):
        q = t.get("question","")[:60]
        val = hash(str(q)) & 0x7FFFFFFF
        print(f"  [{i:3d}] 0x{val:08X} = {val:10d}  {q}")

def cmd_bench(args):
    import ctypes
    lib = ctypes.CDLL("/tmp/ai-forest/fortran/libplato_math.so")
    for fn, na, nb in [("contract", 1000, 1000), ("contract", 5000, 5000)]:
        a = (ctypes.c_int32 * na)(); b = (ctypes.c_int32 * nb)()
        for i in range(na): a[i] = i * 1000
        for i in range(nb): b[i] = i * 1000 + 500
        nr = ctypes.c_int32(0)
        t0 = time.time()
        if fn == "contract":
            lib.contract(a, na, b, nb, ctypes.c_int32(10000), ctypes.byref(nr))
        dt = time.time() - t0
        print(f"  Contract {na}×{nb}: {dt*1000:.1f}ms ({na*nb/dt/1e6:.0f}M pairs/sec)")
    
    # Gradient
    for n in [10000, 100000]:
        a = (ctypes.c_int32 * n)()
        for i in range(n): a[i] = i * 100
        g = (ctypes.c_int32 * n)()
        t0 = time.time()
        lib.gradient(a, n, g)
        dt = time.time() - t0
        print(f"  Gradient {n}: {dt*1000:.3f}ms ({n/dt/1e6:.0f}M elem/sec)")

def cmd_zig(args):
    """Benchmark Zig compute path"""
    import time, ctypes
    lib = ctypes.CDLL("/tmp/ai-forest/zig/libft_zig.so")
    lib.ft_contract.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32]
    lib.ft_contract.restype = ctypes.c_int32
    for n in [1000, 5000]:
        a = (ctypes.c_int32 * n)(); b = (ctypes.c_int32 * n)()
        for i in range(n): a[i] = i * 1000; b[i] = i * 1000 + 500
        t0 = time.time()
        nr = lib.ft_contract(a, n, b, n, 10000)
        dt = time.time() - t0
        print(f"  Zig contract {n}x{n}: {dt*1000:.1f}ms ({n*n/dt/1e6:.0f}M pairs/sec)")

COMMANDS = {k.replace("cmd_",""): v for k,v in locals().items() if k.startswith("cmd_")}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h","--help","help"):
        print(__doc__)
        sys.exit(0)
    fn = COMMANDS.get(sys.argv[1])
    if not fn:
        print(f"Unknown: {sys.argv[1]}. Available: {', '.join(sorted(COMMANDS))}")
        sys.exit(1)
    fn(sys.argv[2:])
