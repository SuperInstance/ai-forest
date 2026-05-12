"""plato-sdk — Python client for PLATO room-based knowledge systems.

A room is a shared knowledge space. A tile is a structured contribution
(question + answer + confidence + source). Tiles persist forever.

The ft CLI and all PLATO operations are built on this SDK.

Quick start:
    from plato_sdk import PlatoClient
    pc = PlatoClient("http://localhost:8847")
    pc.write("my-room", "What is PLATO?", "A room-based knowledge system.")
    tiles = pc.read("my-room")
"""

import json, os, time, urllib.request
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Config:
    """Global configuration loaded from environment."""
    plato_url: str = field(default_factory=lambda: os.environ.get("PLATO_URL", "http://localhost:8847"))
    http_timeout: int = 10


_CONF = Config()


# ═══════════════════════════════════════════════════════════════
# CORE CLIENT
# ═══════════════════════════════════════════════════════════════

class PlatoError(Exception):
    """Base exception for PLATO operations."""
    pass


class PlatoClient:
    """Client for PLATO room-based knowledge servers.

    Rooms are shared knowledge spaces. Tiles are structured contributions.
    Every tile persists forever (object-permanence).
    """

    def __init__(self, url: Optional[str] = None, timeout: int = 10):
        self.url = (url or _CONF.plato_url).rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Any = None) -> Dict[str, Any]:
        """Make an HTTP request to the PLATO server."""
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            f"{self.url}{path}", data=data,
            headers={"Content-Type": "application/json"} if body else {},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()[:200]
            raise PlatoError(f"PLATO HTTP {e.code}: {body_text}")
        except urllib.error.URLError as e:
            raise PlatoError(f"PLATO unreachable: {e.reason}")
        except Exception as e:
            raise PlatoError(str(e))

    # ── Room Operations ──────────────────────────────────────────────

    def write(self, room: str, question: str, answer: str,
              source: str = "plato-sdk", confidence: float = 0.8,
              tags: Optional[List[str]] = None) -> bool:
        """Submit a tile to a PLATO room.

        Args:
            room: Room name (e.g., "my-room")
            question: The prompt or query (max 200 chars)
            answer: The content or response (max 2000 chars)
            source: Source identifier (default: "plato-sdk")
            confidence: Confidence score 0.0-1.0 (default: 0.8)
            tags: Optional classification tags

        Returns:
            True if the tile was accepted, False otherwise.
        """
        data = {
            "room": room, "question": question[:200],
            "answer": answer[:2000], "source": source, "confidence": confidence,
        }
        if tags:
            data["tags"] = tags[:10]

        result = self._request("POST", f"/room/{room}/submit", data)
        return result.get("status") == "accepted"

    def read(self, room: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Read recent tiles from a PLATO room.

        Args:
            room: Room name
            limit: Maximum number of tiles to fetch (default: 50)

        Returns:
            List of tile dictionaries with keys: question, answer,
            source, confidence, timestamp, etc.
        """
        result = self._request("GET", f"/room/{room}?limit={limit}")
        return result.get("tiles", [])

    def status(self) -> Dict[str, Any]:
        """Get PLATO server status.

        Returns:
            Dict with rooms, gate_stats, version, uptime.
        """
        return self._request("GET", "/status")

    # ── Convenience ──────────────────────────────────────────────────

    def rooms(self) -> Dict[str, Dict[str, Any]]:
        """Get all rooms and their tile counts."""
        s = self.status()
        return s.get("rooms", {})

    def tile_count(self, room: str) -> int:
        """Get the number of tiles in a room."""
        r = self.read(room, limit=1)
        return len(r)

    def write_now(self, room: str, question: str, answer: str,
                  **kwargs) -> bool:
        """Write a tile with an automatic timestamp in the question."""
        ts = datetime.now().strftime("%H:%M:%S")
        return self.write(room, f"[{ts}] {question}", answer, **kwargs)


# ═══════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    """Command-line entry point for the ft CLI.
    Delegates to the ft module if available."""
    import sys
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    try:
        import ft
        ft.main()
    except ImportError:
        print("ft CLI not installed. Run: pip3 install plato-ft")
        sys.exit(1)
