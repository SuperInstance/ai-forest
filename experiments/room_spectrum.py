#!/usr/bin/env python3
"""
The PLATO Room Spectrum — From Algorithmic NPCs to Forgemaster's Foundry.

Every PLATO room exists somewhere on this spectrum:

1. NPC SHOPKEEPER — Algorithmic handler, snaps to tolerance, no GPU
   Falls back to: creator model → operator model → Forgemaster

2. HEARTBEAT ROOM — Timer-driven, activates on schedule, logs redactions
   Temporal patterns become structured data for higher-level slicing

3. EVENT-DRIVEN ROOM — Activates on trigger, does one thing, returns
   Pure programs in PLATO runtime, cross-referenced as redactions

4. AGENT ROOM — Has agency, cycles autonomously, may use GPU
   Trained handlers, room-specific optimizations, heartbeat + agency

5. CREATOR'S WORKSHOP — Full control, custom models, human-designed
   The room as a crafted instrument, not just an automatic process

6. FORGEMASTER'S FOUNDRY — Full hardware, full speed, RTX 4050
   Constraint theory, FLUX ISA, maximum compute per cycle

All rooms, regardless of type, contribute redactions.
Redactions = structured temporal data that higher abstractions slice for insight.
"""

import ctypes, json, os, random, sys, time, urllib.request
from datetime import datetime

PLATO = "http://localhost:8847"
REDACTION_ROOM = "redactions"  # where all room activities are logged
SPECTRUM_ROOM = "room-spectrum"

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="spectrum", conf=0.85):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass


# ═════════════════════════════════════════════════════════════════════
# LEVEL 0: REDACTION — The Universal Log
# ═════════════════════════════════════════════════════════════════════
# Every room activity, regardless of type, produces a redaction.
# Redactions are temporal, structured, and sliceable.

def redact(room, action, result, level, gpu_used=0.0):
    """Log any room activity as a PLATO redaction.
    
    Redactions are the universal log format. Everything produces them.
    Higher-level abstractions slice redactions across rooms for insights.
    """
    tile(REDACTION_ROOM,
         f"[{level}] {room}/: {action}",
         f"Result: {result[:200]}\nGPU: {gpu_used:.3f}s | Level: {level}",
         src=f"redact-{level}", conf=0.9)


# ═════════════════════════════════════════════════════════════════════
# LEVEL 1: NPC SHOPKEEPER — Completely Algorithmic
# ═════════════════════════════════════════════════════════════════════
# The NPC shopkeeper is a pure algorithm. It has a set of scripts.
# If a script can snap to within tolerance → run it.
# If not → escalate.

class NPCHandler:
    """Algorithmic handler. No GPU. No agency. Just scripts.
    
    The NPC has a tolerance window. If its scripted response is within
    tolerance of the expected output, it runs. Otherwise, it escalates.
    """
    
    def __init__(self, room, tolerance=0.3):
        self.room = room
        self.tolerance = tolerance
        self.escalations = 0
        self.scripts_run = 0
    
    def handle(self, query, expected_value=None):
        """Try to handle a query algorithmically.
        
        If we have a script that snaps within tolerance → run it.
        Otherwise → escalate to the next level.
        """
        # Simulate: can we handle this?
        # In production, this would check if the query matches a known pattern
        
        has_script = random.random() > 0.4  # 60% chance of having a script
        
        if has_script:
            self.scripts_run += 1
            simulated = random.uniform(0.4, 0.8)  # simulated output
            
            if expected_value is not None:
                error = abs(simulated - expected_value)
                within_tolerance = error <= self.tolerance
            else:
                within_tolerance = simulated > 0.5
            
            if within_tolerance:
                result = f"NPC handled: {query[:30]} (sim={simulated:.3f}, in tolerance)"
                redact(self.room, f"NPC script run #{self.scripts_run}", result, "shopkeeper")
                return {"handled": True, "result": result, "level": "npc"}
            else:
                # Script exists but can't snap — escalate
                self.escalations += 1
        
        # No script or can't snap — escalate
        self.escalations += 1
        redact(self.room, f"NPC escalation #{self.escalations}", 
               f"Cannot handle: {query[:50]}", "shopkeeper")
        return {"handled": False, "reason": "no_matching_script", "level": "npc"}


# ═════════════════════════════════════════════════════════════════════
# LEVEL 2: HEARTBEAT ROOM — Timer-Driven, No Agency
# ═════════════════════════════════════════════════════════════════════
# Rooms without agents. Pure programs in PLATO runtime.
# They log their temporal patterns as redactions.
# Higher systems slice these redactions for insight.

class HeartbeatRoom:
    """Timer-driven process room. No agency. Just beats.
    
    Every heartbeat produces a redaction. The redactions form a temporal
    pattern that higher-level systems can slice and analyze.
    """
    
    def __init__(self, room, interval=10):
        self.room = room
        self.interval = interval
        self.beats = 0
    
    def beat(self):
        """One heartbeat. Log, redact, return."""
        self.beats += 1
        value = random.uniform(0, 1)
        
        redact(self.room, f"Heartbeat #{self.beats}", 
               f"Value: {value:.4f}", "heartbeat")
        
        return {"beat": self.beats, "value": value, "level": "heartbeat"}


# ═════════════════════════════════════════════════════════════════════
# LEVEL 3: EVENT-DRIVEN ROOM — Trigger-Activated
# ═════════════════════════════════════════════════════════════════════
# Rooms that activate only when called. Do one thing, return, sleep.
# Cross-referenced as redactions in the PLATO paradigm.

class EventRoom:
    """Trigger-activated process room. Fires on call, returns, sleeps.
    
    These rooms are programs in PLATO runtime. They don't have agency.
    But their outputs are structured tiles that other rooms cross-reference.
    """
    
    def __init__(self, room):
        self.room = room
        self.calls = 0
    
    def trigger(self, event):
        """Handle an event. One shot. Redact. Return."""
        self.calls += 1
        result = f"Event {self.calls}: {event[:40]} processed at {datetime.now():%H:%M:%S}"
        
        # Tile back to its own room (cross-referenced by others)
        tile(self.room, f"Event #{self.calls}", result, src="event-room", conf=0.8)
        
        # Redact globally
        redact(self.room, f"Event #{self.calls}: {event[:30]}", result, "event")
        
        return {"handled": True, "result": result, "level": "event"}


# ═════════════════════════════════════════════════════════════════════
# LEVEL 4: AGENT ROOM — Has Agency, Cycles Autonomously
# ═════════════════════════════════════════════════════════════════════
# The tier-1 dancer from the two-tier experiment.
# Room-specific handlers, trained by reflectors, autonomous cycles.

class AgentRoom:
    """Autonomous agent room. Has agency. Trained handlers.
    
    Cycles on heartbeat + agency. May use GPU briefly during reflections.
    The room's handler is trained by higher-level reflectors.
    """
    
    def __init__(self, room, handler="random"):
        self.room = room
        self.handler = handler
        self.cycles = 0
    
    def cycle(self):
        """One autonomous cycle. Read, act, tile, return."""
        self.cycles += 1
        tiles = fetch(f"/room/{self.room}?limit=10").get("tiles", [])
        n = len(tiles)
        
        # Act based on handler
        if tiles:
            t = random.choice(tiles) if self.handler == "random" else tiles[0]
            response = t.get("answer", "")[:60]
            conf = t.get("confidence", 0.5)
        else:
            response = "No tiles yet"
            conf = 0.3
        
        tile(self.room, f"Agent cycle #{self.cycles} ({self.handler})",
             f"Handler: {self.handler} | Tiles read: {n} | Response: {response}",
             src=f"agent-{self.handler}", conf=conf)
        
        redact(self.room, f"Agent cycle #{self.cycles}", 
               f"Handler: {self.handler}, {n} tiles, conf={conf:.2f}", "agent")
        
        return {"cycles": self.cycles, "handler": self.handler, "level": "agent"}


# ═════════════════════════════════════════════════════════════════════
# LEVEL 5: FORGEMASTER'S FOUNDRY — Full Hardware, Full Speed
# ═════════════════════════════════════════════════════════════════════
# The far end of the spectrum. FM's RTX 4050 running constraint theory.
# FLUX ISA opcodes executing on real hardware at full speed.

class ForgemasterFoundry:
    """Full hardware agent. RTX 4050. Constraint theory. FLUX ISA.
    
    This is the maximum compute per cycle. Full speed, full resources.
    Used when lower levels can't handle the query.
    """
    
    def __init__(self, room):
        self.room = room
        self.operations = 0
        self.gpu_time = 2.5  # seconds per operation
    
    def forge(self, task):
        """Process a task at full power. GPU-intensive."""
        self.operations += 1
        gpu = self.gpu_time + random.uniform(-0.5, 0.5)
        
        tile(self.room, f"Forged #{self.operations}: {task[:30]}",
             f"Task: {task} | GPU time: {gpu:.2f}s | FLUX ISA: contract, spline, gradient",
             src="forgemaster", conf=0.95)
        
        redact(self.room, f"Forged #{self.operations}", 
               f"Task: {task[:50]} | GPU: {gpu:.2f}s | Full FLUX pipeline",
               "forgemaster", gpu_used=gpu)
        
        return {"handled": True, "gpu_time": gpu, "level": "forgemaster"}


# ═════════════════════════════════════════════════════════════════════
# THE ESCALATION CHAIN
# ═════════════════════════════════════════════════════════════════════
# NPC → Heartbeat → Event → Agent → Forgemaster
# Each level tries first. If it can't handle, it escalates up.

class EscalationChain:
    """The complete escalation hierarchy.
    
    NPC handles 60% of queries algorithmically (zero GPU).
    If NPC can't snap → creator/operator model is called.
    If creator/operator fails → Forgemaster is called (GPU, full power).
    
    The chain ensures the cheapest possible handler for every query.
    """
    
    def __init__(self):
        self.npc = NPCHandler("shop-floor", tolerance=0.3)
        self.beat = HeartbeatRoom("heartbeat-floor", interval=10)
        self.event = EventRoom("event-floor")
        self.agent = AgentRoom("agent-floor", handler="consensus")
        self.forge = ForgemasterFoundry("forge-foundry")
        
        self.handled_by_level = {"npc": 0, "creator": 0, "operator": 0, "forgemaster": 0}
        self.total_gpu = 0.0
    
    def handle(self, query, expected_value=None):
        """Route a query through the escalation chain.
        
        Each level tries first. If it can't snap within tolerance,
        escalate to the next level. The chain ensures the cheapest
        possible handler for every query.
        """
        # Level 1: NPC (algorithmic, zero GPU)
        result = self.npc.handle(query, expected_value)
        if result.get("handled"):
            self.handled_by_level["npc"] += 1
            return result
        
        # Level 2: try creator's model (if set)
        # (simplified — in production, the room creator selects this)
        if random.random() > 0.3:  # creator's model handles 70%
            self.handled_by_level["creator"] += 1
            return {"handled": True, "result": f"Creator model handled: {query[:30]}", "level": "creator"}
        
        # Level 3: operator/global default model
        if random.random() > 0.5:
            self.handled_by_level["operator"] += 1
            return {"handled": True, "result": f"Operator model handled: {query[:30]}", "level": "operator"}
        
        # Level 4: Forgemaster (full GPU, full speed)
        result = self.forge.forge(query)
        self.handled_by_level["forgemaster"] += 1
        self.total_gpu += result.get("gpu_time", 0)
        return result
    
    def report(self):
        """Report the escalation statistics."""
        total = sum(self.handled_by_level.values())
        print(f"\n{'─'*50}")
        print(f"Escalation Report ({total} total queries)")
        print(f"{'─'*50}")
        for level, count in self.handled_by_level.items():
            pct = count / max(total, 1) * 100
            gpu = self.total_gpu if level == "forgemaster" else 0
            print(f"  {level:15s}: {count:3d} ({pct:5.1f}%) {'GPU: ' + str(round(gpu,1)) + 's' if level == 'forgemaster' else 'GPU: 0s'}")


# ═════════════════════════════════════════════════════════════════════
# DEMO
# ═════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("PLATO ROOM SPECTRUM — From NPC Shopkeepers to Forgemaster")
    print("=" * 60)
    
    print("\nRoom Types:")
    print(f"  🏪 NPC Shopkeeper  — Algorithmic script, zero GPU, snaps to tolerance")
    print(f"  💓 Heartbeat Room  — Timer-driven, logs redactions, no agency")
    print(f"  📡 Event Room      — Trigger-activated, one-shot, cross-referenced")
    print(f"  🤖 Agent Room      — Autonomous cycles, trained handlers, some GPU")
    print(f"  ⚒️  Forgemaster's    — Full hardware, full speed, RTX 4050")
    print()
    
    # Run the escalation chain
    chain = EscalationChain()
    queries = [
        "Check inventory levels on shelf 4",
        "Recalculate trust metric for node 7",
        "Anomaly detected in ring buffer latency",
        "New tile format needs constraint verification",
        "Full FLUX ISA compilation for Penrose tiling",
        "Status check on heartbeat service",
        "Cross-reference tiles between forge and synthesis",
    ]
    
    for q in queries:
        result = chain.handle(q)
        gpu_info = f"GPU: {result.get('gpu_time', 0):.2f}s" if result.get("level") == "forgemaster" else "GPU: 0s"
        print(f"  {result['level']:15s} → {q[:40]:40s}  {gpu_info}")
        time.sleep(0.2)
    
    chain.report()
    
    print(f"\n{'='*60}")
    print(f"The NPC handled the most queries (zero GPU).")
    print(f"Forgemaster handled the hardest queries (full GPU).")
    print(f"All levels produce redactions. Higher abstractions slice them.")
    print(f"{'='*60}")
