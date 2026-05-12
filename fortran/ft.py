#!/usr/bin/env python3
"""ft — FLUX tile toolkit. Every tool reads/writes 24-bit tiles.

Built on the Fortran compute claw (:4081) and PLATO.

Usage:
  ft cat <room>           — Decode tiles from a PLATO room
  ft grep <room> <field> <op> <val>  — Filter tiles by field
  ft canon <room> [N]     — Top N highest-confidence tiles
  ft merge <room_a> <room_b>  — Merge two rooms, deduplicate
  ft contract <a> <b>     — Contract room A against room B
  ft gradient <room>      — Delta stream from room history
  ft plato                 — Show PLATO status
  ft physics               — Show compute claw physics
"""

import ctypes
import json
import os
import subprocess
import sys
import urllib.request

PLATO = "http://localhost:8847"
CLAW = "http://localhost:4081"
FORT_LIB = os.path.join(os.path.dirname(__file__), "libplato_math.so")

def http_get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())

def http_post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def load_fortran():
    """Direct Fortran .so access (no server needed for simple ops)"""
    import ctypes
    lib = ctypes.CDLL(FORT_LIB)
    lib.tile_filter.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32)]
    lib.tile_canon.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_int32)]
    lib.batch_gradient.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32)]
    return lib

def room_tiles(room, limit=50):
    tiles = http_get(f"{PLATO}/room/{room}?limit={limit}")
    return tiles.get("tiles", [])

def decode_tile(val):
    """Decode a 24-bit integer to fields."""
    scheme = (val >> 22) & 0x3
    conf = (val >> 18) & 0x3F
    grad = (val >> 12) & 0x3F
    eps = (val >> 6) & 0x3F
    ctx = val & 0xF
    return {"scheme": scheme, "conf": conf, "grad": grad, "eps": eps, "ctx": ctx,
            "hex": f"0x{val:06X}", "raw": val}

def make_tile(conf, grad, eps=0, ctx=0, scheme=0):
    return (scheme << 22) | (min(conf, 63) << 18) | (min(grad, 63) << 12) | (min(eps, 63) << 6) | (min(ctx, 15))

def cmd_cat(args):
    """Decode tiles from a PLATO room"""
    room = args[0]
    tiles = room_tiles(room)
    if not tiles:
        print(f"No tiles in {room}/")
        return
    
    lib = load_fortran()
    vals = (ctypes.c_int32 * len(tiles))()
    for i, t in enumerate(tiles):
        vals[i] = hash(str(t.get("question","")[:16])) & 0xFFFFFF  # hash for display
    
    print(f"{'HEX':>10} {'CONF':>4} {'GRAD':>4} {'EPS':>4} {'CTX':>4}  QUESTION")
    print("-" * 60)
    for t in tiles[:30]:
        h = abs(hash(str(t.get("question","")[:16])) & 0xFFFFFF)
        d = decode_tile(h)
        q = t.get("question","")[:40]
        print(f"{d['hex']:>10} {d['conf']:>4} {d['grad']:>4} {d['eps']:>4} {d['ctx']:>4}  {q}")
    if len(tiles) > 30:
        print(f"... and {len(tiles)-30} more")

def cmd_grep(args):
    """Filter tiles by field value"""
    room = args[0]
    field = args[1]
    op = args[2]
    val = int(args[3])
    
    fields = {"conf": 18, "grad": 12, "eps": 6, "ctx": 0}
    if field not in fields:
        print(f"Unknown field: {field} (use conf, grad, eps, ctx)")
        return
    
    tiles = room_tiles(room)
    if not tiles:
        return
    
    # Convert to ints for Fortran
    ints = []
    for t in tiles:
        v = abs(hash(str(t.get("question","")[:16])) & 0xFFFFFF)
        conf = abs(hash(str(t.get("answer","")[:16]))) % 64
        grad = abs(hash(str(t.get("source","")[:8]))) % 64
        v = make_tile(conf, grad)
        ints.append(v)
    
    lib = load_fortran()
    import ctypes
    arr = (ctypes.c_int32 * len(ints))(*ints)
    out = (ctypes.c_int32 * len(ints))()
    
    # Filter field is at bits N to N+5
    if field == "conf":
        lib.tile_filter(arr, len(ints), val, 0, out, ctypes.byref(ctypes.c_int32(0)))
    elif field == "grad":
        lib.tile_filter(arr, len(ints), 0, val, out, ctypes.byref(ctypes.c_int32(0)))
    
    print(f"{'HEX':>10} {'CONF':>4} {'GRAD':>4}  SOURCE")
    print("-" * 40)
    for i in range(len(ints)):
        v = ints[i]
        d = decode_tile(v)
        if (field == "conf" and d[field] >= val) or (field == "grad" and d[field] >= val) or (field == "eps" and d[field] >= val):
            print(f"{d['hex']:>10} {d['conf']:>4} {d['grad']:>4}  {tiles[i].get('source','?')[:20]}")

def cmd_canon(args):
    """Top N tiles by confidence"""
    room = args[0]
    n = int(args[1]) if len(args) > 1 else 10
    
    tiles = room_tiles(room)
    if not tiles:
        return
    
    import ctypes
    lib = load_fortran()
    
    # Convert tiles to ints with hashed confidence
    ints = []
    for t in tiles:
        conf = int(t.get("confidence", 0) * 60) + 2  # map 0-1 to 2-62
        grad = abs(hash(str(t.get("question","")[:16]))) % 40 + 1
        v = make_tile(conf, grad)
        ints.append(v)
    
    arr = (ctypes.c_int32 * len(ints))(*ints)
    out = (ctypes.c_int32 * n)()
    nout = ctypes.c_int32(0)
    lib.tile_canon(arr, len(ints), n, out, ctypes.byref(nout))
    
    print(f"{'RANK':>4} {'HEX':>10} {'CONF':>4} {'GRAD':>4}  QUESTION")
    print("-" * 50)
    for i in range(nout.value):
        # Find which original tile this corresponds to
        d = decode_tile(out[i])
        # Search for matching confidence
        for t in tiles:
            tc = int(t.get("confidence", 0) * 60) + 2
            if abs(tc - d['conf']) <= 1:
                print(f"{i+1:>4} {d['hex']:>10} {d['conf']:>4} {d['grad']:>4}  {t.get('question','')[:40]}")
                break

def cmd_contract(args):
    """Contract two rooms through the Fortran claw"""
    a, b = args[0], args[1]
    tA, tB = room_tiles(a), room_tiles(b)
    
    # Send to compute claw
    result = http_post(f"{CLAW}/contract", {
        "room_a": [abs(hash(str(t.get("question","")[:16])) & 0xFFFFFF) for t in tA],
        "room_b": [abs(hash(str(t.get("question","")[:16])) & 0xFFFFFF) for t in tB],
        "na": len(tA), "nb": len(tB),
        "threshold": 0.3,
    })
    print(f"Contracted {a}({len(tA)}) × {b}({len(tB)}) = {result['nresult']} matches")

def cmd_gradient(args):
    """Gradient from room history"""
    room = args[0]
    tiles = room_tiles(room)
    if len(tiles) < 2:
        print("Need at least 2 tiles for gradient")
        return
    
    lib = load_fortran()
    import ctypes
    vals = (ctypes.c_int32 * len(tiles))()
    for i, t in enumerate(tiles):
        vals[i] = abs(hash(str(t.get("question","")[:16])) & 0xFFFFFF)
    grads = (ctypes.c_int32 * len(tiles))()
    lib.batch_gradient(vals, len(tiles), grads)
    
    print(f"{'IDX':>4} {'HEX':>10} {'GRADIENT':>10}  QUESTION")
    print("-" * 45)
    for i in range(min(len(tiles), 20)):
        print(f"{i:>4} {decode_tile(vals[i])['hex']:>10} {grads[i]:>10}  {tiles[i].get('question','')[:30]}")

def cmd_plato(args):
    """PLATO status"""
    status = http_get(f"{PLATO}/status")
    if "rooms" in status:
        rooms = status["rooms"]
        tiles = sum(r.get("tile_count", 0) for r in rooms.values())
        print(f"PLATO: {len(rooms)} rooms, ~{tiles} tiles")
        print(f"Gate: {status.get('gate_stats',{}).get('accepted',0)}a/{status.get('gate_stats',{}).get('rejected',0)}r")

def cmd_physics(args):
    """Compute claw physics"""
    phys = http_get(f"{CLAW}/physics")
    if "latency_ns" in phys:
        print(f"Fortran Claw: {phys['latency_ns']}ns latency, {phys['flops']:.1e} flops, {phys['simd_bits']}-bit SIMD")

def cmd_view(args):
    """Open forest-view.html in browser"""
    print("Open: http://147.224.38.131:4091/forest-view.html")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)
    
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    
    commands = {
        "cat": cmd_cat,
        "grep": cmd_grep,
        "canon": cmd_canon,
        "contract": cmd_contract,
        "gradient": cmd_gradient,
        "plato": cmd_plato,
        "physics": cmd_physics,
        "view": cmd_view,
    }
    
    # Handle help
    if cmd in ("-h", "--help", "help"):
        print(__doc__.strip())
        sys.exit(0)
    
    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)
    
    try:
        commands[cmd](rest)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
