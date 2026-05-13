#!/usr/bin/env python3
"""
Question Seeder — After experiments, seed models generate the next questions.

Reads experiment results from PLATO, analyzes patterns using Fortran compute,
generates new questions that become the next experiment phase.
The system decides what to investigate next.
"""

import ctypes, json, os, sys, time, urllib.request, random
from datetime import datetime

PLATO = "http://localhost:8847"
lib = ctypes.CDLL("/usr/local/lib/libplato_math.so")
lib.contract.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32)]
lib.gradient.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32)]

SEED_ROOM = "question-seeds"

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="question-seeder", conf=0.9):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass

def analyze_experiment_results():
    """Read experiment rooms, compute gradients, find anomalies.
    
    The gradient of experiment results over time tells us:
    - HIGH gradient = something changed → question: why?
    - LOW gradient = stable → question: is this settled?
    - ZERO gradient = no data → question: what's missing?
    """
    experiment_rooms = ["fleet-experiments", "calibration", "waveform-experiments",
                         "cooperation-experiments", "novel-science", "swarm-insights"]
    
    questions = []
    
    for room in experiment_rooms:
        tiles = fetch(f"/room/{room}?limit=50").get("tiles", [])
        if len(tiles) < 3:
            continue
        
        n = len(tiles)
        vals = (ctypes.c_int32 * n)()
        for i, t in enumerate(tiles):
            vals[i] = abs(hash(str(t.get("answer",""))[:32])) & 0x7FFFFFFF
        
        grads = (ctypes.c_int32 * n)()
        lib.gradient(vals, n, grads)
        
        avg_grad = sum(grads) // max(n, 1)
        max_grad = max(grads)
        
        # Classify: high signal = something changed
        signal_type = "high_change" if max_grad > 10000000 else "stable" if avg_grad < 1000000 else "moderate"
        
        # Generate questions based on signal type
        if signal_type == "high_change":
            questions.append(f"What changed in {room}/ — max gradient {max_grad} suggests a phase transition")
        elif signal_type == "stable":
            questions.append(f"Is {room}/ converged? — low gradient ({avg_grad}) suggests stability")
        else:
            questions.append(f"Moderate drift in {room}/ — gradient {avg_grad}, what drives it?")
        
        # Read the first and last tile — what changed?
        first_q = tiles[0].get("question", "")[:60] if tiles else ""
        last_q = tiles[-1].get("question", "")[:60] if tiles else ""
        
        if first_q and first_q != last_q:
            questions.append(f"Question evolution: '{first_q}' → '{last_q}' — did the topic shift?")
    
    return questions

def suggest_experiments(questions):
    """From questions, propose concrete experiments."""
    experiments = []
    
    for q in questions:
        if "phase transition" in q.lower():
            room = q.split("/")[0].split()[-1] if "/" in q else "unknown"
            experiments.append(f"Sweep α values across {room} to find the phase transition point")
        elif "converged" in q.lower():
            experiments.append("Run extended stability test — 24h without parameter changes")
        elif "gradient" in q.lower():
            experiments.append("Vary the forgetting curve τ parameter and measure gradient sensitivity")
        elif "topic shift" in q.lower():
            experiments.append("Cross-correlate question embeddings to detect topic drift")
        else:
            experiments.append(f"Investigate: {q[:40]}... with controlled parameter sweep")
    
    return experiments

def question_fortran_seed(questions):
    """Use Fortran seed cycle to generate variations of questions."""
    fs = ctypes.CDLL("/usr/local/lib/libfortran_seed.so")
    fs.seed_cycle.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32]*5 + \
        [ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]
    
    # Hash questions to numeric values for Fortran processing
    n = min(len(questions), 20)
    if n == 0: return questions
    
    vals = (ctypes.c_int32 * n)()
    for i in range(n):
        vals[i] = abs(hash(questions[i])) & 0xFFFFFF
    
    # Run seed cycle to generate variations (novelty from existing questions)
    out = (ctypes.c_int32 * 100)()
    nout = ctypes.c_int32(0)
    fs.seed_cycle(vals, n, int(time.time()), 512, 500, 5000, out, ctypes.byref(nout))
    
    # Map variations back to question-space
    varied = []
    for i in range(min(nout.value, 20)):
        # Use the variation as a hash offset to pick a related question
        idx = out[i] % max(n, 1)
        wall_clock = int(time.time()) % n
        varied.append(f"Variant {i}: {questions[idx]} (source: seed_cycle, θ={out[i] & 0xFF})")
    
    return varied + questions[:10]

if __name__ == "__main__":
    print("=" * 60)
    print("QUESTION SEEDER — After Experiments, New Questions")
    print("=" * 60)
    
    # Phase 1: Analyze experiment results
    print("\n1. Analyzing experiment results...")
    questions = analyze_experiment_results()
    print(f"   Generated {len(questions)} questions from experiment rooms")
    
    for q in questions:
        print(f"     ❓ {q[:70]}")
    
    # Phase 2: Propose experiments
    print("\n2. Proposing next experiments...")
    experiments = suggest_experiments(questions)
    for e in experiments:
        print(f"     🔬 {e[:70]}")
    
    # Phase 3: Fortran seed variation
    print("\n3. Fortran seed variations on questions...")
    varied = question_fortran_seed(questions)
    print(f"   {len(varied)} seed variations generated")
    
    # Phase 4: Write to PLATO
    print("\n4. Writing to PLATO...")
    ts = datetime.now().strftime("%H:%M")
    
    tile(SEED_ROOM, f"Question seed cycle {ts}",
         f"Generated {len(questions)} questions + {len(experiments)} experiments + {len(varied)} variations\n"
         f"Questions: {'; '.join(questions[:5])}\n"
         f"Experiments: {'; '.join(experiments[:5])}")
    
    for i, q in enumerate(questions):
        tile(SEED_ROOM, f"Q{i}: {q[:100]}",
             f"Source: experiment analysis, gradient-based anomaly detection", conf=0.7)
    
    for i, e in enumerate(experiments):
        tile(SEED_ROOM, f"Exp{i}: {e[:100]}",
             f"Proposed experiment derived from question analysis", conf=0.65)
    
    print(f"   Tiled to {SEED_ROOM}/")
    print(f"\n✅ Question seed cycle complete. Next round ready.")
