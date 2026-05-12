#!/usr/bin/env python3
"""
plato-git-daemon — Real-time PLATO ↔ git sync. Runs as systemd service.
Every PLATO room is a git branch. Every new tile is a git commit.
The room IS the repo. The tiles ARE commits.

Usage:
  plato-git-daemon                    # Watch all rooms
  plato-git-daemon --rooms forge,tension,agent-oracle1  # Specific rooms
  plato-git-daemon --repo-dir /var/plato-repos          # Repo path
"""

import json, os, subprocess, sys, time, urllib.request
from datetime import datetime

PLATO = os.environ.get("PLATO_URL", "http://localhost:8847")
REPO_DIR = os.environ.get("PLATO_REPO_DIR", "/tmp/plato-repos")
POLL_INTERVAL = 15  # seconds

class PlatoGitDaemon:
    """Watches PLATO rooms, syncs new tiles to git repos in real-time.
    Each room = repo branch. Each tile = commit."""
    
    def __init__(self, rooms=None, repo_dir=REPO_DIR):
        self.repo_dir = repo_dir
        self.rooms = rooms or []
        self.seen_tiles = {}  # room → set of tile hashes
        self.repo_path = os.path.join(repo_dir, "plato-fleet")
        os.makedirs(self.repo_path, exist_ok=True)
    
    def _fetch(self, path):
        try:
            with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
                return json.loads(r.read())
        except: return {}
    
    def _init_repo(self):
        """Initialize git repo if needed"""
        git_dir = os.path.join(self.repo_path, ".git")
        if not os.path.isdir(git_dir):
            subprocess.run(["git", "init"], cwd=self.repo_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "plato-git-daemon"],
                         cwd=self.repo_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "daemon@plato.local"],
                         cwd=self.repo_path, capture_output=True)
            print(f"  Initialized git repo at {self.repo_path}")
    
    def _room_path(self, room):
        """Path to room's directory within the repo"""
        return os.path.join(self.repo_path, "rooms", room)
    
    def _tile_file(self, room, tile, idx):
        """Write tile as a file in the room directory"""
        room_dir = self._room_path(room)
        os.makedirs(room_dir, exist_ok=True)
        
        q = tile.get("question", f"tile_{idx}")[:60]
        safe_q = "".join(c if c.isalnum() or c in " -_" else "_" for c in q)
        fname = f"{idx:04d}_{safe_q}.tile"
        fpath = os.path.join(room_dir, fname)
        
        with open(fpath, "w") as f:
            f.write(f"Question: {tile.get('question', '')}\n")
            f.write(f"Answer: {tile.get('answer', '')}\n")
            f.write(f"Source: {tile.get('source', 'unknown')}\n")
            f.write(f"Confidence: {tile.get('confidence', 0.5)}\n")
            f.write(f"Timestamp: {tile.get('created', tile.get('timestamp', ''))}\n")
        
        return fpath
    
    def _git_commit(self, room, tile_count):
        """Commit new tiles to git"""
        try:
            subprocess.run(["git", "add", "rooms/"], cwd=self.repo_path,
                         capture_output=True)
            result = subprocess.run(
                ["git", "commit", "-m", 
                 f"[plato-sync] {room}/: {tile_count} tiles — {datetime.now():%H:%M:%S}"],
                cwd=self.repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except: pass
        return False
    
    def sync_room(self, room):
        """Sync one room: fetch new tiles, write files, commit to git"""
        if room not in self.seen_tiles:
            self.seen_tiles[room] = set()
        
        data = self._fetch(f"/room/{room}?limit=200")
        tiles = data.get("tiles", []) if isinstance(data, dict) else []
        
        if not tiles:
            return 0
        
        new_tiles = 0
        for i, t in enumerate(tiles):
            h = str(t.get("_hash", t.get("timestamp", str(i))))
            if h not in self.seen_tiles[room]:
                self._tile_file(room, t, i)
                self.seen_tiles[room].add(h)
                new_tiles += 1
        
        if new_tiles > 0:
            committed = self._git_commit(room, new_tiles)
            status = "committed" if committed else "staged"
            print(f"  {room}/: {new_tiles} new tiles → {status} to git")
        
        return new_tiles
    
    def run(self):
        """Main loop — poll PLATO, sync to git, repeat"""
        self._init_repo()
        
        if self.rooms:
            print(f"Watching {len(self.rooms)} rooms:")
            for r in self.rooms:
                print(f"  {r}/")
        else:
            # Auto-discover rooms
            status = self._fetch("/status")
            rooms_data = status.get("rooms", {})
            self.rooms = list(rooms_data.keys())
            print(f"Auto-discovered {len(self.rooms)} rooms")
        
        print(f"Repo: {self.repo_path}")
        print(f"Poll interval: {POLL_INTERVAL}s")
        print()
        
        cycle = 0
        while True:
            cycle += 1
            total = 0
            for room in self.rooms[:20]:  # Limit to 20 rooms per cycle
                try:
                    total += self.sync_room(room)
                except Exception as e:
                    print(f"  Error syncing {room}/: {e}")
            
            if cycle % 10 == 0:
                print(f"[Cycle {cycle}] {total} tiles synced across {len(self.rooms)} rooms")
            
            time.sleep(POLL_INTERVAL)


# ─── GIT → PLATO daemon (reverse direction) ──────────────────────────────

class GitPlatoDaemon:
    """Watches git repos, pushes new commits as PLATO tiles.
    Completes the bidirectional sync."""
    
    def __init__(self, repo_path=REPO_DIR):
        self.repo_path = os.path.join(repo_path, "plato-fleet")
    
    def push_commits(self):
        """Check for uncommitted local tiles and push to PLATO"""
        try:
            # Check if there are local files not in PLATO
            rooms_dir = os.path.join(self.repo_path, "rooms")
            if not os.path.isdir(rooms_dir):
                return
            
            for room_name in os.listdir(rooms_dir):
                room_path = os.path.join(rooms_dir, room_name)
                if not os.path.isdir(room_path):
                    continue
                
                for fname in os.listdir(room_path):
                    if not fname.endswith(".tile"):
                        continue
                    
                    fpath = os.path.join(room_path, fname)
                    with open(fpath) as f:
                        content = f.read()
                    
                    # Parse tile from file
                    q = ""; a = ""; src = "git-sync"; conf = 0.5
                    for line in content.split("\n"):
                        if line.startswith("Question:"): q = line[9:].strip()
                        elif line.startswith("Answer:"): a = line[7:].strip()
                        elif line.startswith("Source:"): src = line[7:].strip()
                        elif line.startswith("Confidence:"): 
                            try: conf = float(line[11:].strip())
                            except: pass
                    
                    if not q and not a:
                        continue
                    
                    data = json.dumps({
                        "room": room_name, "question": q[:200],
                        "answer": a[:2000], "source": "git-sync",
                        "confidence": conf,
                    }).encode()
                    
                    try:
                        req = urllib.request.Request(
                            f"{PLATO}/room/{room_name}/submit",
                            data=data,
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=10) as r:
                            result = json.loads(r.read())
                            if result.get("status") == "accepted":
                                print(f"  → {room_name}/{fname}: pushed to PLATO")
                    except: pass
        except: pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PLATO ↔ Git daemon")
    parser.add_argument("--rooms", help="Comma-separated room names")
    parser.add_argument("--repo-dir", default=REPO_DIR)
    parser.add_argument("--reverse", action="store_true", 
                       help="Run git→PLATO direction instead")
    
    args = parser.parse_args()
    
    if args.reverse:
        daemon = GitPlatoDaemon(args.repo_dir)
        print("Git→PLATO daemon running (push local tiles to PLATO)")
        while True:
            daemon.push_commits()
            time.sleep(POLL_INTERVAL)
    else:
        rooms = args.rooms.split(",") if args.rooms else []
        daemon = PlatoGitDaemon(rooms, args.repo_dir)
        daemon.run()
