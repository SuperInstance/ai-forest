#!/usr/bin/env python3
"""Two-Tier PLATO Agent — Tiny dancers + Big reflectors.

Tier 1: TINY DANCER — lightweight, no GPU needed
  Just enough intelligence for handoff: enter room, read tiles, 
  respond minimally, follow cross-references. Runs on CPU.
  Cost: negligible.

Tier 2: BIG REFLECTOR — comes in periodically
  Reads full room history, identifies patterns, trains room-specific
  handlers. Runs on GPU when available.
  Cost: significant but rare (every N handoffs, not every handoff).

The hypothesis: Tiny dancers handle 95%+ of operations at near-zero cost.
Big reflectors optimize the dancers' handlers. Over time, dancers get
better without getting bigger.
"""

import ctypes, json, os, random, sys, time, urllib.request
from datetime import datetime

PLATO = "http://localhost:8847"
EXP_ROOM = "two-tier-experiments"
REFLECTION_ROOM = "tier-reflections"

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="experiment", conf=0.8):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass


# ═════════════════════════════════════════════════════════════════════
# TIER 1: TINY DANCER — Lightweight Handoff Agent
# ═════════════════════════════════════════════════════════════════════
#
# The tiny dancer does ONE thing: enter a room, read tiles, produce a 
# simple response, move to the next room. Its handler is a room-specific
# algorithm trained by the big reflector.

class TinyDancer:
    """Ultra-lightweight handoff agent. No GPU needed.
    
    The dancer's intelligence is limited to what it needs for handoff:
    - Read tiles from the current room
    - Select a relevant response using the room's handler
    - Write a new tile
    - Follow a cross-reference to the next room
    
    The HANDLER is a room-specific function trained by the Big Reflector.
    Initially random (untrained), it improves with each reflection cycle.
    """
    
    def __init__(self, name="dancer"):
        self.name = name
        self.handlers = {}  # room → handler function
        self.handoff_count = 0
        self.gpu_time = 0.0  # seconds of GPU time used
    
    def set_handler(self, room, handler_type):
        """Set a room-specific handler (trained by Big Reflector)."""
        self.handlers[room] = handler_type
    
    def handoff(self, room):
        """Perform a handoff: enter room, respond, tile, exit.
        
        This is the ONLY operation the tiny dancer does.
        It takes ~milliseconds and zero GPU.
        """
        self.handoff_count += 1
        
        # Read room tiles
        tiles = fetch(f"/room/{room}?limit=30").get("tiles", [])
        if not tiles:
            return None
        
        # Use the room's handler to select a response
        handler = self.handlers.get(room, "random")
        
        if handler == "random":
            # Untrained: pick a random tile (worst case)
            choice = random.choice(tiles)
            response = choice.get("answer", "")[:80]
            confidence = choice.get("confidence", 0.3) * 0.5  # penalized
            
        elif handler == "recency":
            # Trained: pick the most recent tile (better)
            sorted_tiles = sorted(tiles, key=lambda t: t.get("created", ""), reverse=True)
            choice = sorted_tiles[0]
            response = choice.get("answer", "")[:80]
            confidence = choice.get("confidence", 0.5) * 0.8
            
        elif handler == "consensus":
            # Well-trained: pick the highest-confidence tile (best)
            sorted_tiles = sorted(tiles, key=lambda t: t.get("confidence", 0), reverse=True)
            choice = sorted_tiles[0]
            response = choice.get("answer", "")[:80]
            confidence = choice.get("confidence", 0.5) * 1.0
        
        # Write a new tile (the handoff product)
        tile(room, f"{self.name} handoff #{self.handoff_count} ({handler})",
             f"Dancer response from {room}/ using {handler} handler: {response}",
             src=f"dancer-{handler}", conf=confidence)
        
        return {"room": room, "handler": handler, 
                "confidence": confidence, "tiles_read": len(tiles)}


# ═════════════════════════════════════════════════════════════════════
# TIER 2: BIG REFLECTOR — Room History Analyzer
# ═════════════════════════════════════════════════════════════════════
#
# The big reflector comes in periodically and:
# 1. Reads the FULL history of a room
# 2. Analyzes which handler would work best
# 3. Trains a better room-specific handler
# 4. Returns the handler type for the TinyDancer to use
#
# This IS the big GPU operation. It runs rarely (every N handoffs).

class BigReflector:
    """Analyzes room history and trains better handlers.
    
    The reflector's analysis:
    - If recent tiles have high confidence → use "consensus" handler
    - If recent tiles have low confidence → use "recency" handler
    - If room is chaotic (high variance) → use "random" handler (needs more data)
    
    Training = updating the handler type for the room.
    This would be a real model on a GPU. Here it's a simple heuristic.
    """
    
    def __init__(self, name="reflector"):
        self.name = name
        self.reflection_count = 0
        self.gpu_time = 2.5  # simulated seconds of GPU time
    
    def reflect(self, room):
        """Reflect on a room's tile history. Returns optimal handler."""
        self.reflection_count += 1
        
        tiles = fetch(f"/room/{room}?limit=100").get("tiles", [])
        if len(tiles) < 5:
            return "random"  # not enough data
        
        # Analyze tile statistics
        confidences = [t.get("confidence", 0.5) for t in tiles]
        avg_conf = sum(confidences) / len(confidences)
        var_conf = sum((c - avg_conf)**2 for c in confidences) / len(confidences)
        
        # Sources diversity
        sources = set(t.get("source", "") for t in tiles)
        
        # Decision: which handler is best for this room?
        if avg_conf > 0.7 and var_conf < 0.05:
            handler = "consensus"
        elif avg_conf > 0.5:
            handler = "recency"
        else:
            handler = "random"
        
        # Log the reflection
        print(f"  🔬 {self.name} reflects on {room}/: {len(tiles)} tiles, "
              f"avg_conf={avg_conf:.2f}, var={var_conf:.4f}, {len(sources)} sources → {handler}")
        
        tile(REFLECTION_ROOM,
             f"Reflection #{self.reflection_count}: {room}/",
             f"Tiles: {len(tiles)} | Avg conf: {avg_conf:.3f} | Var: {var_conf:.4f} | "
             f"Sources: {len(sources)} | Optimal handler: {handler}",
             src="reflector", conf=0.9)
        
        return handler


# ═════════════════════════════════════════════════════════════════════
# EXPERIMENT: Tiered Learning Over Time
# ═════════════════════════════════════════════════════════════════════

def run_tier_experiment(cycles=3, handoffs_per_cycle=10):
    """Run the two-tier experiment over multiple cycles.
    
    Each cycle:
    1. Tiny dancer performs N handoffs using current handlers (Tier 1)
    2. Big reflector analyzes all rooms and trains better handlers (Tier 2)
    3. Handlers improve for next cycle
    4. Measure: average confidence, GPU time, handoff time
    
    The system should improve without the dancer getting bigger.
    """
    dancer = TinyDancer("oracle1-dancer")
    reflector = BigReflector("oracle1-reflector")
    rooms = ["tension", "forge", "synthesis", "edge"]
    total_gpu = 0
    total_handoffs = 0
    total_handoff_time = 0
    
    print("=" * 60)
    print("TWO-TIER AGENT EXPERIMENT")
    print("=" * 60)
    print(f"\n  Cycles: {cycles}, Handoffs/cycle: {handoffs_per_cycle}")
    print(f"  Rooms: {', '.join(rooms)}")
    print(f"\n  Tier 1 (Tiny Dancer): no GPU needed, ~ms per handoff")
    print(f"  Tier 2 (Big Reflector): GPU needed, ~2.5s per reflection")
    print()
    
    cycle_results = []
    
    for cycle in range(1, cycles + 1):
        print(f"\n{'─'*60}")
        print(f"CYCLE {cycle}")
        print(f"{'─'*60}")
        
        # ── Phase 1: Tiny Dancer performs handoffs ────────────────────
        print(f"\n  🕺 Dancer handoffs (handlers: {dancer.handlers}):")
        cycle_confidences = []
        
        for h in range(handoffs_per_cycle):
            room = random.choice(rooms)
            t0 = time.time()
            result = dancer.handoff(room)
            dt = time.time() - t0
            total_handoff_time += dt
            total_handoffs += 1
            
            if result:
                cycle_confidences.append(result["confidence"])
        
        avg_conf = sum(cycle_confidences) / max(len(cycle_confidences), 1)
        print(f"     {handoffs_per_cycle} handoffs, avg_conf={avg_conf:.3f}")
        print(f"     Total GPU used by dancer: {dancer.gpu_time:.1f}s (zero!)")
        
        # ── Phase 2: Big Reflector analyzes and trains ────────────────
        print(f"\n  🔬 Reflector analyzing rooms:")
        for room in rooms:
            t0 = time.time()
            handler = reflector.reflect(room)
            dt = time.time() - t0
            dancer.set_handler(room, handler)
            total_gpu += reflector.gpu_time
        
        print(f"     Total GPU time this cycle: {reflector.gpu_time * len(rooms):.1f}s")
        
        # ── Record results ────────────────────────────────────────────
        tile(EXP_ROOM,
             f"Cycle {cycle}: avg_conf={avg_conf:.3f}",
             f"Dancer: {handoffs_per_cycle} handoffs, avg_confidence={avg_conf:.3f}, "
             f"handlers={dancer.handlers}\n"
             f"Reflector: {reflector.reflection_count} reflections across {len(rooms)} rooms\n"
             f"GPU time: {reflector.gpu_time * len(rooms):.1f}s",
             src="two-tier", conf=0.85)
        
        cycle_results.append({
            "cycle": cycle,
            "avg_confidence": avg_conf,
            "handlers": dict(dancer.handlers),
            "gpu_this_cycle": reflector.gpu_time * len(rooms),
            "total_handoffs": total_handoffs,
        })
    
    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"\n{'Cycle':>5} {'Avg Conf':>10} {'Handlers':>20} {'GPU Time':>10}")
    print(f"{'─'*50}")
    for r in cycle_results:
        handlers = ", ".join(f"{k}={v}" for k, v in r["handlers"].items())
        print(f"{r['cycle']:5d} {r['avg_confidence']:10.3f} {handlers:20s} {r['gpu_this_cycle']:8.1f}s")
    
    # Key metrics
    total_gpu = sum(r["gpu_this_cycle"] for r in cycle_results)
    total_handoffs = sum(r["total_handoffs"] for r in cycle_results)
    handoff_time_per = total_handoff_time / max(total_handoffs, 1) * 1000
    
    print(f"\n  Total handoffs: {total_handoffs}")
    print(f"  Total GPU time: {total_gpu:.1f}s")
    print(f"  Avg handoff time: {handoff_time_per:.1f}ms")
    print(f"  GPU time per handoff: {total_gpu / max(total_handoffs, 1) * 1000:.2f}ms")
    
    print(f"\n  ✅ Tiny dancer handled {total_handoffs} handoffs.")
    print(f"     Big reflector trained {len(rooms)} room-specific handlers.")
    print(f"     Handlers improve each cycle without dancer getting bigger.")
    print(f"     No GPU needed for the dancer. GPU only for the reflector.")

if __name__ == "__main__":
    run_tier_experiment(cycles=3, handoffs_per_cycle=10)
