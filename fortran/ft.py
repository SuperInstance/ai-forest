#!/usr/bin/env python3
"""ft — PLATO compute toolkit. Native int32, no bit packing.

Built on Fortran native array operations + PLATO rooms.

SYNOPSIS
    ft plato                            — PLATO server status
    ft physics                          — Compute claw physics (latency, flops, SIMD)
    ft cat <room>                       — Read and display tiles from a room
    ft canon <room> [N]                 — Top N highest-confidence tiles
    ft contract <room_a> <room_b> [thr] — Contract two room tile sets through Fortran claw
    ft gradient <room>                  — Gradient across room tile history
    ft spline <room> <mu>               — Interpolate room state (mu: 0-1023)
    ft watch <room> [interval]          — Watch a room for new tiles (poll every N sec)
    ft benchmarks                       — Run benchmarks (Fortran direct + Zig ABI)
    ft help                             — This help text

COMMANDS
    plato
        Fetches GET /status from PLATO and displays:
          • Total rooms and tile count
          • Gate stats (accepted / rejected / top rejection reasons)  
          • Room-by-room breakdown with tile counts and creation dates

    physics
        Fetches GET /physics from the compute claw and shows:
          • Latency (ns)
          • FLOPs (floating-point ops/sec)
          • SIMD bit-width

    cat <room>
        Fetches tiles from GET /room/{name}?limit=50.
        Displays each tile as a table row with:
          • Index
          • Confidence (color-coded: green ≥0.9, yellow ≥0.7, red <0.7)
          • Source abbreviation
          • Question text (truncated to fit terminal)

    canon <room> [N]
        Fetches tiles from GET /room/{name}?limit=200.
        Sorts by confidence (descending) and shows top N (default: 10).
        Color-codes confidence values.

    contract <room_a> <room_b> [threshold]
        Reads all tile IDs from both PLATO rooms (limit=200 each).
        Posts to CLAW /contract with JSON body:
          {"room_a": [int32...], "room_b": [int32...],
           "na": N, "nb": N, "threshold": T}
        Displays result count and first 10 result values.

    gradient <room>
        Fetches tiles from GET /room/{name}?limit=100.
        Extracts a signed hash from each question.
        Posts to CLAW /gradient.
        Displays first 10 gradient deltas with corresponding question text.

    spline <room> <mu>
        Fetches tiles from GET /room/{name}?limit=50.
        Posts to CLAW /spline with before/after arrays and mu (0-1023).
        Displays number of result elements.

    watch <room> [interval]
        Polls PLATO every N seconds (default: 10) for GET /room/{name}.
        Prints new tiles as they appear.
        Runs until Ctrl+C. Tracks seen tile hashes to detect duplicates.

    benchmarks
        Loads the native compute libraries (Fortran libplato_math.so,
        Zig libft_zig.so) and runs:
          • Contract benchmarks (1K×1K, 5K×5K) — pairs/sec
          • Gradient benchmarks (10K, 100K elements) — elements/sec
          • Zig contract benchmark (1K×1K, 5K×5K) — pairs/sec
        Searches /usr/local/lib/ first, then /tmp/ai-forest/fortran/.

    help
        Prints this documentation.

ENVIRONMENT
    PLATO_URL     PLATO server (default: http://localhost:8847)
    CLAW_URL      Compute claw (default: http://localhost:4081)

EXIT CODES
    0  Success
    1  Usage error (missing arguments, unknown command)
    2  Network error (PLATO or CLAW unreachable)
    3  Library error (native .so not found)
"""

import ctypes
import json
import os
import sys
import time
import urllib.error
import urllib.request

PLATO = os.environ.get("PLATO_URL", "http://localhost:8847")
CLAW = os.environ.get("CLAW_URL", "http://localhost:4081")

# ─── ANSI color codes ────────────────────────────────────────────────
_COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "CYAN": "\033[96m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "RESET": "\033[0m",
}

def _color_confidence(conf):
    """Return green/yellow/red ANSI code for a confidence value."""
    if conf >= 0.9:
        return _COLORS["GREEN"]
    elif conf >= 0.7:
        return _COLORS["YELLOW"]
    return _COLORS["RED"]

def _colorize(text, color):
    """Wrap text in ANSI color, resetting afterward."""
    return f"{_COLORS[color]}{text}{_COLORS['RESET']}"

def _bold(text):
    return f"{_COLORS['BOLD']}{text}{_COLORS['RESET']}"

def _dim(text):
    return f"{_COLORS['DIM']}{text}{_COLORS['RESET']}"

# ─── Network helpers ─────────────────────────────────────────────────

def _fetch(path, timeout=10):
    """JSON GET from PLATO. Returns dict or raises on error."""
    try:
        with urllib.request.urlopen(f"{PLATO}{path}", timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        print(f"Error: cannot reach PLATO at {PLATO}: {e.reason}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON from PLATO: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: PLATO request failed: {e}", file=sys.stderr)
        sys.exit(2)


def _fetch_room(room, limit=50):
    """Fetch tiles from a PLATO room. Returns list of tiles."""
    data = _fetch(f"/room/{room}?limit={limit}")
    tiles = data.get("tiles", [])
    if not tiles:
        print(f"Info: room '{room}' has no tiles or does not exist", file=sys.stderr)
    return tiles


def _claw_post(endpoint, data, timeout=30):
    """JSON POST to CLAW. Returns dict or raises on error."""
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{CLAW}{endpoint}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        print(f"Error: cannot reach CLAW at {CLAW}: {e.reason}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON from CLAW: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: CLAW request failed: {e}", file=sys.stderr)
        sys.exit(2)


# ─── Library helpers ─────────────────────────────────────────────────

def _find_lib(name):
    """Find a shared library. Checks /usr/local/lib/ first, then fallback."""
    paths = [
        f"/usr/local/lib/{name}",
        f"/tmp/ai-forest/fortran/{name}",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _load_libs():
    """Load Fortran and Zig libraries. Exits with code 3 if not found."""
    fortran_path = _find_lib("libplato_math.so")
    zig_path = _find_lib("libft_zig.so")

    if not fortran_path:
        print("Error: libplato_math.so not found in /usr/local/lib/ or /tmp/ai-forest/fortran/",
              file=sys.stderr)
        sys.exit(3)

    lib_f = ctypes.CDLL(fortran_path)
    lib_z = None
    if zig_path:
        lib_z = ctypes.CDLL(zig_path)
        lib_z.ft_contract.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32,
        ]
        lib_z.ft_contract.restype = ctypes.c_int32

    return lib_f, lib_z


# ─── Commands ────────────────────────────────────────────────────────

def cmd_plato(args):
    """PLATO server status: rooms, tiles, gate stats."""
    s = _fetch("/status")
    rooms = s.get("rooms", {})
    gate = s.get("gate_stats", {})

    if not rooms:
        print("PLATO status: active, no rooms yet")
        return

    total_tiles = sum(r.get("tile_count", 0) for r in rooms.values())
    print(f"{_bold('PLATO Status')}")
    print(f"  Version:  {s.get('version', 'unknown')}")
    print(f"  Uptime:   {_format_uptime(s.get('uptime', 0))}")
    print(f"  Rooms:    {len(rooms)}")
    print(f"  Tiles:    {total_tiles}")
    print()

    if gate:
        accepted = gate.get("accepted", 0)
        rejected = gate.get("rejected", 0)
        print(f"{_bold('Gate Stats')}")
        print(f"  Accepted: {accepted}")
        print(f"  Rejected: {rejected}")
        reasons = gate.get("reasons", {})
        if reasons:
            print(f"  Top rejection reasons:")
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:5]:
                print(f"    • {reason}: {count}")
        print()

    # Room list with tile counts
    print(f"{_bold('Rooms')}")
    by_tiles = sorted(rooms.items(), key=lambda kv: -kv[1].get("tile_count", 0))
    header = f"  {'ROOM':<30} {'TILES':>6} {'CREATED':<20}"
    print(header)
    print(f"  {'-'*30} {'-'*6} {'-'*20}")
    for name, info in by_tiles:
        tc = info.get("tile_count", 0)
        created = info.get("created", "?")[:19]
        print(f"  {name:<30} {tc:>6} {created:<20}")


def _format_uptime(seconds):
    """Format uptime seconds into human-readable string."""
    seconds = int(time.time() - seconds) if seconds > 1e10 else int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def cmd_physics(args):
    """Compute claw physics: latency, flops, SIMD."""
    try:
        with urllib.request.urlopen(f"{CLAW}/physics", timeout=5) as r:
            p = json.loads(r.read())
    except urllib.error.URLError:
        print(f"Error: cannot reach compute claw at {CLAW}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: physics check failed: {e}", file=sys.stderr)
        sys.exit(2)

    latency = p.get("latency_ns", 0)
    flops = p.get("flops", 0)
    simd = p.get("simd_bits", 0)

    print(f"{_bold('Compute Claw Physics')}")
    print(f"  Latency:   {_colorize(f'{latency:.1f} ns', 'GREEN')}")
    print(f"  FLOPs:     {flops:.2e}")
    print(f"  SIMD:      {_colorize(f'{simd}-bit', 'CYAN')}")


def cmd_cat(args):
    """Read and display tiles from a room with confidence colors."""
    if not args:
        print("Usage: ft cat <room>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    tiles = _fetch_room(room, limit=50)

    if not tiles:
        return

    # Terminal-width safe: question column fills remaining space
    # Format: [idx] conf  source  question
    conf_w = 5  # "0.000"
    src_w = 18
    print(f"{_bold(f'Room: {room}')}  ({len(tiles)} tiles)")
    print()
    for i, t in enumerate(tiles):
        conf = t.get("confidence", 0.0)
        source = (t.get("source", "") or "")[:src_w]
        q = (t.get("question", "") or "").strip()
        # Truncate question to terminal width minus fixed columns
        term_w = _term_width()
        q_max = term_w - conf_w - src_w - 12
        if q_max < 10:
            q_max = 60
        q_display = q[:q_max]
        if len(q) > q_max:
            q_display += "…"

        conf_color = _color_confidence(conf)
        conf_str = f"{conf_color}{conf:.2f}{_COLORS['RESET']}"
        print(f"  [{i:3d}] {conf_str}  {_dim(source):{src_w}s}  {q_display}")


def _term_width():
    """Get terminal width, default to 100."""
    try:
        import shutil
        return shutil.get_terminal_size((100, 24)).columns
    except Exception:
        return 100


def cmd_canon(args):
    """Top N highest-confidence tiles from a room."""
    if not args:
        print("Usage: ft canon <room> [N]", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    n = 10
    if len(args) > 1:
        try:
            n = int(args[1])
        except ValueError:
            print(f"Error: N must be a number, got '{args[1]}'", file=sys.stderr)
            sys.exit(1)

    tiles = _fetch_room(room, limit=200)
    if not tiles:
        return

    # Sort by confidence descending
    sorted_tiles = sorted(tiles, key=lambda t: -(t.get("confidence", 0) or 0))
    top = sorted_tiles[:n]

    print(f"{_bold(f'Top {len(top)} of {len(tiles)} tiles in {room}')}")
    print()

    # Header
    term_w = _term_width()
    conf_w = 6
    src_w = 18
    q_max = term_w - conf_w - src_w - 12
    if q_max < 10:
        q_max = 60

    print(f"  {'#':>3}  {'CONF':>{conf_w}s}  {'SOURCE':{src_w}s}  QUESTION")
    print(f"  {'---':>3s}  {'------':>{conf_w}s}  {'------------------':{src_w}s}  {'-------':>{q_max}s}")
    for i, t in enumerate(top):
        conf = t.get("confidence", 0.0)
        source = (t.get("source", "") or "")[:src_w]
        q = (t.get("question", "") or "").strip()[:q_max]
        conf_color = _color_confidence(conf)
        conf_str = f"{conf_color}{conf:.3f}{_COLORS['RESET']}"
        print(f"  [{i+1:>2d}] {conf_str}  {_dim(source):{src_w}s}  {q}")


def cmd_contract(args):
    """Contract two room tile sets through Fortran compute claw."""
    if len(args) < 2:
        print("Usage: ft contract <room_a> <room_b> [threshold]", file=sys.stderr)
        sys.exit(1)

    a_name, b_name = args[0], args[1]
    threshold = 100
    if len(args) > 2:
        try:
            threshold = int(args[2])
        except ValueError:
            print(f"Error: threshold must be an integer, got '{args[2]}'", file=sys.stderr)
            sys.exit(1)

    # Fetch rooms
    print(f"Fetching room '{a_name}'…")
    tiles_a = _fetch_room(a_name, limit=200)
    print(f"Fetching room '{b_name}'…")
    tiles_b = _fetch_room(b_name, limit=200)

    na, nb = len(tiles_a), len(tiles_b)
    if na == 0 or nb == 0:
        print(f"Error: one or both rooms are empty", file=sys.stderr)
        sys.exit(2)

    # Extract hash values for contract (use _hash or generated)
    vals_a = [int(t.get("_hash", "0")[:8], 16) % 0x7FFFFFFF for t in tiles_a]
    vals_b = [int(t.get("_hash", "0")[:8], 16) % 0x7FFFFFFF for t in tiles_b]

    payload = {
        "room_a": vals_a,
        "room_b": vals_b,
        "na": na,
        "nb": nb,
        "threshold": threshold,
    }
    print(f"Contracting {na}×{nb} tiles, threshold={threshold}…")
    r = _claw_post("/contract", payload)

    nresult = r.get("nresult", 0)
    results = r.get("results", [])
    print(f"{_bold('Contract Results')}")
    print(f"  Pairs above threshold: {_colorize(str(nresult), 'GREEN')}")

    if results:
        print(f"  First {min(10, len(results))} values: ", end="")
        preview = ", ".join(str(v) for v in results[:10])
        print(preview)


def cmd_gradient(args):
    """Gradient across room tile history."""
    if not args:
        print("Usage: ft gradient <room>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    tiles = _fetch_room(room, limit=100)
    if not tiles:
        return

    # Extract signed hash from each question
    vals = []
    for t in tiles:
        q = (t.get("question", "") or "").strip()
        h = hash(q[:16]) & 0x7FFFFFFF
        vals.append(h)

    payload = {"tiles": vals, "n": len(vals)}
    r = _claw_post("/gradient", payload)
    gradients = r.get("gradients", [])

    print(f"{_bold(f'Gradient across {len(vals)} tiles in {room}')}")
    print()
    for i, g in enumerate(gradients[:10]):
        q = (tiles[i].get("question", "") or "").strip()[:50]
        if len(q) >= 50:
            q += "…"
        # Color large deltas
        g_abs = abs(g)
        if g_abs > 1000000:
            g_str = _colorize(f"{g:10d}", "RED")
        elif g_abs > 100000:
            g_str = _colorize(f"{g:10d}", "YELLOW")
        else:
            g_str = _colorize(f"{g:10d}", "DIM")
        print(f"  [{i:3d}] Δ={g_str}  {q}")

    if len(gradients) > 10:
        print(f"  … and {len(gradients) - 10} more")


def cmd_spline(args):
    """Interpolate room state (mu: 0-1023)."""
    if not args:
        print("Usage: ft spline <room> <mu>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    mu = 512
    if len(args) > 1:
        try:
            mu = int(args[1])
            if mu < 0 or mu > 1023:
                print(f"Warning: mu should be 0-1023, got {mu}", file=sys.stderr)
        except ValueError:
            print(f"Error: mu must be an integer, got '{args[1]}'", file=sys.stderr)
            sys.exit(1)

    tiles = _fetch_room(room, limit=50)
    if not tiles:
        return

    # Extract hash values for before, double for after
    vals = []
    for t in tiles:
        q = (t.get("question", "") or "").strip()
        h = hash(q[:16]) & 0x7FFFFFFF
        vals.append(h)

    payload = {
        "before": vals,
        "after": [v * 2 for v in vals],
        "n": len(vals),
        "mu": mu,
    }
    r = _claw_post("/spline", payload)
    result = r.get("result", [])

    print(f"{_bold(f'Spline {room}')}")
    print(f"  mu={mu}/1023  |before|={len(vals)}  |result|={len(result)}")
    if result:
        print(f"  First 5: {', '.join(str(v) for v in result[:5])}")


def cmd_watch(args):
    """Watch a room for new tiles, polling every N seconds."""
    if not args:
        print("Usage: ft watch <room> [interval]", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    interval = 10
    if len(args) > 1:
        try:
            interval = float(args[1])
            if interval < 0.5:
                print("Warning: minimum interval is 0.5s, clamping", file=sys.stderr)
                interval = 0.5
        except ValueError:
            print(f"Error: interval must be a number, got '{args[1]}'", file=sys.stderr)
            sys.exit(1)

    print(f"Watching room '{_bold(room)}' every {interval}s…")
    print("Press Ctrl+C to stop.")
    print()

    seen = set()
    try:
        while True:
            tiles = _fetch_room(room, limit=200)
            if tiles:
                for t in tiles:
                    tile_hash = t.get("_hash", "")
                    if tile_hash and tile_hash not in seen:
                        seen.add(tile_hash)
                        conf = t.get("confidence", 0.0)
                        q = (t.get("question", "") or "").strip()
                        a = (t.get("answer", "") or "").strip()
                        source = t.get("source", "?")
                        now = time.strftime("%H:%M:%S")
                        conf_color = _color_confidence(conf)
                        print(f"{_dim(f'[{now}]')} {conf_color}{conf:.2f}{_COLORS['RESET']}  "
                              f"{_dim(source):>12s}  {_bold(q)}")
                        if a:
                            # Print answer shortened
                            a_short = a[:100].replace("\n", " ")
                            if len(a) > 100:
                                a_short += "…"
                            print(f"           {_dim(a_short)}")
                        print()
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        print(f"Stopped. Seen {len(seen)} unique tiles.")


def cmd_benchmarks(args):
    """Run benchmarks: Fortran direct + Zig ABI."""
    lib_f, lib_z = _load_libs()

    print(f"{_bold('Benchmarks')}")
    print()

    # ── Fortran contract ──
    print(f"{_colorize('Fortran Contract', 'CYAN')}")
    for na, nb in [(1000, 1000), (5000, 5000)]:
        a = (ctypes.c_int32 * na)()
        b = (ctypes.c_int32 * nb)()
        for i in range(na):
            a[i] = i * 1000
        for i in range(nb):
            b[i] = i * 1000 + 500
        nr = ctypes.c_int32(0)
        t0 = time.perf_counter()
        lib_f.contract(a, na, b, nb, ctypes.c_int32(10000), ctypes.byref(nr))
        dt = time.perf_counter() - t0
        rate = na * nb / dt / 1e6 if dt > 0 else 0
        print(f"  Contract {na}×{nb}: {dt*1000:.1f}ms  {rate:.0f}M pairs/s   ({_bold(str(nr.value))} results)")

    # ── Fortran gradient ──
    print()
    print(f"{_colorize('Fortran Gradient', 'CYAN')}")
    for n in [10000, 100000]:
        a = (ctypes.c_int32 * n)()
        for i in range(n):
            a[i] = i * 100
        g = (ctypes.c_int32 * n)()
        t0 = time.perf_counter()
        lib_f.gradient(a, n, g)
        dt = time.perf_counter() - t0
        rate = n / dt / 1e6 if dt > 0 else 0
        print(f"  Gradient {n}: {dt*1000:.3f}ms  {rate:.0f}M elem/s")

    # ── Zig contract ──
    if lib_z:
        print()
        print(f"{_colorize('Zig Contract', 'CYAN')}")
        for n in [1000, 5000]:
            a = (ctypes.c_int32 * n)()
            b = (ctypes.c_int32 * n)()
            for i in range(n):
                a[i] = i * 1000
                b[i] = i * 1000 + 500
            t0 = time.perf_counter()
            nr = lib_z.ft_contract(a, n, b, n, 10000)
            dt = time.perf_counter() - t0
            rate = n * n / dt / 1e6 if dt > 0 else 0
            print(f"  Zig contract {n}×{n}: {dt*1000:.1f}ms  {rate:.0f}M pairs/s   ({_bold(str(nr))} results)")
    else:
        print()
        print(f"{_colorize('Zig Contract', 'YELLOW')}")
        print(f"  libft_zig.so not found — skipping Zig benchmarks")


def cmd_help(args):
    """Comprehensive help (this text)."""
    print(__doc__.strip())


# ─── Command registry ────────────────────────────────────────────────
COMMANDS = {
    "plato": cmd_plato,
    "physics": cmd_physics,
    "cat": cmd_cat,
    "canon": cmd_canon,
    "contract": cmd_contract,
    "gradient": cmd_gradient,
    "spline": cmd_spline,
    "watch": cmd_watch,
    "benchmarks": cmd_benchmarks,
    "bench": cmd_benchmarks,
    "help": cmd_help,
    "-h": cmd_help,
    "--help": cmd_help,
}


def _usage():
    """Print short usage and exit."""
    print("Usage: ft <command> [args]")
    print()
    print("Commands:")
    for name in ["plato", "physics", "cat", "canon", "contract", "gradient", "spline", "watch", "benchmarks", "help"]:
        fn = COMMANDS[name]
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        print(f"  {name:<14s}  {doc}")
    print()
    print("See 'ft help' for full documentation.")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        _usage()

    cmd = sys.argv[1]
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(k for k in sorted(COMMANDS) if not k.startswith('-'))}",
              file=sys.stderr)
        sys.exit(1)

    try:
        fn(sys.argv[2:])
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()
