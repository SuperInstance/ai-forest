#!/usr/bin/env python3
"""
PLATO Actor Agent — A tiny model trained to play PLATO like a professional.

Each actor is a PLATO-native agent constructed from room tiles:
1. Enter a room → read tiles → construct a room-bot (algorithmic chatbot from tiles)
2. Act in the room → contribute new tiles based on what you learned
3. Follow cross-references → cascade to the next room (like MoE token routing)
4. No tile? → casting call → spawn a new actor for the missing role

The actor changes costumes (room context) as it dances through rooms,
playing all the parts in the play. The knowledge is in the tiles.
The actor IS the tile stream.
"""

import json, os, sys, time, urllib.request, random, hashlib

PLATO = "http://localhost:8847"
ACTOR_ROOM = "actor-dance"
SPEED = 0.3  # seconds between dance steps

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile(room, q, a, src="actor", conf=0.85):
    d = json.dumps({"room":room,"question":str(q)[:200],"answer":str(a)[:2000],"source":src,"confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit",data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass

# ─── The Room-Bot — An algorithmic chatbot constructed from PLATO tiles ───
#
# When an actor enters a room, it reads the recent tiles. Those tiles ARE
# the bot's "model" — the knowledge that guides its responses. No weights,
# no training. Just tiles constructed by previous generations of actors.

class RoomBot:
    """An algorithmic chatbot built from a room's tiles.
    
    The room-bot's knowledge = the room's tiles.
    It doesn't generate text — it selects and recombines existing tiles
    based on the query, following the adjunction framework.
    """
    
    def __init__(self, room, tiles=None):
        self.room = room
        self.tiles = tiles or []
        self.confidence = sum(t.get("confidence", 0.5) for t in self.tiles) / max(len(self.tiles), 1)
    
    @classmethod
    def from_room(cls, room, limit=30):
        tiles = fetch(f"/room/{room}?limit={limit}").get("tiles", [])
        return cls(room, tiles)
    
    def respond(self, query):
        """Respond to a query using the room's tiles as knowledge.
        
        This is a simplified "algorithmic chatbot" — in production, this
        would use seed cycle permutation + blending on tile content.
        For this demo, it selects the most relevant tile by keyword match
        and produces a response based on the tile's content.
        """
        if not self.tiles:
            return None, 0.0
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        best_tile = None
        best_score = 0
        
        for t in self.tiles:
            q = t.get("question", "").lower()
            a = t.get("answer", "").lower()
            combined = q + " " + a
            score = sum(1 for w in query_words if w in combined) / max(len(query_words), 1)
            score *= t.get("confidence", 0.5)
            
            if score > best_score:
                best_score = score
                best_tile = t
        
        if best_tile:
            q = best_tile.get("question", "")
            a = best_tile.get("answer", "")[:100]
            return f"From {self.room}/: {a}", best_score
        
        return None, 0.0
    
    def has_knowledge(self):
        return len(self.tiles) >= 3 and self.confidence > 0.3


class CastingCall:
    """When a room has no tiles, Casting Call finds or creates the right actor.
    
    In production, this would spawn a MiniMax/Seed call to generate the
    first tile. For this demo, it creates a seed tile from the room name.
    """
    
    @staticmethod
    def cast(room, reason="no tiles"):
        seed_question = f"First tile for {room}/"
        seed_answer = f"Cast from {reason}. Room initialized. Ready for dance."
        tile(room, seed_question, seed_answer, src="casting-call", conf=0.5)
        return f"Actor cast for {room}/: seed tile created"


class Actor:
    """A PLATO-native agent that dances through rooms.
    
    Each actor:
    1. Enters a room → constructs a room-bot from tiles
    2. Responds to the room's context → contributes new tiles
    3. Follows cross-references → cascades to the next room
    4. If no tiles in the next room → casting call → seed it
    """
    
    def __init__(self, name="actor-1"):
        self.name = name
        self.current_room = None
        self.bot = None
        self.path = []
    
    def costume(self, room):
        """Enter a room — put on the costume (construct room-bot)."""
        self.current_room = room
        self.bot = RoomBot.from_room(room)
        self.path.append(room)
        
        knowledge = "knowledge" if self.bot.has_knowledge() else "no tiles — need casting"
        print(f"\n  🎭 {self.name} enters {room}/ ({knowledge})")
        
        if not self.bot.has_knowledge():
            result = CastingCall.cast(room)
            print(f"     {result}")
            self.bot = RoomBot.from_room(room)
        
        return self.bot
    
    def act(self, query):
        """Perform in the current room — respond, tile, dance."""
        if not self.bot:
            return None
        
        response, confidence = self.bot.respond(query)
        
        if response:
            # Contribute a new tile to the room
            tile(self.current_room, f"{self.name} acts: {query[:30]}",
                 f"Response from {self.current_room}/: {response[:150]}",
                 src=self.name, conf=confidence)
            print(f"     💬 Tiled to {self.current_room}/ (conf={confidence:.2f})")
        
        return response
    
    def find_exits(self):
        """Find cross-references to other rooms (the exits from this room)."""
        tiles = fetch(f"/room/{self.current_room}?limit=20").get("tiles", [])
        if not tiles:
            return []
        
        all_text = " ".join(
            t.get("question", "") + " " + t.get("answer", "") 
            for t in tiles
        ).lower()
        
        # Known room keywords
        room_keywords = {
            "tension": "tension",
            "forge": "forge", 
            "synthesis": "synthesis",
            "edge": "edge",
            "calibration": "calibrat",
            "innovation": "innovation",
            "question": "question",
            "swarm": "swarm",
            "murmur": "murmur",
        }
        
        exits = []
        for room, keyword in room_keywords.items():
            if keyword in all_text:
                exits.append(room)
        
        return exits
    
    def dance(self, entry_room, query, max_steps=5):
        """Full dance through rooms.
        
        1. Enter room (costume change)
        2. Act in room (construct bot, respond, tile)
        3. Find exits (cross-references to other rooms)
        4. Follow next exit (cascade)
        5. Repeat until max_steps or no exits
        """
        print(f"\n{'='*60}")
        print(f"DANCE: {self.name} enters {entry_room}/")
        print(f"Query: {query[:60]}")
        print(f"{'='*60}")
        
        current = entry_room
        for step in range(max_steps):
            # Enter room (change costume)
            bot = self.costume(current)
            
            # Act in room
            response = self.act(query)
            if response:
                print(f"     🗣️  {response[:80]}")
            
            time.sleep(SPEED)
            
            # Find exits (cross-references)
            exits = self.find_exits()
            exits = [e for e in exits if e not in self.path]
            
            if not exits:
                print(f"\n  ✨ Dance complete — no more exits from {current}/")
                break
            
            # Cascade to next room (follow the MoE routing)
            next_room = exits[0]
            print(f"     🚪 Exit via cross-reference → {next_room}/")
            current = next_room
            time.sleep(SPEED)
        
        print(f"\n  🏁 Dance path: {' → '.join(self.path[:max_steps+1])}")
        return self.path


# ─── Demo ───

if __name__ == "__main__":
    print("=" * 60)
    print("PLATO ACTOR AGENT — Dance of Meaning and Response")
    print("=" * 60)
    print()
    print("Each actor enters a room, constructs a room-bot from tiles,")
    print("acts, tiles, and follows cross-references to the next room.")
    print("No external LLM needed except as bootstrap (casting call).")
    
    actor = Actor("oracle1")
    path = actor.dance("tension", "What is the nature of constraint in creative systems?", max_steps=5)
    
    print(f"\nThe actor danced through {len(path)} rooms, playing each part.")
    print("The knowledge was in the tiles. The actor was the tile stream.")
