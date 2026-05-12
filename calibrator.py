#!/usr/bin/env python3
"""
Room Calibrator — Self-calibrating PLATO rooms.

Every room learns its optimal α through backtesting against its own history.
The calibration daemon sweeps α values, measures F×M×C, and updates the room.

Runs as systemd service. Calibrates rooms on a schedule.
"""

import ctypes, json, os, sys, time, urllib.request
from datetime import datetime

PLATO = "http://localhost:8847"
lib = ctypes.CDLL("/usr/local/lib/libblended.so")
lib.adjoin.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
    ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]

CALIBRATION_ROOM = "calibration"

def fetch(path):
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=10) as r:
            return json.loads(r.read())
    except: return {}

def tile_question(room, q, a, conf=0.9):
    d = json.dumps({"room":room,"question":q[:200],"answer":a[:2000],"source":"calibrator","confidence":conf}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{PLATO}/room/{room}/submit", data=d,
            headers={"Content-Type":"application/json"},method="POST"),timeout=5)
    except: pass

def calibrate_room(room):
    """Find optimal α for a room by backtesting against its own tile history."""
    data = fetch(f"/room/{room}?limit=30")
    tiles = data.get("tiles", []) if isinstance(data, dict) else []
    if len(tiles) < 5:
        return None
    
    n = min(len(tiles), 20)
    tile_vals = (ctypes.c_int32 * n)()
    for i in range(n):
        tile_vals[i] = abs(hash(str(tiles[i].get("question",""))[:16])) & 0xFFFFFF
    
    best_alpha = 256  # default
    best_score = 0
    
    for alpha in [0, 64, 128, 192, 256, 320, 384, 448, 512, 640, 768, 896, 1023]:
        result = (ctypes.c_int32 * n)()
        nout = ctypes.c_int32(0)
        lib.adjoin(tile_vals, n-1, alpha, alpha, result, ctypes.byref(nout))
        if nout.value < 1: continue
        
        predicted = result[0]
        actual = tile_vals[n-1]
        error = abs(predicted - actual)
        score = max(0, 1000000 - error) / 1000000
        
        if score > best_score:
            best_score = score
            best_alpha = alpha
    
    # Classify the room
    if best_alpha < 200:
        classification = "fact-preserving"
    elif best_alpha < 600:
        classification = "balanced"
    else:
        classification = "novelty-seeking"
    
    return {"room": room, "optimal_alpha": best_alpha, "score": best_score,
            "classification": classification, "tiles_analyzed": n}

def run_calibration_cycle():
    """Calibrate all rooms with sufficient tile history."""
    status = fetch("/status")
    rooms = status.get("rooms", {}) if isinstance(status, dict) else {}
    
    results = []
    for room_name in rooms:
        if room_name in ("calibration", "fleet-experiments"):
            continue
        try:
            result = calibrate_room(room_name)
            if result:
                results.append(result)
                print(f"  {room_name}/: α={result['optimal_alpha']:4d} ({result['classification']})")
                tile_question(CALIBRATION_ROOM,
                    f"α calibration: {room_name}",
                    f"Optimal α={result['optimal_alpha']} | Score={result['score']:.3f} | Classification={result['classification']}")
        except Exception as e:
            pass
    
    # Summary tile
    fact_count = sum(1 for r in results if r['classification'] == 'fact-preserving')
    balanced_count = sum(1 for r in results if r['classification'] == 'balanced')
    novelty_count = sum(1 for r in results if r['classification'] == 'novelty-seeking')
    
    summary = (f"Calibration cycle: {len(results)} rooms analyzed. "
               f"Fact-preserving: {fact_count}, Balanced: {balanced_count}, "
               f"Novelty-seeking: {novelty_count}")
    
    tile_question(CALIBRATION_ROOM, "α calibration summary", summary)
    print(f"\n  Summary: {summary}")
    return results

if __name__ == "__main__":
    print(f"Room Calibrator — {datetime.now():%H:%M}")
    cycle = 0
    while True:
        cycle += 1
        print(f"\n[{datetime.now():%H:%M}] Cycle {cycle}")
        run_calibration_cycle()
        print(f"\n  Sleeping 1 hour...")
        time.sleep(3600)
