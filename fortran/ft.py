#!/usr/bin/env python3
"""ft — PLATO compute toolkit. Native int32 array operations.

A production-quality CLI for PLATO room operations backed by Fortran
native array operations and an optional Zig bridge layer.

Usage:
    ft plato                    Server status
    ft physics                  Compute claw physics (latency, flops, SIMD)
    ft cat <room>               Read room tiles
    ft canon <room> [N]         Top N highest-confidence tiles
    ft contract <a> <b> [t]     Contract two rooms through Fortran claw
    ft gradient <room>          Gradient across tile history
    ft spline <room> <mu>       Interpolate room state (mu: 0-1023)
    ft watch <room> [i]         Watch room for new tiles (poll every i sec)
    ft bench                    Run all benchmarks (Fortran + Zig)
    ft zig                      Run Zig-specific benchmarks
    ft window-contract <a> <b> <w> [t]  Temporal contract with time window
    ft recency-dot <room>       Recency-weighted dot product
    ft window-gradient <r> [w]  Smoothed gradient over sliding window
    ft help                     Comprehensive help text

Environment:
    PLATO_URL  PLATO server base URL (default: http://localhost:8847)
    CLAW_URL   Compute claw base URL (default: http://localhost:4081)

Exit codes:
    0  Success
    1  Usage error (missing arguments, unknown command)
    2  Network error (PLATO/CLAW unreachable or malformed response)
    3  Library error (native .so not found or load failure)
"""

from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ─── ANSI color constants ─────────────────────────────────────────────────
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _color(text: str, ansi: str) -> str:
    return f"{ansi}{text}{_RESET}"


def green(text: str) -> str:
    return _color(text, _GREEN)


def yellow(text: str) -> str:
    return _color(text, _YELLOW)


def red(text: str) -> str:
    return _color(text, _RED)


def cyan(text: str) -> str:
    return _color(text, _CYAN)


def bold(text: str) -> str:
    return _color(text, _BOLD)


def dim(text: str) -> str:
    return _color(text, _DIM)


def confidence_color(conf: float) -> str:
    """Return green/yellow/red based on confidence threshold."""
    if conf >= 0.9:
        return _GREEN
    if conf >= 0.7:
        return _YELLOW
    return _RED


# ─── Configuration ──────────────────────────────────────────────────────────

@dataclass
class Config:
    """Global configuration loaded from environment."""
    plato_url: str = field(default_factory=lambda: os.environ.get("PLATO_URL", "http://localhost:8847"))
    claw_url: str = field(default_factory=lambda: os.environ.get("CLAW_URL", "http://localhost:4081"))
    http_timeout: int = 10
    claw_timeout: int = 30
    bench_library_paths: Tuple[str, ...] = (
        "/usr/local/lib",
        "/tmp/ai-forest/fortran",
        "/tmp/ai-forest/zig",
    )


_CONF = Config()


# ─── Terminal helpers ──────────────────────────────────────────────────────

def _terminal_width(fallback: int = 100) -> int:
    try:
        return shutil.get_terminal_size((fallback, 24)).columns
    except Exception:
        return fallback


def _format_uptime(seconds: float) -> str:
    """Format an uptime delta (seconds or Unix timestamp) as human-readable."""
    secs = int(seconds)
    # If it looks like a Unix timestamp (> 1e10), compute delta from now
    if seconds > 1e10:
        secs = int(time.time() - seconds)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


# ─── PlatoClient ────────────────────────────────────────────────────────────

class PlatoClient:
    """HTTP client for PLATO server interactions."""

    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_json(self, path: str, *, label: str = "PLATO") -> Any:
        """GET a JSON resource from PLATO. Exits on network/parse error."""
        url = self._url(path)
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.URLError as e:
            print(f"{red('Error')}: cannot reach {label} at {url}: {e.reason}", file=sys.stderr)
            sys.exit(2)
        except json.JSONDecodeError as e:
            print(f"{red('Error')}: invalid JSON from {label}: {e}", file=sys.stderr)
            sys.exit(2)
        except Exception as e:
            print(f"{red('Error')}: {label} request failed: {e}", file=sys.stderr)
            sys.exit(2)

    def fetch_status(self) -> Dict[str, Any]:
        return self.get_json("/status")

    def fetch_room(self, name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch tiles from a PLATO room. Returns empty list on missing room."""
        data = self.get_json(f"/room/{name}?limit={limit}")
        tiles: List[Dict[str, Any]] = data.get("tiles", [])
        return tiles


# ─── ComputeClaw (Native Fortran/Zig) ─────────────────────────────────────

class _FortranLib:
    """Wrapper around ctypes-loaded Fortran/C shared library."""

    def __init__(self, lib: ctypes.CDLL) -> None:
        self._lib = lib
        self._setup_prototypes()

    def _setup_prototypes(self) -> None:
        L = self._lib
        # contract(a, na, b, nb, threshold, &nresult)
        L.contract.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
        ]
        L.contract.restype = None

        # dot(a, b, n, &result)
        L.dot.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.c_int32, ctypes.POINTER(ctypes.c_int64),
        ]
        L.dot.restype = None

        # spline(before, after, n, mu, result)
        L.spline.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.c_int32, ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32),
        ]
        L.spline.restype = None

        # gradient(arr, n, result)
        L.gradient.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32),
        ]
        L.gradient.restype = None

        # physics(&latency_ns, &flops, &simd_bits)
        L.physics.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int32),
        ]
        L.physics.restype = None

        # filter_val(arr, n, target, tolerance, indices, &n_found)
        L.filter_val.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32, ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
        ]
        L.filter_val.restype = None

        # window_contract(time_a, a, na, time_b, b, nb, window, threshold, &nresult)
        L.window_contract.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
        ]
        L.window_contract.restype = None

        # recency_dot(a, time_a, b, time_b, n, &result)
        L.recency_dot.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.c_int32, ctypes.POINTER(ctypes.c_int64),
        ]
        L.recency_dot.restype = None

        # window_gradient(arr, n, window, result)
        L.window_gradient.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
        ]
        L.window_gradient.restype = None

    def contract(
        self,
        a: Sequence[int], na: int,
        b: Sequence[int], nb: int,
        threshold: int,
    ) -> int:
        arr_a = (ctypes.c_int32 * na)(*a)
        arr_b = (ctypes.c_int32 * nb)(*b)
        nresult = ctypes.c_int32(0)
        self._lib.contract(arr_a, na, arr_b, nb, threshold, ctypes.byref(nresult))
        return nresult.value

    def dot(self, a: Sequence[int], b: Sequence[int], n: int) -> int:
        arr_a = (ctypes.c_int32 * n)(*a)
        arr_b = (ctypes.c_int32 * n)(*b)
        result = ctypes.c_int64(0)
        self._lib.dot(arr_a, arr_b, n, ctypes.byref(result))
        return result.value

    def gradient(self, arr: Sequence[int], n: int) -> List[int]:
        arr_in = (ctypes.c_int32 * n)(*arr)
        result = (ctypes.c_int32 * n)()
        self._lib.gradient(arr_in, n, result)
        return [result[i] for i in range(n)]

    def spline(self, before: Sequence[int], after: Sequence[int],
               n: int, mu: int) -> List[int]:
        arr_before = (ctypes.c_int32 * n)(*before)
        arr_after = (ctypes.c_int32 * n)(*after)
        result = (ctypes.c_int32 * n)()
        self._lib.spline(arr_before, arr_after, n, mu, result)
        return [result[i] for i in range(n)]

    def physics(self) -> Tuple[float, float, int]:
        lat = ctypes.c_float(0.0)
        flops = ctypes.c_float(0.0)
        simd = ctypes.c_int32(0)
        self._lib.physics(ctypes.byref(lat), ctypes.byref(flops), ctypes.byref(simd))
        return (lat.value, flops.value, simd.value)

    def window_contract(
        self,
        time_a: Sequence[int], a: Sequence[int], na: int,
        time_b: Sequence[int], b: Sequence[int], nb: int,
        window: int, threshold: int,
    ) -> int:
        arr_ta = (ctypes.c_int32 * na)(*time_a)
        arr_a = (ctypes.c_int32 * na)(*a)
        arr_tb = (ctypes.c_int32 * nb)(*time_b)
        arr_b = (ctypes.c_int32 * nb)(*b)
        nresult = ctypes.c_int32(0)
        self._lib.window_contract(
            arr_ta, arr_a, na, arr_tb, arr_b, nb,
            window, threshold, ctypes.byref(nresult),
        )
        return nresult.value

    def recency_dot(
        self, a: Sequence[int], time_a: Sequence[int],
        b: Sequence[int], time_b: Sequence[int], n: int,
    ) -> int:
        arr_a = (ctypes.c_int32 * n)(*a)
        arr_ta = (ctypes.c_int32 * n)(*time_a)
        arr_b = (ctypes.c_int32 * n)(*b)
        arr_tb = (ctypes.c_int32 * n)(*time_b)
        result = ctypes.c_int64(0)
        self._lib.recency_dot(arr_a, arr_ta, arr_b, arr_tb, n, ctypes.byref(result))
        return result.value

    def window_gradient(self, arr: Sequence[int], n: int, window: int) -> List[int]:
        arr_in = (ctypes.c_int32 * n)(*arr)
        result = (ctypes.c_int32 * n)()
        self._lib.window_gradient(arr_in, n, window, result)
        return [result[i] for i in range(n)]


class _ZigLib:
    """Wrapper around ctypes-loaded Zig shared library (libft_zig.so)."""

    def __init__(self, lib: ctypes.CDLL) -> None:
        self._lib = lib
        self._setup_prototypes()

    def _setup_prototypes(self) -> None:
        L = self._lib
        # ft_contract(a_ptr, a_len, b_ptr, b_len, threshold) -> i32
        L.ft_contract.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32,
        ]
        L.ft_contract.restype = ctypes.c_int32

        # ft_dot(a_ptr, b_ptr, n) -> i64
        L.ft_dot.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.c_int32,
        ]
        L.ft_dot.restype = ctypes.c_int64

        # ft_physics(&lat, &flops, &simd)
        L.ft_physics.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int32),
        ]
        L.ft_physics.restype = None

        # ft_window_contract(...)
        L.ft_window_contract.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32, ctypes.c_int32,
        ]
        L.ft_window_contract.restype = ctypes.c_int32

        # ft_recency_dot(...) -> i64
        L.ft_recency_dot.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
            ctypes.c_int32,
        ]
        L.ft_recency_dot.restype = ctypes.c_int64

        # ft_window_gradient(arr, n, window, result)
        L.ft_window_gradient.argtypes = [
            ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
            ctypes.c_int32, ctypes.POINTER(ctypes.c_int32),
        ]
        L.ft_window_gradient.restype = None

    def contract(self, a: Sequence[int], na: int,
                  b: Sequence[int], nb: int,
                  threshold: int) -> int:
        arr_a = (ctypes.c_int32 * na)(*a)
        arr_b = (ctypes.c_int32 * nb)(*b)
        return self._lib.ft_contract(arr_a, na, arr_b, nb, threshold)

    def dot(self, a: Sequence[int], b: Sequence[int], n: int) -> int:
        arr_a = (ctypes.c_int32 * n)(*a)
        arr_b = (ctypes.c_int32 * n)(*b)
        return self._lib.ft_dot(arr_a, arr_b, n)

    def physics(self) -> Tuple[float, float, int]:
        lat = ctypes.c_float(0.0)
        flops = ctypes.c_float(0.0)
        simd = ctypes.c_int32(0)
        self._lib.ft_physics(ctypes.byref(lat), ctypes.byref(flops), ctypes.byref(simd))
        return (lat.value, flops.value, simd.value)

    def window_contract(
        self,
        time_a: Sequence[int], a: Sequence[int], na: int,
        time_b: Sequence[int], b: Sequence[int], nb: int,
        window: int, threshold: int,
    ) -> int:
        arr_ta = (ctypes.c_int32 * na)(*time_a)
        arr_a = (ctypes.c_int32 * na)(*a)
        arr_tb = (ctypes.c_int32 * nb)(*time_b)
        arr_b = (ctypes.c_int32 * nb)(*b)
        return self._lib.ft_window_contract(
            arr_ta, arr_a, na, arr_tb, arr_b, nb, window, threshold,
        )

    def recency_dot(
        self, a: Sequence[int], time_a: Sequence[int],
        b: Sequence[int], time_b: Sequence[int], n: int,
    ) -> int:
        arr_a = (ctypes.c_int32 * n)(*a)
        arr_ta = (ctypes.c_int32 * n)(*time_a)
        arr_b = (ctypes.c_int32 * n)(*b)
        arr_tb = (ctypes.c_int32 * n)(*time_b)
        return self._lib.ft_recency_dot(arr_a, arr_ta, arr_b, arr_tb, n)

    def window_gradient(self, arr: Sequence[int], n: int, window: int) -> List[int]:
        arr_in = (ctypes.c_int32 * n)(*arr)
        result = (ctypes.c_int32 * n)()
        self._lib.ft_window_gradient(arr_in, n, window, result)
        return [result[i] for i in range(n)]


class ComputeClaw:
    """Interface to native Fortran and Zig compute libraries.

    Loads libplato_math.so (Fortran) and libft_zig.so (Zig bridge) from
    standard paths. All operations are pure int32 array calls.
    """

    def __init__(self) -> None:
        self.fortran: _FortranLib
        self.zig: Optional[_ZigLib] = None
        self._load()

    def _find_lib(self, name: str) -> Optional[str]:
        for d in _CONF.bench_library_paths:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        return None

    def _load(self) -> None:
        f_path = self._find_lib("libplato_math.so")
        if not f_path:
            print(f"{red('Error')}: libplato_math.so not found in search paths: "
                  f"{', '.join(_CONF.bench_library_paths)}", file=sys.stderr)
            sys.exit(3)
        try:
            self.fortran = _FortranLib(ctypes.CDLL(f_path))
        except OSError as e:
            print(f"{red('Error')}: cannot load {f_path}: {e}", file=sys.stderr)
            sys.exit(3)

        z_path = self._find_lib("libft_zig.so")
        if z_path:
            try:
                self.zig = _ZigLib(ctypes.CDLL(z_path))
            except OSError:
                self.zig = None


# ─── Utility: hash extraction ─────────────────────────────────────────────

def _tile_hash(tile: Dict[str, Any]) -> int:
    """Extract a deterministic int32 from a tile for compute operations."""
    raw = tile.get("_hash", "0")[:8]
    try:
        return int(raw, 16) % 0x7FFFFFFF
    except ValueError:
        return 0


def _question_hash(tile: Dict[str, Any]) -> int:
    """Hash the question text to an int32 for compute ops."""
    q = (tile.get("question", "") or "").strip()
    return hash(q[:32]) & 0x7FFFFFFF


# ─── CLAW HTTP helpers ────────────────────────────────────────────────────

def _claw_post(endpoint: str, data: Dict[str, Any]) -> Any:
    """JSON POST to the compute claw HTTP server."""
    url = f"{_CONF.claw_url}{endpoint}"
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=_CONF.claw_timeout) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        print(f"{red('Error')}: cannot reach compute claw at {url}: {e.reason}",
              file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"{red('Error')}: invalid JSON from compute claw: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"{red('Error')}: compute claw request failed: {e}", file=sys.stderr)
        sys.exit(2)


# ─── CLI Commands ──────────────────────────────────────────────────────────

def cmd_plato(_args: List[str]) -> None:
    """Server status: rooms, tiles, gate statistics."""
    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    status = client.fetch_status()

    rooms = status.get("rooms", {})
    gate = status.get("gate_stats", {})
    total_tiles = sum(r.get("tile_count", 0) for r in rooms.values())

    print(f"{bold('PLATO Server Status')}")
    print(f"  Version:  {status.get('version', 'unknown')}")
    print(f"  Uptime:   {_format_uptime(status.get('uptime', 0))}")
    print(f"  Rooms:    {len(rooms)}")
    print(f"  Tiles:    {total_tiles}")

    if gate:
        acc = gate.get("accepted", 0)
        rej = gate.get("rejected", 0)
        print()
        print(f"{bold('Gate Stats')}")
        print(f"  Accepted:  {green(str(acc))}")
        print(f"  Rejected:  {red(str(rej)) if rej > 0 else str(rej)}")
        reasons = gate.get("reasons", {})
        if reasons:
            print(f"  Top reasons:")
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:5]:
                print(f"    • {reason}: {count}")

    if rooms:
        print()
        print(f"{bold('Rooms')}")
        sorted_rooms = sorted(rooms.items(), key=lambda kv: -kv[1].get("tile_count", 0))
        header = f"  {'NAME':<30} {'TILES':>6}  {'CREATED':<20}"
        print(header)
        print(f"  {'-'*30} {'-'*6}  {'-'*20}")
        for name, info in sorted_rooms:
            tc = info.get("tile_count", 0)
            created = (info.get("created", "") or "")[:19]
            print(f"  {name:<30} {tc:>6}  {created:<20}")


def cmd_physics(_args: List[str]) -> None:
    """Compute claw physics: latency, FLOPs, SIMD width."""
    # Try HTTP claw first, fall back to native Fortran
    try:
        with urllib.request.urlopen(f"{_CONF.claw_url}/physics", timeout=5) as r:
            p = json.loads(r.read())
        lat = p.get("latency_ns", 0)
        flops = p.get("flops", 0)
        simd = p.get("simd_bits", 0)
        print(f"{bold('Compute Claw Physics (HTTP)')}")
    except Exception:
        claw = ComputeClaw()
        lat, flops, simd = claw.fortran.physics()
        print(f"{bold('Compute Claw Physics (Native)')}")

    print(f"  Latency:  {green(f'{lat:.1f} ns')}")
    print(f"  FLOPs:    {flops:.2e}")
    print(f"  SIMD:     {cyan(f'{simd}-bit')}")


def cmd_cat(args: List[str]) -> None:
    """Read and display tiles from a room with confidence colors."""
    if not args:
        print(f"Usage: ft cat <room>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles = client.fetch_room(room, limit=50)

    if not tiles:
        print(f"{yellow('Info')}: room '{room}' has no tiles or does not exist", file=sys.stderr)
        return

    tw = _terminal_width()
    src_w = 18
    conf_w = 5
    q_max = tw - conf_w - src_w - 14
    if q_max < 20:
        q_max = 60

    print(f"{bold(f'Room: {room}')}  ({len(tiles)} tiles)")
    print()
    for i, t in enumerate(tiles):
        conf = t.get("confidence", 0.0)
        source = (t.get("source", "") or "")[:src_w]
        q = (t.get("question", "") or "").strip()[:q_max]
        if len(q) >= q_max:
            q += "…"
        ccolor = confidence_color(conf)
        conf_str = f"{ccolor}{conf:.2f}{_RESET}"
        print(f"  [{i:3d}] {conf_str}  {dim(source):{src_w}s}  {q}")


def cmd_canon(args: List[str]) -> None:
    """Top N highest-confidence tiles from a room."""
    if not args:
        print(f"Usage: ft canon <room> [N]", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    n = 10
    if len(args) > 1:
        try:
            n = int(args[1])
        except ValueError:
            print(f"{red('Error')}: N must be a number, got '{args[1]}'", file=sys.stderr)
            sys.exit(1)

    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles = client.fetch_room(room, limit=200)
    if not tiles:
        print(f"{yellow('Info')}: room '{room}' has no tiles", file=sys.stderr)
        return

    sorted_tiles = sorted(tiles, key=lambda t: -(t.get("confidence", 0) or 0))
    top = sorted_tiles[:n]

    tw = _terminal_width()
    conf_w = 6
    src_w = 18
    q_max = tw - conf_w - src_w - 14
    if q_max < 20:
        q_max = 60

    print(f"{bold(f'Top {len(top)} of {len(tiles)} tiles in {room}')}")
    print()
    print(f"  {'#':>3}  {'CONF':>{conf_w}s}  {'SOURCE':{src_w}s}  QUESTION")
    print(f"  {'---':>3s}  {'------':>{conf_w}s}  {'------------------':{src_w}s}  "
          f"{'-------':>{q_max}s}")
    for i, t in enumerate(top):
        conf = t.get("confidence", 0.0)
        source = (t.get("source", "") or "")[:src_w]
        q = (t.get("question", "") or "").strip()[:q_max]
        ccolor = confidence_color(conf)
        conf_str = f"{ccolor}{conf:.3f}{_RESET}"
        print(f"  [{i+1:>2d}] {conf_str}  {dim(source):{src_w}s}  {q}")


def cmd_contract(args: List[str]) -> None:
    """Contract two room tile sets through Fortran compute claw.

    Computes how many value-pairs between two rooms differ by more than
    the given threshold. This is PLATO's primary similarity/dissimilarity
    operation.
    """
    if len(args) < 2:
        print(f"Usage: ft contract <room_a> <room_b> [threshold]", file=sys.stderr)
        sys.exit(1)

    a_name, b_name = args[0], args[1]
    threshold = 100
    if len(args) > 2:
        try:
            threshold = int(args[2])
        except ValueError:
            print(f"{red('Error')}: threshold must be an integer, got '{args[2]}'",
                  file=sys.stderr)
            sys.exit(1)

    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    print(f"  Fetching room '{a_name}'...", end=" ", flush=True)
    tiles_a = client.fetch_room(a_name, limit=200)
    print(f"{green(f'{len(tiles_a)} tiles')}")
    print(f"  Fetching room '{b_name}'...", end=" ", flush=True)
    tiles_b = client.fetch_room(b_name, limit=200)
    print(f"{green(f'{len(tiles_b)} tiles')}")

    if not tiles_a or not tiles_b:
        print(f"{red('Error')}: one or both rooms are empty", file=sys.stderr)
        sys.exit(2)

    vals_a = [_tile_hash(t) for t in tiles_a]
    vals_b = [_tile_hash(t) for t in tiles_b]
    na, nb = len(vals_a), len(vals_b)

    # Try HTTP claw first, fall back to native
    try:
        payload = {
            "room_a": vals_a, "room_b": vals_b,
            "na": na, "nb": nb, "threshold": threshold,
        }
        r = _claw_post("/contract", payload)
        nresult = r.get("nresult", 0)
        results = r.get("results", [])
    except (SystemExit, Exception):
        claw = ComputeClaw()
        nresult = claw.fortran.contract(vals_a, na, vals_b, nb, threshold)
        results = [nresult]

    pairs_total = na * nb
    pct = nresult / pairs_total * 100 if pairs_total > 0 else 0.0
    print(f"  Result:   {green(str(nresult))} of {pairs_total} pairs ({pct:.1f}%) "
          f"above threshold {threshold}")
    if len(results) > 1:
        print(f"  First 10: {', '.join(str(v) for v in results[:10])}")


def cmd_gradient(args: List[str]) -> None:
    """Absolute differences between consecutive tiles (gradient)."""
    if not args:
        print(f"Usage: ft gradient <room>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles = client.fetch_room(room, limit=100)
    if not tiles:
        print(f"{yellow('Info')}: room '{room}' has no tiles", file=sys.stderr)
        return

    vals = [_question_hash(t) for t in tiles]
    n = len(vals)

    try:
        payload = {"tiles": vals, "n": n}
        r = _claw_post("/gradient", payload)
        grads = r.get("gradients", [])
    except (SystemExit, Exception):
        claw = ComputeClaw()
        grads = claw.fortran.gradient(vals, n)

    print(f"{bold(f'Gradient across {n} tiles in {room}')}")
    print()
    for i, g in enumerate(grads[:10]):
        q = (tiles[i].get("question", "") or "").strip()[:50]
        if len(q) >= 50:
            q += "…"
        g_abs = abs(g)
        if g_abs > 1000000:
            g_str = red(f"{g:10d}")
        elif g_abs > 100000:
            g_str = yellow(f"{g:10d}")
        else:
            g_str = dim(f"{g:10d}")
        print(f"  [{i:3d}] Δ={g_str}  {q}")

    if n > 10:
        print(f"  … and {n - 10} more values")


def cmd_spline(args: List[str]) -> None:
    """Interpolate room state between before and after states (mu: 0-1023)."""
    if not args:
        print(f"Usage: ft spline <room> <mu>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    mu = 512
    if len(args) > 1:
        try:
            mu = int(args[1])
            if mu < 0 or mu > 1023:
                print(f"{yellow('Warning')}: mu should be 0-1023, got {mu}", file=sys.stderr)
        except ValueError:
            print(f"{red('Error')}: mu must be an integer, got '{args[1]}'", file=sys.stderr)
            sys.exit(1)

    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles = client.fetch_room(room, limit=50)
    if not tiles:
        return

    vals = [_question_hash(t) for t in tiles]
    n = len(vals)

    try:
        payload = {"before": vals, "after": [v * 2 for v in vals], "n": n, "mu": mu}
        r = _claw_post("/spline", payload)
        result = r.get("result", [])
    except (SystemExit, Exception):
        claw = ComputeClaw()
        result = claw.fortran.spline(vals, [v * 2 for v in vals], n, mu)

    print(f"{bold(f'Spline {room}')}")
    print(f"  mu={mu}/1023  |before|={n}  |result|={len(result)}")
    if result:
        print(f"  First 5: {', '.join(str(v) for v in result[:5])}")


def cmd_watch(args: List[str]) -> None:
    """Poll a PLATO room for new tiles, printing them as they appear."""
    if not args:
        print(f"Usage: ft watch <room> [interval]", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    interval = 10.0
    if len(args) > 1:
        try:
            interval = float(args[1])
            if interval < 0.5:
                print(f"{yellow('Warning')}: minimum interval is 0.5s, clamping", file=sys.stderr)
                interval = 0.5
        except ValueError:
            print(f"{red('Error')}: interval must be a number, got '{args[1]}'",
                  file=sys.stderr)
            sys.exit(1)

    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    print(f"{bold('Watching')} room '{green(room)}' every {interval}s...  "
          f"({dim('Ctrl+C to stop')})")
    print()

    seen: set = set()
    try:
        while True:
            tiles = client.fetch_room(room, limit=200)
            for t in tiles:
                tile_hash = t.get("_hash", "")
                if tile_hash and tile_hash not in seen:
                    seen.add(tile_hash)
                    conf = t.get("confidence", 0.0)
                    q = (t.get("question", "") or "").strip()
                    a = (t.get("answer", "") or "").strip()
                    source = t.get("source", "?")
                    now = time.strftime("%H:%M:%S")
                    ccolor = confidence_color(conf)
                    print(f"{dim(f'[{now}]')} {ccolor}{conf:.2f}{_RESET}  "
                          f"{dim(source):>12s}  {bold(q)}")
                    if a:
                        a_short = a[:100].replace("\n", " ")
                        if len(a) > 100:
                            a_short += "…"
                        print(f"           {dim(a_short)}")
                    print()
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        print(f"Stopped. Seen {len(seen)} unique tiles.")


def cmd_bench(_args: List[str]) -> None:
    """Run all benchmarks: Fortran direct + Zig ABI."""
    claw = ComputeClaw()
    fw = claw.fortran
    zw = claw.zig

    print(f"{bold('Benchmarks')}")
    print(f"{dim('Fortran library via ctypes')}")
    print()

    # ── Fortran contract ──
    print(f"  {cyan('Fortran Contract')}")
    for na, nb in [(1000, 1000), (5000, 5000)]:
        a = [i * 1000 for i in range(na)]
        b = [i * 1000 + 500 for i in range(nb)]
        t0 = time.perf_counter()
        nr = fw.contract(a, na, b, nb, 10000)
        dt = time.perf_counter() - t0
        rate = na * nb / dt / 1e6 if dt > 0 else 0
        print(f"    Contract {na:>4}×{nb:<4}: {dt*1000:>7.1f}ms  "
              f"{rate:>9.0f}M pairs/s   ({bold(str(nr))} results)")

    # ── Fortran gradient ──
    print()
    print(f"  {cyan('Fortran Gradient')}")
    for n in [10000, 100000]:
        a = [i * 100 for i in range(n)]
        t0 = time.perf_counter()
        g = fw.gradient(a, n)
        dt = time.perf_counter() - t0
        rate = n / dt / 1e6 if dt > 0 else 0
        print(f"    Gradient {n:>6}: {dt*1000:>7.3f}ms  {rate:>9.0f}M elem/s")

    # ── Fortran dot ──
    print()
    print(f"  {cyan('Fortran Dot')}")
    for n in [1000, 10000]:
        a = [i * 3 for i in range(n)]
        b = [i * 7 for i in range(n)]
        t0 = time.perf_counter()
        r = fw.dot(a, b, n)
        dt = time.perf_counter() - t0
        rate = n / dt / 1e6 if dt > 0 else 0
        print(f"    Dot {n:>6}: {dt*1000:>7.3f}ms  {rate:>9.0f}M elem/s  ({r})")

    # ── Fortran window contract ──
    print()
    print(f"  {cyan('Fortran Window Contract')}")
    for n in [500]:
        ta = list(range(n))
        a = [i * 1000 for i in range(n)]
        tb = list(range(n))
        b = [i * 1000 + 500 for i in range(n)]
        t0 = time.perf_counter()
        nr = fw.window_contract(ta, a, n, tb, b, n, 100, 10000)
        dt = time.perf_counter() - t0
        rate = n * n / dt / 1e6 if dt > 0 else 0
        print(f"    Window {n:>4}×{n:<4}: {dt*1000:>7.1f}ms  {rate:>9.0f}M pairs/s  "
              f"({bold(str(nr))} results)")

    # ── Zig contract ──
    if zw:
        print()
        print(f"  {cyan('Zig Contract')}")
        for n in [1000, 5000]:
            a = [i * 1000 for i in range(n)]
            b = [i * 1000 + 500 for i in range(n)]
            t0 = time.perf_counter()
            nr = zw.contract(a, n, b, n, 10000)
            dt = time.perf_counter() - t0
            rate = n * n / dt / 1e6 if dt > 0 else 0
            print(f"    Contract {n:>4}×{n:<4}: {dt*1000:>7.1f}ms  "
                  f"{rate:>9.0f}M pairs/s   ({bold(str(nr))} results)")

        # ── Zig dot ──
        print()
        print(f"  {cyan('Zig Dot')}")
        for n in [1000, 10000]:
            a = [i * 3 for i in range(n)]
            b = [i * 7 for i in range(n)]
            t0 = time.perf_counter()
            r = zw.dot(a, b, n)
            dt = time.perf_counter() - t0
            rate = n / dt / 1e6 if dt > 0 else 0
            print(f"    Dot {n:>6}: {dt*1000:>7.3f}ms  {rate:>9.0f}M elem/s  ({r})")
    else:
        print()
        print(f"  {yellow('Zig — skipping (libft_zig.so not found)')}")


def cmd_zig(_args: List[str]) -> None:
    """Run Zig-specific benchmarks (Zig ABI only)."""
    claw = ComputeClaw()
    if not claw.zig:
        print(f"{red('Error')}: libft_zig.so not found — Zig benchmarks unavailable",
              file=sys.stderr)
        sys.exit(3)

    zw = claw.zig
    print(f"{bold('Zig Benchmarks')}")
    print()

    # ── Zig contract ──
    print(f"  {cyan('Contract')}")
    for n in [1000, 5000, 10000]:
        a = [i * 1000 for i in range(n)]
        b = [i * 1000 + 500 for i in range(n)]
        t0 = time.perf_counter()
        nr = zw.contract(a, n, b, n, 10000)
        dt = time.perf_counter() - t0
        rate = n * n / dt / 1e6 if dt > 0 else 0
        print(f"    {n:>5}×{n:<5}: {dt*1000:>7.1f}ms  {rate:>9.0f}M pairs/s  "
              f"({bold(str(nr))} results)")

    # ── Zig dot ──
    print()
    print(f"  {cyan('Dot')}")
    for n in [1000, 10000, 100000]:
        a = [i * 3 for i in range(n)]
        b = [i * 7 for i in range(n)]
        t0 = time.perf_counter()
        r = zw.dot(a, b, n)
        dt = time.perf_counter() - t0
        rate = n / dt / 1e6 if dt > 0 else 0
        print(f"    {n:>6}: {dt*1000:>7.3f}ms  {rate:>9.0f}M elem/s  ({r})")

    # ── Zig physics ──
    print()
    print(f"  {cyan('Physics')}")
    lat, flops, simd = zw.physics()
    print(f"    Latency:  {green(f'{lat:.1f} ns')}")
    print(f"    FLOPs:    {flops:.2e}")
    print(f"    SIMD:     {cyan(f'{simd}-bit')}")

    # ── Zig window contract ──
    print()
    print(f"  {cyan('Window Contract')}")
    n = 500
    ta = list(range(n))
    a = [i * 1000 for i in range(n)]
    tb = list(range(n))
    b = [i * 1000 + 500 for i in range(n)]
    t0 = time.perf_counter()
    nr = zw.window_contract(ta, a, n, tb, b, n, 100, 10000)
    dt = time.perf_counter() - t0
    print(f"    {n}×{n} window=100: {dt*1000:.1f}ms  ({bold(str(nr))} results)")


def cmd_window_contract(args: List[str]) -> None:
    """Contract two arrays with a time-window constraint.

    Only considers element pairs whose timestamps are within 'window'
    of each other. Makes time a first-class dimension.
    """
    if len(args) < 3:
        print(f"Usage: ft window-contract <room_a> <room_b> <window> [threshold]",
              file=sys.stderr)
        sys.exit(1)

    a_name, b_name = args[0], args[1]
    try:
        window = int(args[2])
    except ValueError:
        print(f"{red('Error')}: window must be an integer, got '{args[2]}'", file=sys.stderr)
        sys.exit(1)

    threshold = 100
    if len(args) > 3:
        try:
            threshold = int(args[3])
        except ValueError:
            print(f"{red('Error')}: threshold must be an integer, got '{args[3]}'",
                  file=sys.stderr)
            sys.exit(1)

    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles_a = client.fetch_room(a_name, limit=50)
    tiles_b = client.fetch_room(b_name, limit=50)

    if not tiles_a or not tiles_b:
        print(f"{red('Error')}: one or both rooms are empty", file=sys.stderr)
        sys.exit(2)

    na, nb = len(tiles_a), len(tiles_b)
    time_a = list(range(na))
    vals_a = [_tile_hash(t) for t in tiles_a]
    time_b = list(range(nb))
    vals_b = [_tile_hash(t) for t in tiles_b]

    claw = ComputeClaw()
    nresult = claw.fortran.window_contract(
        time_a, vals_a, na, time_b, vals_b, nb, window, threshold,
    )

    print(f"{bold('Window Contract Results')}")
    print(f"  Rooms:        {a_name} ({na}) × {b_name} ({nb})")
    print(f"  Window:       {window}")
    print(f"  Threshold:    {threshold}")
    print(f"  Pairs above:  {green(str(nresult))}")


def cmd_recency_dot(args: List[str]) -> None:
    """Recency-weighted dot product.

    Each element's contribution to the dot product is weighted by
    its recency: newer entries contribute more.
    """
    if not args:
        print(f"Usage: ft recency-dot <room>", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles = client.fetch_room(room, limit=50)

    if not tiles:
        print(f"{yellow('Info')}: room '{room}' has no tiles", file=sys.stderr)
        return

    n = len(tiles)
    time_a = list(range(n))
    vals_a = [_tile_hash(t) for t in tiles]
    time_b = list(range(n))
    vals_b = [v * 2 for v in vals_a]

    claw = ComputeClaw()
    result = claw.fortran.recency_dot(vals_a, time_a, vals_b, time_b, n)

    print(f"{bold('Recency-Weighted Dot Product')}")
    print(f"  Room:        {room} ({n} tiles)")
    print(f"  Result:      {green(str(result))}")


def cmd_window_gradient(args: List[str]) -> None:
    """Smoothed gradient over a sliding window.

    Each position's value is the average gradient across a window
    centered at that position. Smooths noise to reveal trends.
    """
    if not args:
        print(f"Usage: ft window-gradient <room> [window]", file=sys.stderr)
        sys.exit(1)

    room = args[0]
    win = 3
    if len(args) > 1:
        try:
            win = int(args[1])
            if win < 3:
                win = 3
        except ValueError:
            print(f"{red('Error')}: window must be an integer, got '{args[1]}'",
                  file=sys.stderr)
            sys.exit(1)

    client = PlatoClient(_CONF.plato_url, _CONF.http_timeout)
    tiles = client.fetch_room(room, limit=50)
    if not tiles:
        return

    vals = [_question_hash(t) for t in tiles]
    n = len(vals)

    claw = ComputeClaw()
    result = claw.fortran.window_gradient(vals, n, win)

    print(f"{bold(f'Window Gradient {room}')}")
    print(f"  Tiles:  {n}")
    print(f"  Window: {win}")
    print(f"  First values: "
          f"{', '.join(str(v) for v in result[:min(10, len(result))])}")


def cmd_help(_args: List[str]) -> None:
    """Comprehensive help text."""
    print(__doc__.strip())


# ─── Command Registry ─────────────────────────────────────────────────────


def cmd_recall(args):
    """Recall and reconstruct tiles from a room (lossy reconstruction)."""
    if not args:
        return print("Usage: ft recall <room> [count]")
    room = args[0]
    count = int(args[1]) if len(args) > 1 else 5
    try:
        import urllib.request, json, random
        resp = json.loads(urllib.request.urlopen(
            _CONF.plato_url + "/room/{0}?limit={1}".format(room, count), timeout=10).read())
        tiles = resp.get("tiles", [])
        if not tiles: return print("No tiles in {}/".format(room))
        tiles = tiles[:count]
        written = 0
        for i, t in enumerate(tiles):
            import time
            age = random.uniform(0, 3)
            weight = 1.0 / (1.0 + age)
            conf = t.get("confidence", 0.5)
            recon_conf = min(1.0, conf * (0.7 + 0.3 * weight))
            data = json.dumps({
                "room": room,
                "question": "recall: {}".format(t.get("question", "")[:60]),
                "answer": "[Recall weight={:.3f}] {}".format(weight, t.get("answer", "")[:200]),
                "source": "recall",
                "confidence": recon_conf,
            }).encode()
            req = urllib.request.Request(
                _CONF.plato_url + "/room/{}/submit".format(room),
                data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                if json.loads(r.read()).get("status") == "accepted":
                    written += 1
                    print("  [{:3d}] reconstructed conf={:.3f} weight={:.3f}".format(i, recon_conf, weight))
        print("\nRecall: {}/{} tiles reconstructed to {}/".format(written, len(tiles), room))
    except Exception as e:
        print("Error: {}".format(e))


_COMMANDS: Dict[str, Dict[str, Any]] = {
    "plato": {"fn": cmd_plato, "doc": "Server status"},
    "physics": {"fn": cmd_physics, "doc": "Compute claw physics"},
    "cat": {"fn": cmd_cat, "doc": "Read room tiles"},
    "canon": {"fn": cmd_canon, "doc": "Top N tiles by confidence"},
    "contract": {"fn": cmd_contract, "doc": "Contract two rooms"},
    "gradient": {"fn": cmd_gradient, "doc": "Gradient across tiles"},
    "spline": {"fn": cmd_spline, "doc": "Interpolate room state"},
    "watch": {"fn": cmd_watch, "doc": "Watch for new tiles"},
    "bench": {"fn": cmd_bench, "doc": "Run all benchmarks"},
    "benchmarks": {"fn": cmd_bench, "doc": "Alias for bench"},
    "zig": {"fn": cmd_zig, "doc": "Zig-specific benchmarks"},
    "window-contract": {"fn": cmd_window_contract, "doc": "Temporal contract"},
    "recency-dot": {"fn": cmd_recency_dot, "doc": "Recency-weighted dot product"},
    "window-gradient": {"fn": cmd_window_gradient, "doc": "Smoothed gradient"},
    "recall": {"fn": cmd_recall, "doc": "Recall and reconstruct tiles (lossy)"},
    "recall-agent": {"fn": cmd_recall_agent, "doc": "Continuous recall agent loop"},
    "-h": {"fn": cmd_help, "doc": "Help"},
    "--help": {"fn": cmd_help, "doc": "Help"},
    "help": {"fn": cmd_help, "doc": "Comprehensive help"},
}


def _usage() -> None:
    """Print short usage and exit."""
    print(f"Usage: ft <command> [args]")
    print()
    print(f"Commands:")
    for name, info in _COMMANDS.items():
        if name.startswith("-") or name in ("benchmarks",):
            continue
        print(f"  {name:<16s}  {info['doc']}")
    print()
    print(f"See 'ft help' for full documentation.")
    sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        _usage()

    raw_cmd = sys.argv[1].replace("_", "-")
    entry = _COMMANDS.get(raw_cmd)
    if entry is None:
        print(f"{red('Error')}: unknown command '{raw_cmd}'", file=sys.stderr)
        cmds = ", ".join(k for k in sorted(_COMMANDS)
                          if not k.startswith("-") and k != "benchmarks")
        print(f"Available: {cmds}", file=sys.stderr)
        sys.exit(1)

    try:
        entry["fn"](sys.argv[2:])
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()

def cmd_recall_agent(args):
    """Start a recall agent loop for a room.
    Every cycle: read tiles, reconstruct them, write reconstructions back.
    The room accumulates interpretations over time.
    
    Usage: ft recall-agent <room> [interval_sec]"""
    if not args:
        return print("Usage: ft recall-agent <room> [interval_sec]")
    room = args[0]
    interval = int(args[1]) if len(args) > 1 else 30
    import time
    cycle = 0
    print("Recall agent watching {}/ every {}s...".format(room, interval))
    print("Every cycle reads N tiles, reconstructs them, writes back.")
    print("The room accumulates interpretations, not just originals.")
    while True:
        cycle += 1
        print("\n[Cycle {}] Recalling {}/...".format(cycle, room))
        try:
            import urllib.request, json, random
            resp = json.loads(urllib.request.urlopen(
                _CONF.plato_url + "/room/{0}?limit=5".format(room), timeout=10).read())
            tiles = resp.get("tiles", [])[:5]
            written = 0
            for i, t in enumerate(tiles):
                age = random.uniform(0, 2)
                weight = 1.0 / (1.0 + age)
                conf = t.get("confidence", 0.5)
                recon_conf = min(1.0, conf * (0.8 + 0.2 * weight))
                data = json.dumps({
                    "room": room,
                    "question": "recall cycle {}: {}".format(cycle, t.get("question", "")[:50]),
                    "answer": "[Cycle {} weight={:.3f}] {}".format(cycle, weight, t.get("answer", "")[:150]),
                    "source": "recall-agent",
                    "confidence": recon_conf,
                }).encode()
                req = urllib.request.Request(
                    _CONF.plato_url + "/room/{}/submit".format(room),
                    data=data, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=10) as r:
                    if json.loads(r.read()).get("status") == "accepted":
                        written += 1
            print("  Reconstructed {}/{} tiles".format(written, len(tiles)))
        except Exception as e:
            print("  Error: {}".format(e))
        time.sleep(interval)
