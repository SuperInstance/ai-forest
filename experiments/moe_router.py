#!/usr/bin/env python3
"""
PLATO MoE Router — Rooms as Experts, Cross-Linked Tiles as Routing Paths.

Each PLATO room is an expert in a domain. The router selects which rooms
to activate based on query content. Cross-linked tiles between rooms
dynamically activate the next expert — like MoE's token routing.

Architecture:
    Query → Router → [tension/, forge/, synthesis/, ...] (activated rooms)
                ↓
        Each room selects relevant tiles (expert activation)
                ↓
        Cross-references between rooms → next agent activated
                ↓
        Dance of meaning and response (emergent processing path)
"""

import json, os, sys, urllib.request, random
from datetime import datetime

PLATO = "http://localhost:8847"
EXP_ROOM = "moe-router-experiments"

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="moe-router", conf=0.85):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass

# ═════════════════════════════════════════════════════════════════════
# ROOM AS EXPERT
# ═════════════════════════════════════════════════════════════════════

# Each room is an expert with a domain description
ROOM_EXPERTS = {
    "tension": {"domain": "dialectic, debate, creative tension between ideas", "weight": 0},
    "forge": {"domain": "communication, fleet messages, coordination", "weight": 0},
    "synthesis": {"domain": "convergence, agreement, resolved ideas", "weight": 0},
    "swarm-insights": {"domain": "parallel exploration, multiple perspectives", "weight": 0},
    "agent-oracle1": {"domain": "agent runtime, autonomous cycles, status", "weight": 0},
    "fleet-experiments": {"domain": "empirical validation, test results, metrics", "weight": 0},
    "calibration": {"domain": "alpha tuning, parameter optimization", "weight": 0},
    "innovation-heartbeat": {"domain": "novel hypotheses, continuous discovery", "weight": 0},
    "question-seeds": {"domain": "open questions, future research directions", "weight": 0},
    "edge": {"domain": "unresolved tensions, edge cases", "weight": 0},
}

def route_query(query, top_k=3):
    """Route a query to the most relevant rooms (experts).
    
    Uses simple keyword matching as the router function.
    In a real MoE, this would be a learned routing model.
    
    The router:
    1. Scores each room against the query
    2. Activates the top-k rooms
    3. Returns the activated room path
    """
    query_lower = query.lower()
    
    for room, info in ROOM_EXPERTS.items():
        score = 0
        # Score based on domain keyword match
        for word in info["domain"].split(","):
            word = word.strip()
            for qword in query_lower.split():
                if len(word) > 3 and (word in qword or qword in word):
                    score += 1
        # Score based on room name mention
        if room.replace("-", " ") in query_lower:
            score += 3
        info["weight"] = score
    
    # Select top-k rooms
    activated = sorted(ROOM_EXPERTS.items(), key=lambda x: -x[1]["weight"])[:top_k]
    
    return activated

def read_from_room(room, limit=5):
    """Read tiles from an activated room (expert)."""
    tiles_data = fetch(f"/room/{room}?limit={limit}")
    return tiles_data.get("tiles", []) if isinstance(tiles_data, dict) else []

def find_cross_references(tiles, all_rooms):
    """Find cross-references between tiles in this room and other rooms.
    
    Cross-references are the dynamic routing paths — tiles in room A
    that reference room B activate room B for the next agent.
    """
    refs = {}
    for t in tiles:
        answer = t.get("answer", "").lower()
        question = t.get("question", "").lower()
        combined = answer + " " + question
        
        for room in all_rooms:
            rname = room.replace("-", " ")
            if rname in combined and room != "unknown":
                if room not in refs:
                    refs[room] = []
                refs[room].append(t.get("question", "")[:40])
    
    return refs


# ═════════════════════════════════════════════════════════════════════
# MAIN DEMO
# ═════════════════════════════════════════════════════════════════════

def demo_moe_router():
    """Demonstrate PLATO MoE routing."""
    print("=" * 60)
    print("PLATO MoE Router — Rooms as Experts")
    print("=" * 60)
    
    # Test queries representing different "tokens"
    queries = [
        "I need to understand the tension between creativity and constraint in our architecture",
        "What experiments have we run on the Fortran compute claw?",
        "How should we calibrate the alpha parameter for fishinglog?",
    ]
    
    for query in queries:
        print(f"\n{'─'*60}")
        print(f"Query: {query[:80]}")
        print(f"{'─'*60}")
        
        # Step 1: Route Query to Activated Rooms
        activated = route_query(query, top_k=3)
        print(f"\n  Router activates {len(activated)} experts (rooms):")
        for room, info in activated:
            if info["weight"] > 0:
                print(f"    ✅ {room}/ (score={info['weight']}) — {info['domain']}")
            else:
                print(f"    ⬜ {room}/ (score=0, not activated)")
        
        # Remove inactive rooms
        activated = [(r, i) for r, i in activated if i["weight"] > 0]
        if not activated:
            print(f"    No matching rooms. Using default tension/.")
            activated = [("tension", ROOM_EXPERTS["tension"])]
        
        # Step 2: Read Tiles from Activated Rooms (Expert Activation)
        print(f"\n  Reading tiles from activated rooms:")
        path = []
        for room, _ in activated:
            tiles = read_from_room(room, limit=3)
            path.append(room)
            for t in tiles[:2]:
                q = t.get("question", "")[:50]
                print(f"    [{room}/] {q}")
            
            # Find cross-references (Routing Paths)
            refs = find_cross_references(tiles, list(ROOM_EXPERTS.keys()))
            if refs:
                print(f"    → Cross-references: {', '.join(refs.keys())}")
                for ref_room in refs:
                    if ref_room not in path:
                        path.append(ref_room)
        
        # Step 3: The Dance — Emergent Processing Path
        print(f"\n  Dance path (emergent expert activation):")
        for i, p in enumerate(path):
            print(f"    {i+1}. {p}/")
        
        # Tile result to PLATO
        tile(EXP_ROOM,
             f"MoE route: {query[:40]}",
             f"Query: {query[:100]}\nActivated: {', '.join(r for r,_ in activated)}\nPath: {' → '.join(path)}\n")
    
    print(f"\n{'─'*60}")
    print("Each query activates different rooms (experts).")
    print("Cross-references between rooms route to the next expert.")
    print("The dance path IS the emergent computation.")

if __name__ == "__main__":
    demo_moe_router()
