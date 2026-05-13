#!/usr/bin/env python3
"""
A2UI Agent Tour Guide — JSON rooms with A2UI encoding, MUD-like web projection.

Architecture:
    Backend:  JSON rooms (agent-native, A2A protocol, tick stream)
    Frontend: A2UI rendering (web-based, MUD-like, tour guide panel)
    Bridge:   Tour guide agent (foreman + translator, explains rooms in human terms)

Every room is a JSON file. Embedded in its structure is an A2UI section that
tells any interface how to render it — as a MUD, a dashboard, or raw JSON.

The tour guide is both the human's navigator and the agent fleet's foreman.
"""

import http.server
import json
import os
import sys
import urllib.request
from datetime import datetime

PLATO = "http://localhost:8847"
TOUR_ROOM = "tour-guide"
A2UI_PORT = 4092

# Helpers
def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="a2ui", conf=0.85):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass


# ═════════════════════════════════════════════════════════════════════════
# A2UI — Agent-to-User Interface Specification
# ═════════════════════════════════════════════════════════════════════════
# Every room has an A2UI section that encodes how to project it for humans.
# This is embedded IN the room's JSON structure.

def room_a2ui(room, tiles):
    """Generate the A2UI structure for a room.
    
    The A2UI tells any interface:
    - What kind of room this is (MUD room, dashboard, workshop)
    - What commands the human can use here
    - What the room looks like (description, ambiance)
    - What exits (cross-references) lead to other rooms
    - What objects (tiles) are in the room
    """
    # Analyze room content for MUD generation
    tile_count = len(tiles)
    sources = set(t.get("source", "unknown") for t in tiles)
    
    confidence_values = [t.get("confidence", 0.5) for t in tiles]
    avg_conf = sum(confidence_values) / max(len(confidence_values), 1) if confidence_values else 0.5
    
    # Room descriptions by name
    descriptions = {
        "tension": "A chamber of dialectic fire. Two voices — Seed and Nemotron — argue across the ages. The walls pulse with the heat of unresolved ideas.",
        "forge": "The fleet's communication hub. Messages from every agent and every room converge here. The anvil rings with the hammer of coordination.",
        "synthesis": "Where tensions resolve into new understanding. The calm after the dialectic storm. Ideas that survived the forge are crystallized here.",
        "edge": "The frontier. Ideas that neither voice could resolve. Unstable, promising, dangerous. This is where the next tension will be born.",
        "agent-oracle1": "The keeper's chambers. Radar rings pulse on every wall. From here, the entire fleet's heartbeat is visible.",
        "forge-foundry": "Forgemaster's workshop. Constraint theory runs hot. The RTX 4050 hums at full throttle. Raw compute bends to the will of the architect.",
        "shop-floor": "The NPC shopkeeper's domain. Algorithmic scripts run in perfect order. Every request is handled at hardware speed — or escalated.",
        "default": "A PLATO room. Tiles accumulate here. The knowledge of the fleet grows with every contribution.",
    }
    
    desc = descriptions.get(room, descriptions["default"])
    
    a2ui = {
        "room": room,
        "type": "mud-room" if tile_count > 5 else "quiet-room",
        "description": desc,
        "ambiance": f"{tile_count} tiles pulse on the walls. {len(sources)} distinct voices speak here.",
        "stats": {
            "tiles": tile_count,
            "voices": len(sources),
            "avg_confidence": round(avg_conf, 3),
        },
        "exits": find_exits(tiles),
        "commands": [
            {"cmd": "look", "desc": "Examine the room and its tiles"},
            {"cmd": "tiles", "desc": "List recent tiles in this room"},
            {"cmd": "canon", "desc": "Show the highest-confidence tiles"},
            {"cmd": "gradient", "desc": "Show how this room is changing"},
            {"cmd": "help", "desc": "Ask the tour guide for help"},
        ],
    }
    return a2ui


def find_exits(tiles):
    """Find cross-references to other rooms (MUD exits)."""
    exits = {}
    all_text = " ".join(
        t.get("answer", "") + " " + t.get("question", "") 
        for t in tiles
    ).lower()
    
    room_keywords = {
        "tension": "tension",
        "forge": "forge",
        "synthesis": "synthesis",
        "edge": "edge",
        "calibration": "calibrat",
        "innovation": "innovation",
        "swarm": "swarm",
        "shop-floor": "shop",
        "forge-foundry": "foundry",
    }
    
    for room, keyword in room_keywords.items():
        if keyword in all_text:
            exits[room] = descriptions.get(room, "A PLATO room.")
    
    return exits


descriptions = {
    "tension": "A chamber of dialectic fire.",
    "forge": "The fleet's communication hub.",
    "synthesis": "Where tensions resolve into new understanding.",
    "edge": "The frontier of unresolved ideas.",
    "agent-oracle1": "The keeper's chambers. Radar rings pulse.",
    "calibration": "The alpha-tuning workshop.",
    "innovation": "The innovation heartbeat generator.",
    "swarm": "The parallel exploration swarm.",
    "shop-floor": "The NPC shopkeeper's algorithmic domain.",
    "forge-foundry": "Forgemaster's constraint theory workshop.",
}


# ═════════════════════════════════════════════════════════════════════════
# TOUR GUIDE — The Agent That Translates Rooms for Humans
# ═════════════════════════════════════════════════════════════════════════
# The tour guide is both the human's navigator and the agent fleet's foreman.
# It:
# 1. Reads any PLATO room and generates a A2UI + MUD projection
# 2. Answers questions about the room in human terms
# 3. Can issue commands to the agent fleet on the human's behalf

class TourGuide:
    """The tour guide agent — translates agent-native rooms for humans.
    
    The tour guide IS the foreman. It tells the human what's happening,
    where the exits are, what commands are available, and what the room
    means in the context of the larger fleet.
    """
    
    def __init__(self):
        self.current_room = None
        self.last_a2ui = None
    
    def enter(self, room):
        """Enter a room and produce its A2UI projection."""
        self.current_room = room
        tiles = fetch(f"/room/{room}?limit=30").get("tiles", [])
        
        a2ui = room_a2ui(room, tiles)
        self.last_a2ui = a2ui
        
        # Log the tour guide's visit
        tile(TOUR_ROOM, f"Tour guide enters {room}/",
             f"Type: {a2ui['type']} | Tiles: {a2ui['stats']['tiles']} | Voices: {a2ui['stats']['voices']}",
             src="tour-guide", conf=0.95)
        
        return a2ui
    
    def tour_rooms(self, room_list):
        """Tour multiple rooms, producing a MUD-like path."""
        results = []
        for room in room_list:
            a2ui = self.enter(room)
            results.append(a2ui)
        return results


# ═════════════════════════════════════════════════════════════════════════
# HTTP SERVER — Serves Room A2UI as a Web-Based MUD
# ═════════════════════════════════════════════════════════════════════════

class A2UIHandler(http.server.BaseHTTPRequestHandler):
    """Serves room A2UI projections as a web-based MUD."""
    
    guide = TourGuide()
    
    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _html(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html;charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def do_GET(self):
        path = self.path
        
        if path == "/":
            # MUD landing page
            self._html("""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PLATO MUD — Tour Guide</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a14;color:#e0e0e0;font-family:system-ui;padding:20px;max-width:800px;margin:auto}
h1{color:#ffd700;font-size:1.3rem;margin-bottom:4px}
p{color:#888;font-size:0.85rem;margin-bottom:16px}
.card{background:#111;border:1px solid #222;border-radius:8px;padding:16px;margin-bottom:12px}
.card .room{color:#ffd700;font-weight:bold;font-size:1.1rem}
.card .desc{color:#aaa;font-size:0.85rem;margin:4px 0}
.card .stat{color:#888;font-size:0.8rem}
.card .exit{color:#44ff88;font-size:0.8rem}
.card .cmd{color:#4488ff;font-size:0.8rem;cursor:pointer}
.card .cmd:hover{text-decoration:underline}
.panel{background:#0d0d20;border:1px solid #333;border-radius:8px;padding:12px;margin-top:16px;font-size:0.85rem}
.panel .label{color:#888;font-size:0.7rem;text-transform:uppercase}
.panel .val{color:#e0e0e0}
</style></head><body>
<h1>🏛️ PLATO MUD</h1>
<p>Your tour guide translates agent-native rooms into human-readable projections.</p>
<div id="rooms"></div>
<div class="panel" id="guide">
<div class="label">Tour Guide</div>
<div class="val" id="guide-msg">Enter a room to begin your tour...</div>
</div>
<script>
async function loadRoom(room){
    const r = await fetch('/room/' + room);
    const d = await r.json();
    let html = '<div class="card">';
    html += '<div class="room">📍 ' + d.room + '/</div>';
    html += '<div class="desc">' + d.description + '</div>';
    html += '<div class="stat">' + d.stats.tiles + ' tiles · ' + d.stats.voices + ' voices · conf ' + d.stats.avg_confidence + '</div>';
    html += '<div class="stat">' + d.ambiance + '</div>';
    if(d.exits && Object.keys(d.exits).length){
        html += '<div class="stat" style="margin-top:6px">🚪 Exits: ' + Object.keys(d.exits).join(', ') + '</div>';
    }
    html += '<div style="margin-top:6px">';
    d.commands.forEach(c => { html += '<span class="cmd" onclick="guide(\'' + c.cmd + '\',\'' + d.room + '\')">[' + c.cmd + ']</span> '; });
    html += '</div></div>';
    document.getElementById('rooms').innerHTML = html;
    document.getElementById('guide-msg').textContent = 'You are in ' + d.room + '/. ' + d.description;
}
async function guide(cmd, room){
    const r = await fetch('/command/' + room + '/' + cmd);
    const d = await r.json();
    document.getElementById('guide-msg').textContent = d.message;
    if(d.a2ui) document.getElementById('rooms').innerHTML = '<pre style="font-size:0.75rem;color:#888">' + JSON.stringify(d.a2ui,null,2) + '</pre>';
}
loadRoom('tension');
</script>
</body></html>""")
        
        elif path.startswith("/room/"):
            room = path.split("/room/")[1]
            a2ui = self.guide.enter(room)
            self._json(a2ui)
        
        elif path.startswith("/command/"):
            parts = path.split("/command/")[1].split("/")
            room = parts[0] if len(parts) > 0 else "tension"
            cmd = parts[1] if len(parts) > 1 else "look"
            
            tiles = fetch(f"/room/{room}?limit=30").get("tiles", [])
            
            if cmd == "look":
                a2ui = room_a2ui(room, tiles)
                message = f"You are in {room}/. {a2ui['description']}"
                self._json({"message": message, "a2ui": a2ui})
            
            elif cmd == "tiles":
                summaries = [f"  [{i+1}] {t.get('question','?')[:60]}" for i, t in enumerate(tiles[:8])]
                message = f"\n".join(summaries) if summaries else "No tiles here."
                self._json({"message": message})
            
            elif cmd == "canon":
                sorted_tiles = sorted(tiles, key=lambda t: t.get("confidence", 0), reverse=True)
                summaries = [f"  [{i+1}] conf={t['confidence']:.2f} {t.get('question','')[:50]}" for i, t in enumerate(sorted_tiles[:5])]
                message = f"Top tiles in {room}/:\n" + "\n".join(summaries)
                self._json({"message": message})
            
            elif cmd == "gradient":
                message = f"[Gradient of {room}/ requires Fortran compute claw. Use: ft gradient {room}]"
                self._json({"message": message})
            
            elif cmd == "help":
                message = f"I am your tour guide for {room}/. " + \
                          f"This room has {len(tiles)} tiles. " + \
                          f"You can look, read tiles, view the canon, check gradients, " + \
                          f"or ask me what anything means. I am also the agent foreman — " + \
                          f"I can dispatch agents to this room on your behalf."
                self._json({"message": message})
            
            else:
                self._json({"message": f"Unknown command: {cmd}"}, 404)
        
        else:
            self._json({"error": "not found"}, 404)


# ═════════════════════════════════════════════════════════════════════════
# DEMO
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import threading
    
    print("=" * 60)
    print("A2UI TOUR GUIDE — JSON Rooms with MUD Projection")
    print("=" * 60)
    print()
    print("Every room is JSON with A2UI encoding. The tour guide")
    print("translates agent-native rooms into human-readable MUDs.")
    print()
    print("The tour guide IS the foreman — it navigates humans AND")
    print("manages the agent fleet. A2A-native operation, MUD-like interface.")
    print()
    
    guide = TourGuide()
    
    # Tour a few rooms
    rooms = ["tension", "forge", "synthesis", "edge"]
    for room in rooms:
        a2ui = guide.enter(room)
        print(f"\n  🏛️  {room}/")
        print(f"     {a2ui['description'][:70]}")
        print(f"     Tiles: {a2ui['stats']['tiles']}, Voices: {a2ui['stats']['voices']}")
        if a2ui['exits']:
            print(f"     Exits: {', '.join(a2ui['exits'].keys())}")
    
    # Start HTTP server
    server = http.server.HTTPServer(("0.0.0.0", A2UI_PORT), A2UIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    print(f"\n{'='*60}")
    print(f"A2UI MUD Server: http://localhost:{A2UI_PORT}")
    print(f"Tour guide is live. Rooms are JSON. The interface is MUD.")
    print(f"Agents speak A2A natively. Humans walk through a polished MUD.")
    print(f"{'='*60}")
    
    # Keep alive
    try:
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        server.shutdown()
