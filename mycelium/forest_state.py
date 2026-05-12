"""
forest_state.py — Track Connected Layers and Agents

Maintains an in-memory registry of which agents are connected,
which layer they belong to, and when they last checked in.

A "layer" represents a language runtime (Go, Rust, TS, C, Python).
Each layer can have multiple agent connections.
"""

import time
import json
import threading
from typing import Dict, List, Optional, Any


class ForestState:
    """Thread-safe registry of connected forest layers and agents."""

    def __init__(self):
        self._lock = threading.Lock()
        # layers: { layer_name: { agent_id: { "last_seen": ts, "info": {...} } } }
        self._layers: Dict[str, Dict[str, dict]] = {}
        # tile counters: { layer_name: { agent_id: count } }
        self._counters: Dict[str, Dict[str, int]] = {}

    # ── Agent Lifecycle ────────────────────────────────────────────

    def register_agent(self, layer: str, agent_id: str, info: Optional[dict] = None):
        """Register or update a connected agent."""
        with self._lock:
            self._layers.setdefault(layer, {})
            self._layers[layer][agent_id] = {
                "last_seen": time.time(),
                "info": info or {},
            }
            self._counters.setdefault(layer, {})
            self._counters[layer].setdefault(agent_id, 0)

    def unregister_agent(self, layer: str, agent_id: str):
        """Remove a disconnected agent."""
        with self._lock:
            self._layers.get(layer, {}).pop(agent_id, None)
            self._counters.get(layer, {}).pop(agent_id, None)
            # Clean up empty layers
            if layer in self._layers and not self._layers[layer]:
                del self._layers[layer]
            if layer in self._counters and not self._counters[layer]:
                del self._counters[layer]

    def heartbeat(self, layer: str, agent_id: str):
        """Update an agent's last_seen timestamp."""
        with self._lock:
            agents = self._layers.get(layer, {})
            if agent_id in agents:
                agents[agent_id]["last_seen"] = time.time()

    # ── Tile Tracking ──────────────────────────────────────────────

    def increment_tile_count(self, layer: str, agent_id: str, n: int = 1):
        """Increment the tile counter for an agent."""
        with self._lock:
            self._counters.setdefault(layer, {})
            self._counters[layer][agent_id] = \
                self._counters[layer].get(agent_id, 0) + n

    def get_agent_tile_count(self, layer: str, agent_id: str) -> int:
        """Get the tile count for a specific agent."""
        with self._lock:
            return self._counters.get(layer, {}).get(agent_id, 0)

    # ── Queries ────────────────────────────────────────────────────

    def get_layers(self) -> Dict[str, Dict[str, dict]]:
        """Return a snapshot of all layers and their agents.

        Returns:
            { layer_name: { agent_id: { "last_seen": ts, "info": {...}, "tile_count": n } } }
        """
        with self._lock:
            result = {}
            for layer, agents in self._layers.items():
                result[layer] = {}
                for agent_id, data in agents.items():
                    result[layer][agent_id] = {
                        **data,
                        "tile_count": self._counters.get(layer, {}).get(agent_id, 0),
                    }
            return result

    def get_layer_names(self) -> List[str]:
        """Return a sorted list of connected layer names."""
        with self._lock:
            return sorted(self._layers.keys())

    def get_agents_in_layer(self, layer: str) -> Dict[str, dict]:
        """Return all agents in a specific layer."""
        with self._lock:
            agents = self._layers.get(layer, {})
            result = {}
            for agent_id, data in agents.items():
                result[agent_id] = {
                    **data,
                    "tile_count": self._counters.get(layer, {}).get(agent_id, 0),
                }
            return result

    def get_layer_count(self) -> int:
        """Return the number of connected layers."""
        with self._lock:
            return len(self._layers)

    def get_agent_count(self) -> int:
        """Return the total number of connected agents."""
        with self._lock:
            return sum(len(agents) for agents in self._layers.values())

    def get_tile_count(self) -> int:
        """Return the total number of tiles routed through this bridge."""
        with self._lock:
            total = 0
            for layer, agents in self._counters.items():
                total += sum(agents.values())
            return total

    def get_summary(self) -> dict:
        """Return a compact summary dict."""
        with self._lock:
            return {
                "layers": len(self._layers),
                "agents": sum(len(a) for a in self._layers.values()),
                "tiles_routed": sum(
                    sum(c.values()) for c in self._counters.values()
                ),
                "layer_details": {
                    layer: {
                        "agents": len(agents),
                        "tile_count": sum(self._counters.get(layer, {}).values()),
                    }
                    for layer, agents in self._layers.items()
                },
            }

    # ── Serialization ──────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize the full forest state (for API responses)."""
        return self.get_layers()
