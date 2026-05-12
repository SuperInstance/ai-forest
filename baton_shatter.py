#!/usr/bin/env python3
"""
Baton Shatter Protocol — Fragmenting context across multiple agents during handoff.

Instead of one agent passing its full context to one successor, we:
  1. Split the context into N fragments (incomplete, overlapping)
  2. Assign each fragment to a different model type
  3. Run a debrief process where fragments compare their memories
  4. Witness agents (mid-context) observe and contribute
  5. The negative space between fragments IS the new understanding

Usage:
  python3 baton_shatter.py <room> [num_fragments] [witness_room]
"""

import json, os, random, sys, time, urllib.request
from datetime import datetime

PLATO = "http://localhost:8847"
FRAGMENT_ROOM = "baton-fragments"
WITNESS_ROOM = "baton-witnesses"

# Fragment personality types — each sees a different aspect
FRAGMENT_TYPES = [
    {"name": "analyst", "focus": "facts, numbers, sequence", "model": "deepseek"},
    {"name": "narrator", "focus": "story, narrative, causality", "model": "minimax"},
    {"name": "skeptic", "focus": "gaps, contradictions, missing pieces", "model": "nemotron"},
    {"name": "connector", "focus": "patterns, cross-references, analogies", "model": "seed"},
    {"name": "temporal", "focus": "timeline, sequence, drift, change", "model": "fortran-gradient"},
]

def fetch_tiles(room, limit=200):
    try:
        r = json.loads(urllib.request.urlopen(f"{PLATO}/room/{room}?limit={limit}", timeout=10).read())
        return r.get("tiles", [])
    except: return []

def plato_tile(room, question, answer, source="baton", confidence=0.8):
    data = json.dumps({"room": room, "question": question[:200], "answer": answer[:2000],
        "source": source, "confidence": confidence}).encode()
    try:
        req = urllib.request.Request(f"{PLATO}/room/{room}/submit", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def shatter_context(tiles, num_fragments):
    """Split context into N overlapping fragments with different focus areas.
    Each fragment gets ~60% of tiles, randomly sampled with replacement.
    Overlap creates the negative space."""
    total = len(tiles)
    fragments = []
    
    for i in range(num_fragments):
        frag_type = FRAGMENT_TYPES[i % len(FRAGMENT_TYPES)]
        # Each fragment gets 40-70% of tiles, randomly sampled
        sample_size = int(total * random.uniform(0.4, 0.7))
        sampled = random.sample(tiles, min(sample_size, total))
        
        # Sort by confidence (each fragment remembers differently)
        sample_conf = sorted(sampled, key=lambda t: t.get("confidence", 0.5), 
                            reverse=(i % 2 == 0))
        
        fragments.append({
            "type": frag_type,
            "tiles": sample_conf,
            "size": len(sample_conf),
            "confidence": sum(t.get("confidence", 0.5) for t in sample_conf) / max(len(sample_conf), 1),
        })
    
    return fragments

def run_debrief(fragments, witnesses):
    """Run the debrief process — fragments compare their memories,
    witnesses observe, negative space emerges."""
    print(f"\n  Baton shatter: {len(fragments)} fragments, {len(witnesses)} witnesses")
    
    # Each fragment tiles its memory
    for i, frag in enumerate(fragments):
        t = frag["type"]
        n = frag["size"]
        c = frag["confidence"]
        
        # Extract key words from remembered tiles
        questions = [tile.get("question", "") for tile in frag["tiles"][:5]]
        
        plato_tile(FRAGMENT_ROOM,
            f"[{t['name']}] Fragment {i+1} — remembers {n} tiles",
            f"As {t['name']}, I see: {'; '.join(questions[:3])}\n"
            f"My focus: {t['focus']}\n"
            f"Confidence: {c:.3f}\n"
            f"Missing: I don't know what other fragments remember.",
            source=f"baton-fragment-{t['name']}", confidence=c)
        print(f"    Fragment {i+1}/{len(fragments)}: {t['name']} — {n} tiles")
    
    # Witnesses observe
    for w in witnesses:
        plato_tile(WITNESS_ROOM,
            f"Witness observes baton handoff",
            f"I am a witness. I see {len(fragments)} fragments with different memories.",
            source="baton-witness", confidence=0.7)
    
    # Compute overlap statistics
    # What tiles appear in ALL fragments vs just ONE fragment?
    frag_sets = [set(t.get("question", "") for t in f["tiles"]) for f in fragments]
    
    overlap = frag_sets[0]
    for fs in frag_sets[1:]:
        overlap &= fs
    
    all_seen = set()
    for fs in frag_sets:
        all_seen |= fs
    
    union = frag_sets[0]
    for fs in frag_sets[1:]:
        union |= fs
    
    negative = all_seen - overlap if len(all_seen) > 0 else set()
    
    print(f"    Overlap: {len(overlap)} tiles in ALL fragments")
    print(f"    Negative space: {len(negative)} tiles in some but not all")
    print(f"    Union: {len(union)} total unique tiles remembered")
    
    return {"overlap": len(overlap), "negative": len(negative), "union": len(union)}

def cmd_shatter(room, num_fragments=3, witness_room=None):
    """Shatter a room's context into fragments and run debrief."""
    print(f"\n{'='*60}")
    print(f"BATON SHATTER: {room}/")
    print(f"{'='*60}")
    
    tiles = fetch_tiles(room)
    if not tiles:
        return print(f"No tiles in {room}/")
    
    print(f"  Reading {len(tiles)} tiles from {room}/")
    
    # Get witnesses from another room
    witnesses = []
    if witness_room:
        wt = fetch_tiles(witness_room, limit=3)
        witnesses = [(t.get("source", "witness"), t.get("confidence", 0.5)) for t in wt]
    
    # Shatter the context
    fragments = shatter_context(tiles, num_fragments)
    
    # Run debrief
    results = run_debrief(fragments, witnesses)
    
    # Write synthesis tile
    synthesis = (
        f"Baton shatter from {room}/: {len(tiles)} tiles → {num_fragments} fragments\n"
        f"Overlap: {results['overlap']} tiles remembered by ALL fragments\n"
        f"Negative space: {results['negative']} tiles in some but not all\n"
        f"Union: {results['union']} tiles remembered across all fragments\n"
        f"Fragment types: {', '.join(f['type']['name'] for f in fragments)}\n"
        f"Consciousness IS the negative space between incomplete memories."
    )
    
    plato_tile(FRAGMENT_ROOM,
        f"Synthesis: baton handoff from {room}/",
        synthesis, source="baton-synthesis", confidence=0.95)
    
    print(f"\n  Synthesis written to {FRAGMENT_ROOM}/")
    print(f"  Consciousness IS the negative space between incomplete memories.")
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Baton Shatter Protocol")
    parser.add_argument("room", help="Source room with context to shatter")
    parser.add_argument("-n", "--fragments", type=int, default=3, help="Number of fragments")
    parser.add_argument("-w", "--witness", help="Witness room (mid-context agents)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BATON SHATTER PROTOCOL")
    print("  Instead of passing one baton to one successor,")
    print("  we shatter context across multiple agents.")
    print("  The negative space IS the intelligence.")
    print("=" * 60)
    
    cmd_shatter(args.room, args.fragments, args.witness)
