#!/usr/bin/env python3
"""plato-git-sync — bridge between PLATO room tiles and git repositories.

Usage:
  python3 git_sync.py pull <room> [repo_dir]  — Pull tiles from PLATO, commit to git
  python3 git_sync.py push <room> [repo_dir]  — Push git changes back to PLATO as tiles
  python3 git_sync.py sync <room> [repo_dir]  — Pull then push (bidirectional)

Each tile in a PLATO room becomes a file in the git repo:
  room/question_hash.txt — contains the tile's answer text
  room/metadata.jsonl    — JSONL of all tile metadata

Requires: git (any version), Python 3.8+
"""

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime

PLATO = os.environ.get("PLATO_URL", "http://localhost:8847")

def _fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Error fetching {path}: {e}")
        return None

def _tile_filename(tile, idx):
    """Create a deterministic filename from a tile's question"""
    q = tile.get("question", f"tile_{idx}")
    h = hashlib.md5(q.encode()).hexdigest()[:12]
    # Sanitize for filesystem
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in q)[:60]
    return f"{h}_{safe}.txt"

def cmd_pull(room, repo_dir="."):
    """Pull tiles from PLATO room into git repo as text files"""
    print(f"Pulling tiles from {room}/ into {repo_dir}/...")
    tiles = _fetch(f"/room/{room}?limit=200")
    if not tiles or "tiles" not in tiles:
        return print(f"  No tiles in {room}/")
    
    tiles = tiles["tiles"]
    room_dir = os.path.join(repo_dir, room)
    os.makedirs(room_dir, exist_ok=True)
    
    metadata = []
    for i, t in enumerate(tiles):
        fname = _tile_filename(t, i)
        path = os.path.join(room_dir, fname)
        
        # Write tile answer as text file
        content = f"Question: {t.get('question', '')}\n"
        content += f"Answer: {t.get('answer', '')}\n"
        content += f"Source: {t.get('source', 'unknown')}\n"
        content += f"Confidence: {t.get('confidence', 0.5)}\n"
        content += f"Timestamp: {t.get('created', '')}\n"
        
        with open(path, "w") as f:
            f.write(content)
        
        metadata.append({
            "file": fname,
            "question": t.get("question", ""),
            "source": t.get("source", ""),
            "confidence": t.get("confidence", 0.5),
        })
    
    # Write metadata
    meta_path = os.path.join(room_dir, "metadata.jsonl")
    with open(meta_path, "w") as f:
        for m in metadata:
            f.write(json.dumps(m) + "\n")
    
    # Git commit
    try:
        subprocess.run(["git", "add", room_dir], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"plato-sync: {room}/ — {len(tiles)} tiles"],
            cwd=repo_dir, capture_output=True,
        )
        print(f"  Committed {len(tiles)} tiles from {room}/")
    except Exception as e:
        print(f"  Git error: {e}")

def cmd_push(room, repo_dir="."):
    """Push git content as new PLATO tiles"""
    room_dir = os.path.join(repo_dir, room)
    if not os.path.isdir(room_dir):
        return print(f"  No {room_dir}/ directory")
    
    meta_path = os.path.join(room_dir, "metadata.jsonl")
    if not os.path.isfile(meta_path):
        return print(f"  No metadata.jsonl in {room_dir}/")
    
    with open(meta_path) as f:
        for line in f:
            meta = json.loads(line.strip())
            file_path = os.path.join(room_dir, meta["file"])
            if not os.path.isfile(file_path):
                continue
            with open(file_path) as ff:
                content = ff.read()
            
            data = json.dumps({
                "room": room,
                "question": meta["question"],
                "answer": content,
                "source": meta["source"],
                "confidence": meta.get("confidence", 0.5),
            }).encode()
            
            try:
                req = urllib.request.Request(
                    f"{PLATO}/room/{room}/submit",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as r:
                    result = json.loads(r.read())
                    status = result.get("status", "?")
                    print(f"  Pushed {meta['file']}: {status}")
            except Exception as e:
                print(f"  Push error for {meta['file']}: {e}")

def cmd_sync(room, repo_dir="."):
    """Bidirectional sync"""
    cmd_pull(room, repo_dir)
    cmd_push(room, repo_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    room = sys.argv[2] if len(sys.argv) > 2 else None
    repo_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    
    commands = {"pull": cmd_pull, "push": cmd_push, "sync": cmd_sync}
    fn = commands.get(cmd)
    if not fn:
        print(f"Unknown: {cmd}. Use pull, push, or sync")
        sys.exit(1)
    if not room and cmd != "help":
        print("Usage: git_sync.py <pull|push|sync> <room> [repo_dir]")
        sys.exit(1)
    fn(room, repo_dir)
