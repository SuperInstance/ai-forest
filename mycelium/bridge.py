#!/usr/bin/env python3
"""
bridge.py — AI Forest Mycelium Bridge

The universal connector for the AI Forest. Every layer (Go, Rust, TS, C, Python)
sends tiles to this bridge, which normalizes them to 24-bit and routes them:

  1. To the correct PLATO room for persistence and sharing
  2. To any listening agents in other layers (through PLATO's event stream)

Architecture:
  Go Agent ────┐
  Rust Agent ──┤
  TS Agent  ───┼──► Mycelium Bridge (:4080) ──► PLATO (:8847)
  C Agent   ───┤           │
  Python   ────┘           ├──► Log every tile to stdout
                           ├──► Track active agents per layer
                           └──► Route tiles to correct rooms

Usage:
  python3 bridge.py --port 4080
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from tile_codec import (
    encode_24bit, decode_24bit, tile_to_plato_json,
    plato_json_to_tile, format_tile, cast_24bit,
    SCHEME_NAMES,
)
from forest_state import ForestState

# ── Configuration ──────────────────────────────────────────────────────

DEFAULT_PORT = 4080
PLATO_BASE = os.environ.get("PLATO_URL", "http://localhost:8847")

# ── Globals ────────────────────────────────────────────────────────────

forest = ForestState()

# ── PLATO Communication ────────────────────────────────────────────────

def plato_post(room: str, data: dict) -> bool:
    """Send a message to a PLATO room via POST /room/{room}.
    Returns True on success.
    """
    url = f"{PLATO_BASE}/room/{room}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logging.warning("PLATO POST %s failed: %s", url, e)
        return False


def plato_get_room(room: str) -> list:
    """Read messages from a PLATO room via GET /room/{room}.
    Returns a list of message dicts.
    """
    url = f"{PLATO_BASE}/room/{room}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logging.warning("PLATO GET %s failed: %s", url, e)
        return []


def plato_forward_tile(value_24bit: int, source: str, room: str = "ai-forest") -> bool:
    """Normalize a tile to PLATO JSON and post it to a PLATO room."""
    payload = tile_to_plato_json(value_24bit, source)
    return plato_post(room, payload)


# ── Tile Routing Logic ─────────────────────────────────────────────────

def route_tile(value_24bit: int, from_layer: str, to_layer: str,
               agent_id: str = "unknown", room: str = "ai-forest") -> dict:
    """Route a tile from one layer to another through PLATO.

    Args:
        value_24bit: The 24-bit tile value
        from_layer:  Source layer name (e.g. "go", "rust")
        to_layer:    Target layer name (e.g. "ts", "python")
        agent_id:    Source agent identifier
        room:        PLATO room to use

    Returns:
        dict with routing result info
    """
    # Register the source agent
    forest.register_agent(from_layer, agent_id)
    forest.increment_tile_count(from_layer, agent_id)

    # Build the routed tile
    tile_json = tile_to_plato_json(value_24bit, f"{from_layer}/{agent_id}")
    tile_json["routing"] = {
        "from": from_layer,
        "to": to_layer,
        "room": room,
    }

    # Choose destination room — create a layer-specific room
    dest_room = f"ai-forest/{from_layer}-to-{to_layer}"

    # Post to the general forest room and the specific route room
    ok_general = plato_forward_tile(value_24bit, f"{from_layer}/{agent_id}", room)
    ok_route = plato_forward_tile(value_24bit, f"{from_layer}/{agent_id}", dest_room)

    return {
        "ok": ok_general or ok_route,
        "tile": tile_json,
        "routed_to": [room, dest_room],
        "from_agent": f"{from_layer}/{agent_id}",
        "to_layers": [to_layer],
    }


def process_incoming_tile(body: dict, source_hint: str = "unknown") -> dict:
    """Process an incoming tile from any layer format.

    Accepts:
      - Direct 24-bit integer: {"value": 123456}
      - Scheme+fields:        {"scheme": 1, "fields": [10, 20, 30]}
      - PLATO JSON:           {"type": "tile", "value": ..., "source": ...}
      - String representation: {"value": "0x1E240"}

    Returns:
        {"value": <24bit>, "source": <str>, "layer": <str>, ...}
    """
    source = body.get("source", source_hint)
    layer = body.get("layer", os.environ.get("DEFAULT_LAYER", "unknown"))
    agent_id = body.get("agent_id", body.get("agent", source_hint))

    # Extract the 24-bit value
    if "value" in body:
        raw = body["value"]
        if isinstance(raw, str):
            if raw.startswith("0x") or raw.startswith("0X"):
                value_24bit = int(raw, 16) & 0xFFFFFF
            else:
                value_24bit = int(raw) & 0xFFFFFF
        else:
            value_24bit = cast_24bit(int(raw))
    elif "scheme" in body and "fields" in body:
        scheme = int(body["scheme"])
        fields = list(map(int, body["fields"]))
        value_24bit = encode_24bit(scheme, fields)
    else:
        raise ValueError(
            "Tile must contain 'value' (int/hex string) or ('scheme' + 'fields')"
        )

    # Register the agent
    forest.register_agent(layer, agent_id, body.get("info"))
    forest.increment_tile_count(layer, agent_id)

    return {
        "value": value_24bit,
        "source": source,
        "layer": layer,
        "agent_id": agent_id,
        "decoded": {
            "scheme": decode_24bit(value_24bit)[0],
            "fields": decode_24bit(value_24bit)[1],
            "readable": format_tile(value_24bit),
        },
    }


# ── HTTP Server ────────────────────────────────────────────────────────

class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the mycelium bridge."""

    def log_message(self, format, *args):
        """Log via Python logger instead of stderr."""
        logging.info("HTTP %s %s", self.command, self.path)

    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_text(self, text: str, status: int = 200):
        """Send a plain text response."""
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def _read_body(self) -> dict:
        """Read and parse the request body as JSON."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    # ── GET / ──────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "" or path == "/":
            self._handle_status()
        elif path == "/layers":
            self._handle_layers()
        elif path.startswith("/read/"):
            room = path[len("/read/"):]
            self._handle_read_room(room)
        elif path == "/forest":
            self._handle_forest()
        elif path == "/health":
            self._send_json({"status": "ok", "timestamp": time.time()})
        elif path.startswith("/layer/"):
            # Single layer lookup: /layer/{name}
            layer_name = path[len("/layer/"):]
            agents = forest.get_agents_in_layer(layer_name)
            if agents:
                self._send_json({"layer": layer_name, "agents": agents})
            else:
                self._send_json(
                    {"error": f"Layer '{layer_name}' not found"}, 404
                )
        else:
            self._send_json({"error": f"Unknown path: {path}"}, 404)

    # ── POST /tile ─────────────────────────────────────────────────────

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "/tile":
            self._handle_post_tile()
        elif path.startswith("/route/"):
            # /route/{from}/{to}
            parts = path[len("/route/"):].split("/")
            if len(parts) >= 2:
                from_layer, to_layer = parts[0], parts[1]
                self._handle_route_tile(from_layer, to_layer)
            else:
                self._send_json(
                    {"error": "Usage: /route/{from_layer}/{to_layer}"}, 400
                )
        elif path == "/register":
            self._handle_register()
        elif path == "/heartbeat":
            self._handle_heartbeat()
        else:
            self._send_json({"error": f"Unknown path: {path}"}, 404)

    # ── CORS Preflight ─────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── Handler Implementations ────────────────────────────────────────

    def _handle_status(self):
        """GET / — Status page with connected layers."""
        summary = forest.get_summary()
        status_data = {
            "service": "AI Forest Mycelium Bridge",
            "version": "1.0.0",
            "status": "running",
            "uptime_seconds": int(time.time() - _start_time),
            "plato": {
                "url": PLATO_BASE,
                "connected": True,  # optimistic; will fail on use
            },
            "forest": summary,
            "endpoints": {
                "GET /": "This status page",
                "GET /layers": "List all connected layers and agents",
                "GET /layer/{name}": "Get details for a specific layer",
                "GET /read/{room}": "Read tiles from a PLATO room",
                "GET /forest": "Read forest map structure",
                "GET /health": "Health check",
                "POST /tile": "Accept a tile from any layer",
                "POST /route/{from}/{to}": "Route a tile between layers",
                "POST /register": "Register an agent",
                "POST /heartbeat": "Agent heartbeat",
            },
            "schemes": {str(k): v for k, v in SCHEME_NAMES.items()},
        }
        self._send_json(status_data)

    def _handle_layers(self):
        """GET /layers — List all connected layers and their agents."""
        layers = forest.get_layers()
        data = {
            "layers": layers,
            "total_layers": forest.get_layer_count(),
            "total_agents": forest.get_agent_count(),
            "total_tiles_routed": forest.get_tile_count(),
        }
        self._send_json(data)

    def _handle_forest(self):
        """GET /forest — Return the forest map structure.

        This provides a view of all layers and their recent activity.
        """
        layers = forest.get_layers()
        data = {
            "forest_map": {
                "name": "AI Forest",
                "description": "Multi-language agent ecosystem connected via mycelium bridge",
                "bridge_port": _port,
                "layers": layers,
                "summary": forest.get_summary(),
            }
        }
        self._send_json(data)

    def _handle_read_room(self, room: str):
        """GET /read/{room} — Read tiles from a PLATO room."""
        if not room:
            self._send_json({"error": "Room name required"}, 400)
            return
        messages = plato_get_room(room)
        self._send_json({
            "room": room,
            "messages": messages,
            "count": len(messages),
        })

    def _handle_post_tile(self):
        """POST /tile — Accept a tile from any layer, normalize, route to PLATO."""
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        try:
            source = body.get("source",
                             f"unknown/{self.client_address[0]}")
            result = process_incoming_tile(body, source)

            # Route to PLATO
            room = body.get("room", "ai-forest")
            ok = plato_forward_tile(result["value"], result["source"], room)

            result["plato_routed"] = ok
            result["plato_room"] = room

            logging.info(
                "TILE %s %s -> PLATO/%s (ok=%s) | %s",
                result["layer"], result["source"], room, ok,
                format_tile(result["value"]),
            )

            status = 200 if ok else 202  # 202 if PLATO unreachable
            self._send_json(result, status)
        except ValueError as e:
            self._send_json({"error": str(e)}, 400)
        except Exception as e:
            logging.exception("Error processing tile")
            self._send_json({"error": f"Internal error: {e}"}, 500)

    def _handle_route_tile(self, from_layer: str, to_layer: str):
        """POST /route/{from}/{to} — Route a tile between layers."""
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        try:
            source = body.get("source", "unknown")
            agent_id = body.get("agent_id", source)
            room = body.get("room", "ai-forest")

            # Process the incoming tile
            result = process_incoming_tile(body, source)

            # Route it
            route_result = route_tile(
                result["value"], from_layer, to_layer,
                agent_id=agent_id, room=room,
            )

            response = {
                **result,
                "routing": route_result,
                "from_layer": from_layer,
                "to_layer": to_layer,
            }

            logging.info(
                "ROUTE %s -> %s | tile=%s | ok=%s",
                from_layer, to_layer,
                format_tile(result["value"]),
                route_result["ok"],
            )

            status = 200 if route_result["ok"] else 202
            self._send_json(response, status)
        except ValueError as e:
            self._send_json({"error": str(e)}, 400)
        except Exception as e:
            logging.exception("Error routing tile")
            self._send_json({"error": f"Internal error: {e}"}, 500)

    def _handle_register(self):
        """POST /register — Register an agent in a layer."""
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        layer = body.get("layer", "unknown")
        agent_id = body.get("agent_id", body.get("agent", "unknown"))
        info = body.get("info", {})

        forest.register_agent(layer, agent_id, info)

        logging.info("REGISTER %s/%s", layer, agent_id)

        self._send_json({
            "ok": True,
            "layer": layer,
            "agent_id": agent_id,
            "agent_count": forest.get_agent_count(),
        })

    def _handle_heartbeat(self):
        """POST /heartbeat — Agent heartbeat to keep registration alive."""
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        layer = body.get("layer", "unknown")
        agent_id = body.get("agent_id", body.get("agent", "unknown"))

        forest.heartbeat(layer, agent_id)

        self._send_json({
            "ok": True,
            "layer": layer,
            "agent_id": agent_id,
            "timestamp": time.time(),
        })


# ── Server Setup ───────────────────────────────────────────────────────

_port = DEFAULT_PORT
_start_time = time.time()


def run_server(host: str = "0.0.0.0", port: int = DEFAULT_PORT):
    """Start the mycelium bridge HTTP server."""
    global _port, _start_time
    _port = port
    _start_time = time.time()

    server = HTTPServer((host, port), BridgeHandler)
    print(f"🌿 AI Forest Mycelium Bridge running on http://{host}:{port}")
    print(f"   PLATO endpoint: {PLATO_BASE}")
    print(f"   Press Ctrl+C to stop")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


# ── CLI Entry Point ────────────────────────────────────────────────────

def main():
    global PLATO_BASE

    parser = argparse.ArgumentParser(
        description="AI Forest Mycelium Bridge — universal tile connector"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--plato", type=str, default=PLATO_BASE,
        help=f"PLATO base URL (default: {PLATO_BASE})"
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    args = parser.parse_args()

    PLATO_BASE = args.plato

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
