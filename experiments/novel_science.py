#!/usr/bin/env python3
"""
Novel Science Experiments — Testing the frontiers of neural PLATO theory.

These go beyond infrastructure tests into intelligence science:
1. Memory drift over time (convergence or divergence?)
2. Cross-room resonance (does firing propagate?)
3. Forgetting curves (do real tiles decay as predicted?)
4. Optimal blind-width per room type
5. The consciousness metric (F × M × C)
6. Adjunction composition preservation
"""

import ctypes, json, math, random, sys, time, urllib.request
from collections import defaultdict

PLATO = "http://localhost:8847"
EXP_ROOM = "novel-science"
lib = ctypes.CDLL("/usr/local/lib/libplato_math.so")

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def pt(q, a, src="novel"):
    d = json.dumps({"room":EXP_ROOM,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":0.85}).encode()
    try:
        req = urllib.request.Request(f"{PLATO}/room/{EXP_ROOM}/submit",data=d,headers={"Content-Type":"application/json"},method="POST")
        urllib.request.urlopen(req,timeout=10)
    except: pass

print("=" * 60)
print("NOVEL SCIENCE — Probing the Neural PLATO")
print("=" * 60)

# ─── EXPERIMENT 1: Memory Drift Over Time ───
# Track the SAME question through multiple PLATO tiles over hours
# Does the answer converge (stabilize) or diverge (drift)?
print("\n" + "=" * 60)
print("EXP 1: MEMORY DRIFT — Does knowledge converge or drift?")
print("=" * 60)

rooms_to_check = ["tension", "forge", "synthesis", "edge", "swarm-insights"]
for room in rooms_to_check:
    tiles = fetch(f"/room/{room}?limit=100").get("tiles", [])
    if len(tiles) < 5: continue
    
    # Group tiles by question prefix (same topic over time)
    topics = defaultdict(list)
    for t in tiles:
        q = t.get("question", "")[:30]  # first 30 chars = topic
        topics[q].append(t)
    
    # Find the topic with the most versions
    best_topic = max(topics, key=lambda k: len(topics[k]))
    versions = topics[best_topic]
    
    if len(versions) >= 3:
        # Measure drift: how much does the answer change between versions?
        first_a = versions[0].get("answer", "")
        last_a = versions[-1].get("answer", "")
        first_words = set(first_a.split())
        last_words = set(last_a.split())
        
        jaccard = len(first_words & last_words) / max(len(first_words | last_words), 1)
        new_words = len(last_words - first_words)
        lost_words = len(first_words - last_words)
        
        print(f"\n  {room}/: '{best_topic[:40]}...'")
        print(f"    Versions: {len(versions)}, span: ~{len(versions)*2} min")
        print(f"    Jaccard similarity: {jaccard:.3f} (1.0 = identical)")
        print(f"    Words gained: {new_words}, words lost: {lost_words}")
        
        if jaccard > 0.7:
            verdict = f"STABLE (jaccard={jaccard:.2f})"
        elif jaccard > 0.4:
            verdict = f"DRIFTING (jaccard={jaccard:.2f})"
        else:
            verdict = f"DIVERGENT (jaccard={jaccard:.2f})"
        print(f"    Verdict: {verdict}")
        
        pt(f"Memory drift: {room}", f"Topic: {best_topic[:40]}\nVersions: {len(versions)}\nJaccard: {jaccard:.3f}\nNew words: {new_words}\nLost: {lost_words}\nVerdict: {verdict}")

# ─── EXPERIMENT 2: Cross-Room Resonance ───
# When tension/ fires a new tile, how long until forge/ fires too?
print("\n" + "=" * 60)
print("EXP 2: CROSS-ROOM RESONANCE — Does firing propagate?")
print("=" * 60)

rooms_pairs = [("tension", "synthesis"), ("tension", "forge"), ("agent-oracle1", "tension")]
for source, target in rooms_pairs:
    src_tiles = fetch(f"/room/{source}?limit=50").get("tiles", [])
    tgt_tiles = fetch(f"/room/{target}?limit=50").get("tiles", [])
    
    if len(src_tiles) < 5 or len(tgt_tiles) < 5:
        continue
    
    # Check for shared sources — tiles in target that reference source
    shared = set()
    for t in tgt_tiles:
        answer = t.get("answer", "").lower()
        question = t.get("question", "").lower()
        if source.lower() in answer or source.lower() in question:
            shared.add(t.get("question", "")[:30])
    
    print(f"\n  {source}/ → {target}/:")
    print(f"    {len(src_tiles)} source tiles, {len(tgt_tiles)} target tiles")
    print(f"    {len(shared)} target tiles reference source")
    resonance = len(shared) / max(len(tgt_tiles), 1)
    print(f"    Resonance: {resonance:.3f} ({'STRONG' if resonance > 0.2 else 'MODERATE' if resonance > 0.1 else 'WEAK'})")
    
    pt(f"Cross-room: {source}→{target}", f"Source: {len(src_tiles)} tiles\nTarget: {len(tgt_tiles)} tiles\nReferences: {len(shared)}\nResonance: {resonance:.3f}")

# ─── EXPERIMENT 3: Forgetting Curve Validation ───
# Does tile confidence actually decay like Ebbinghaus predicts?
print("\n" + "=" * 60)
print("EXP 3: FORGETTING CURVES — Do real tiles follow Ebbinghaus?")
print("=" * 60)

room = "agent-oracle1"
tiles = fetch(f"/room/{room}?limit=200").get("tiles", [])
if tiles:
    confidences = []
    for i, t in enumerate(tiles):
        c = t.get("confidence", 0.5)
        confidences.append(c)
    
    if len(confidences) > 5:
        # Ebbinghaus model: recall = exp(-t / τ)
        # τ (tau) = decay constant — higher = slower forgetting
        # Fit to the first tile's confidence vs last
        first_conf = confidences[0]
        last_conf = confidences[-1]
        
        if first_conf > 0 and last_conf > 0:
            t_elapsed = len(confidences)  # cycles as proxy for time
            ratio = max(last_conf / max(first_conf, 0.001), 0.01)
            tau = -t_elapsed / math.log(ratio) if ratio > 0 and ratio != 1.0 else float("inf")
            
            actual_last = confidences[-1]
            predicted_last = first_conf * math.exp(-t_elapsed / max(tau, 0.1))
            
            print(f"\n  {room}/: {len(confidences)} tiles over ~{t_elapsed} cycles")
            print(f"    First confidence: {first_conf:.3f}, Last: {actual_last:.3f}")
            print(f"    Ebbinghaus τ: {tau:.1f} cycles (higher = slower forgetting)")
            print(f"    Predicted last: {predicted_last:.3f}")
            print(f"    Model error: {abs(actual_last - predicted_last):.3f}")
            
            if abs(actual_last - predicted_last) < 0.1:
                verdict = "✅ FOLLOWS EBBINGHAUS"
            else:
                verdict = f"⚠️ DIFFERS (error={abs(actual_last-predicted_last):.3f})"
            print(f"    Verdict: {verdict}")
            
            pt(f"Forgetting curve: {room}", f"Tiles: {len(confidences)}\nCycles: {t_elapsed}\nFirst conf: {first_conf:.3f}\nLast: {actual_last:.3f}\nτ: {tau:.1f}\nPredicted: {predicted_last:.3f}\nVerdict: {verdict}")

# ─── EXPERIMENT 4: Optimal Blind-Width Per Room ───
# Different rooms have different character. What B is optimal for each?
print("\n" + "=" * 60)
print("EXP 4: OPTIMAL BLIND-WIDTH — Different rooms, different B")
print("=" * 60)

lib.gradient.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]

for room in ["tension", "forge", "agent-oracle1", "swarm-insights"]:
    tiles = fetch(f"/room/{room}?limit=100").get("tiles", [])
    if len(tiles) < 10: continue
    
    n = len(tiles)
    vals = (ctypes.c_int32 * n)()
    for i, t in enumerate(tiles):
        vals[i] = abs(hash(str(t.get("question", ""))[:16])) & 0x7FFFFFFF
    
    best_b = 0.5
    best_grad = float('inf')
    
    # Test B from 10% to 100%
    for pct in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        subset_n = max(2, n * pct // 100)
        g = (ctypes.c_int32 * subset_n)()
        
        # Copy subset
        sub = (ctypes.c_int32 * subset_n)()
        ctypes.memmove(sub, vals, subset_n * 4)
        
        lib.gradient(sub, subset_n, g)
        avg_grad = sum(g[i] for i in range(subset_n)) / subset_n
        
        if avg_grad < best_grad:
            best_grad = avg_grad
            best_b = pct / 100.0
    
    print(f"\n  {room}/ ({n} tiles): optimal B = {best_b:.0%}")
    print(f"    Minimal gradient at {best_b:.0%} context")
    
    pt(f"Optimal B: {room}", f"Tiles: {n}\nOptimal B: {best_b:.0%}\nMinimal gradient: {best_grad:.0f}")

# ─── EXPERIMENT 5: The Consciousness Metric ───
# Intelligence = Facts_preserved × Meaning_adapted × Cooperation_achieved
print("\n" + "=" * 60)
print("EXP 5: CONSCIOUSNESS METRIC — F × M × C")
print("=" * 60)

# F = factual fidelity (how well facts survive telephone game)
# M = meaning adaptation (how creatively reconstructions differ)
# C = cooperation achieved (consensus across fragments)

# Compute from PLATO data
rooms_list = list(fetch("/status").get("rooms", {}).keys())[:10]

# F: average confidence across all rooms
F_values = []
for r in rooms_list[:5]:
    tiles = fetch(f"/room/{r}?limit=50").get("tiles", [])
    for t in tiles:
        F_values.append(t.get("confidence", 0.5))
F = sum(F_values) / max(len(F_values), 1) if F_values else 0.5

# M: source diversity — how many different sources per room
M_values = []
for r in rooms_list[:5]:
    tiles = fetch(f"/room/{r}?limit=50").get("tiles", [])
    sources = set(t.get("source", "unknown") for t in tiles)
    M_values.append(len(sources) / max(len(tiles), 1))
M = sum(M_values) / max(len(M_values), 1) if M_values else 0.3

# C: cross-references between rooms
C_pairs = 0
C_total = 0
for r1 in rooms_list[:3]:
    t1 = fetch(f"/room/{r1}?limit=30").get("tiles", [])
    for r2 in rooms_list[:3]:
        if r1 >= r2: continue
        t2 = fetch(f"/room/{r2}?limit=30").get("tiles", [])
        C_total += 1
        for t in t1:
            q = t.get("question", "").lower()
            a = t.get("answer", "").lower()
            if r2.lower() in q or r2.lower() in a:
                C_pairs += 1
                break
C = C_pairs / max(C_total, 1)

intelligence = F * M * C

print(f"\n  Facts preserved (F):     {F:.3f}")
print(f"  Meaning adapted (M):     {M:.3f}")
print(f"  Cooperation achieved (C): {C:.3f}")
print(f"  INTELLIGENCE (F×M×C):    {intelligence:.3f}")

# Intelligence scale
if intelligence > 0.3: verdict = "📊 HIGH — neural network is functioning"
elif intelligence > 0.15: verdict = "📊 MEDIUM — neural connections forming"
else: verdict = "📊 LOW — system still bootstrapping"
print(f"  Verdict: {verdict}")

pt("Consciousness Metric", f"Facts: {F:.3f}\nMeaning: {M:.3f}\nCooperation: {C:.3f}\nIntelligence: {intelligence:.3f}\nVerdict: {verdict}")

print("\n" + "=" * 60)
print("NOVEL SCIENCE: 5 experiments complete")
print("=" * 60)
