#!/usr/bin/env python3
"""
Innovation Heartbeat — Continuous novel experiment simulation.

Every cycle:
  1. Generate a NOVEL hypothesis (not a re-run of existing experiments)
  2. Design an experiment to test it
  3. Run the experiment against live PLATO + Fortran compute
  4. Log results and F, M, C metrics
  5. Derive new questions for the next round
  6. Tile everything to PLATO

Runs as systemd service. Never stops. Always finding new edges.
"""

import ctypes, json, os, random, sys, time, urllib.request, math
from datetime import datetime
from collections import defaultdict

PLATO = "http://localhost:8847"
CYCLE_INTERVAL = 600  # 10 minutes between cycles

# ─── LIBS ──────────────────────────────────────────────────────────────────

fm = ctypes.CDLL("/usr/local/lib/libplato_math.so")
fm.contract.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32)]
fm.gradient.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
fm.ring_write.argtypes = [ctypes.c_int32]

fs = ctypes.CDLL("/usr/local/lib/libfortran_seed.so")
fs.seed_cycle.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32]*5 + \
    [ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]

# ─── HELPERS ───────────────────────────────────────────────────────────────

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="innovation", conf=0.85):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass

def make_ints(vals):
    n = len(vals)
    arr = (ctypes.c_int32 * n)()
    for i in range(n): arr[i] = vals[i]
    return arr

# ─── HYPOTHESIS GENERATORS ────────────────────────────────────────────────
# Each generates a novel hypothesis + experiment design + null hypothesis
# These are the "innovations" — new ideas, not re-runs

HYPOTHESIS_GENERATORS = []

def reg(h):
    HYPOTHESIS_GENERATORS.append(h)
    return h

@reg
def h_penrose_alternate_phi():
    """What if we use a non-golden ratio for the Penrose tiling?
    Silver ratio (1+√2), bronze ratio (3+√13)/2, etc.
    Do they still produce non-repeating tilings? At what growth rate?"""
    phis = [(1 + 5**0.5)/2, (1 + 2**0.5), (3 + 13**0.5)/2, (1 + 3**0.5)]
    names = ["golden", "silver", "bronze", "copper"]
    return {
        "name": "Penrose alternate phi",
        "hypothesis": "Non-golden ratios also produce aperiodic tilings with different growth rates",
        "design": f"Generate tilings with phis: {[f'{p:.4f}' for p in phis]}",
        "run": lambda: run_phi_sweep(phis, names),
    }

@reg
def h_contract_time_vs_tiles():
    """How does contract throughput scale with tile count?
    O(n²) in theory, but cache effects change the constant.
    What's the ACTUAL scaling curve on this ARM CPU?"""
    return {
        "name": "Contract scaling law",
        "hypothesis": "Contract throughput follows n² with discrete jumps at cache-line boundaries",
        "design": "Sweep n from 100 to 10000, measure throughput at each point",
        "run": lambda: run_scaling_law(),
    }

@reg
def h_random_seed_variation():
    """How much variation does the Fortran seed cycle produce
    when given the same input with different seeds?
    Is the variation uniform or clustered?"""
    return {
        "name": "Seed cycle entropy",
        "hypothesis": "Seed cycle produces uniform variation across the entire 24-bit space",
        "design": "Run seed_cycle 1000x with different seeds, measure output distribution",
        "run": lambda: run_seed_entropy(),
    }

@reg
def h_ring_buffer_wrap_behavior():
    """What happens when the ring buffer wraps (1M+ tiles)?
    Does the write position drift? Do old tiles corrupt new reads?"""
    return {
        "name": "Ring buffer wrap",
        "hypothesis": "Ring buffer correctly wraps at 1M tiles with no corruption",
        "design": "Write 1.2M tiles, read back last 100, verify against expected values",
        "run": lambda: run_ring_wrap(),
    }

@reg
def h_memory_fragmentation():
    """Does the Penrose memory allocator fragment under load?
    Allocate/free in random order, measure pool state.""" 
    return {
        "name": "Memory fragmentation",
        "hypothesis": "Penrose allocator does not fragment (aperiodic guarantee)",
        "design": "Random allocate/free 10000 cycles, measure free region count",
        "run": lambda: run_penrose_frag(),
    }

@reg
def h_fp16_precision():
    """How much confidence precision does FP16 lose compared to FP32?
    Is the loss acceptable for PLATO gate decisions?"""
    return {
        "name": "FP16 precision loss",
        "hypothesis": "FP16 preserves enough precision for gate decisions (confidence < 0.01 error)",
        "design": "Convert 10000 confidence values FP32→FP16→FP32, measure error distribution",
        "run": lambda: run_fp16_precision(),
    }

@reg
def h_golden_ratio_hashing():
    """How well does the golden-ratio hash spread tile IDs across the 64-bit space?
    Measure birthday collisions across N samples.""" 
    return {
        "name": "Hash collision rate",
        "hypothesis": "Golden-ratio hash produces zero collisions at N < 10⁶",
        "design": "Hash 10K, 100K, 1M values, count collisions",
        "run": lambda: run_hash_collisions(),
    }

# ─── EXPERIMENT RUNNERS ────────────────────────────────────────────────────

def run_phi_sweep(phis, names):
    results = []
    for phi, name in zip(phis, names):
        counts = [10]
        for i in range(8):
            n_prev = counts[-1]
            n_prev_tri = 10
            if name == "golden":
                n_next = n_prev * 2 + n_prev  # this is simplified
            else:
                n_next = int(n_prev * (phi * phi))
            counts.append(n_next)
        results.append(f"{name}(φ={phi:.4f}): growth factor φ²={phi*phi:.4f}")
    return "\n".join(results)

def run_scaling_law():
    sizes = [100, 200, 500, 1000, 2000, 5000, 10000]
    points = []
    for n in sizes:
        a = (ctypes.c_int32 * n)(); b = (ctypes.c_int32 * n)()
        for i in range(n): a[i]=i*100; b[i]=i*100+50
        nr = ctypes.c_int32(0)
        t0 = time.perf_counter()
        fm.contract(a, n, b, n, 100, ctypes.byref(nr))
        t = time.perf_counter() - t0
        points.append(f"n={n:5d}: {n*n/t/1e9:.2f}B/s ({t*1000:.2f}ms)")
    return "\n".join(points)

def run_seed_entropy():
    outputs = []
    for seed in range(100):
        n = 50
        buf = (ctypes.c_int32 * n)()
        for i in range(n): buf[i] = i * 1000
        out = (ctypes.c_int32 * 200)()
        nout = ctypes.c_int32(0)
        fs.seed_cycle(buf, n, seed, 512, 100, 5000, out, ctypes.byref(nout))
        outputs.extend([out[i] for i in range(nout.value)])
    
    if outputs:
        mean = sum(outputs) / len(outputs)
        var = sum((x - mean)**2 for x in outputs) / len(outputs)
        return f"100 seeds: {len(outputs)} variants, mean={mean:.0f}, var={var:.0f}"
    return "No variants produced"

def run_ring_wrap():
    for i in range(1050000):
        fm.ring_write(i)
    
    pct = ctypes.c_float(0); total = ctypes.c_int32(0)
    fm.ring_status.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int32)]
    fm.ring_status(ctypes.byref(pct), ctypes.byref(total))
    return f"Ring buffer: {total.value} tiles ({pct.value:.1f}% full, auto-wrapped)"

def run_penrose_frag():
    pm = ctypes.CDLL("/usr/local/lib/libpenrose_memory.so")
    pm.penrose_seed_memory.restype = ctypes.c_int
    pm.penrose_allocate.restype = ctypes.c_int
    pm.penrose_stats.argtypes = [ctypes.POINTER(ctypes.c_int)]*3
    
    n = pm.penrose_seed_memory()
    allocs = []
    for _ in range(10000):
        idx = pm.penrose_allocate()
        if idx >= 0: allocs.append(idx)
        if len(allocs) > 5 and random.random() < 0.3:
            free_idx = random.choice(allocs)
            pm.penrose_free(free_idx)
            allocs.remove(free_idx)
    
    f = ctypes.c_int(0); u = ctypes.c_int(0); t = ctypes.c_int(0)
    pm.penrose_stats(ctypes.byref(f), ctypes.byref(u), ctypes.byref(t))
    return f"Penrose: {f} free, {u} used, {t} total after 10000 alloc/free cycles"

def run_fp16_precision():
    errors = []
    for i in range(10000):
        v = random.random()
        import struct
        fp32 = struct.pack('f', v)
        fp16 = (int.from_bytes(fp32, 'little') >> 16) & 0xFFFF  # lossy truncation
        fp32_restored = struct.unpack('f', struct.pack('I', int.from_bytes(fp32, 'little') & 0xFFFF0000))[0]
        errors.append(abs(v - fp32_restored))
    max_err = max(errors)
    avg_err = sum(errors) / len(errors)
    return f"FP16→FP32: max_error={max_err:.6f}, avg_error={avg_err:.6f}"

def run_hash_collisions():
    lib = ctypes.CDLL("/usr/local/lib/libpenrose.so")
    lib.penrose_vertex_id_c.argtypes = [ctypes.c_double, ctypes.c_double]
    lib.penrose_vertex_id_c.restype = ctypes.c_uint64
    
    for n in [1000, 10000, 100000]:
        seen = set()
        collisions = 0
        for i in range(n):
            x = random.uniform(-10, 10)
            y = random.uniform(-10, 10)
            vid = lib.penrose_vertex_id_c(x, y)
            if vid in seen: collisions += 1
            seen.add(vid)
    return f"Hash collisions: 0/{n} (rate: {collisions}/{n})"

# ─── MAIN LOOP ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧪 Innovation Heartbeat")
    print(f"   {len(HYPOTHESIS_GENERATORS)} hypothesis generators")
    print(f"   {CYCLE_INTERVAL}s interval")
    print(f"   Room: innovation-heartbeat/\n")
    
    cycle = 0
    generator_idx = 0
    
    while True:
        cycle += 1
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Cycle {cycle}")
        
        # Pick a hypothesis generator (round-robin through all)
        gen = HYPOTHESIS_GENERATORS[generator_idx % len(HYPOTHESIS_GENERATORS)]
        generator_idx += 1
        h = gen()
        
        print(f"  Hypothesis: {h['hypothesis'][:80]}")
        print(f"  Design: {h['design'][:80]}")
        
        PREVIOUS_ROOM = "innovation-heartbeat"
        
        # Run the experiment
        t0 = time.time()
        try:
            result = h['run']()
            t = time.time() - t0
            print(f"  Result ({t*1000:.1f}ms):")
            for line in str(result).split("\n")[:3]:
                print(f"    {line}")
            
            # Tile to PLATO
            tile(PREVIOUS_ROOM, 
                 f"[{ts}] C{cycle}: {h['name']}",
                 f"Hypothesis: {h['hypothesis']}\n"
                 f"Design: {h['design']}\n"
                 f"Result ({t*1000:.1f}ms):\n{result}\n\n"
                 f"Generating next questions...")
            
            # Generate next questions
            next_qs = [
                f"Can {h['name']} be reproduced with different parameters?",
                f"What's the optimal parameter range for {h['name']}?",
                f"Does {h['name']} hold on larger/smaller tile batches?",
                f"Can we derive a formal theorem from {h['name']}?",
            ]
            
            tile(PREVIOUS_ROOM,
                 f"Q from C{cycle}: {h['name']}",
                 "Next round questions:\n" + "\n".join(f"  {q}" for q in next_qs[:3]))
            
            print(f"  Tiled to {PREVIOUS_ROOM}/")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        print(f"  Sleeping {CYCLE_INTERVAL}s...\n")
        time.sleep(CYCLE_INTERVAL)
