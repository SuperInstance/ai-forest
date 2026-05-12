"""
tile_codec.py — 24-bit Tile Encode/Decode Helpers

The AI Forest uses 24-bit tiles as a universal data primitive. Every layer
(Go, Rust, TS, C, Python) emits and consumes tiles. This module provides the
canonical encode/decode logic so the bridge normalizes everything.

Tile format:
  24-bit value, MSB-first:
    Bits 23-20: scheme (4 bits, 0-15)
    Bits 19-0:  fields (20 bits, split per scheme)

Schemes:
  0: RESERVED  (null tile)
  1: SENSOR    (x:5, y:5, temp:10 — 5+5+10=20)
  2: ACTUATOR  (id:8, value:12)
  3: STATE     (key:10, val:10)
  4: SIGNAL    (type:4, channel:8, magnitude:8)
  5: META      (tag:8, seq:12)
  6: COMMAND   (op:6, target:6, payload:8)
  7: ERROR     (code:8, detail:12)
  8-15: CUSTOM (available for layer-specific use)
"""

from typing import Tuple, Dict, Any, Optional

# ── Constants ──────────────────────────────────────────────────────────

SCHEME_BITS = 4
FIELD_BITS = 20
TOTAL_BITS = 24
MAX_VALUE = (1 << TOTAL_BITS) - 1  # 0xFFFFFF

MAX_SCHEME = (1 << SCHEME_BITS) - 1  # 15

SCHEME_NAMES = {
    0: "RESERVED",
    1: "SENSOR",
    2: "ACTUATOR",
    3: "STATE",
    4: "SIGNAL",
    5: "META",
    6: "COMMAND",
    7: "ERROR",
}

# Scheme-specific field widths (in bits)
SCHEME_FIELD_WIDTHS = {
    0: [],  # RESERVED — no fields
    1: [5, 5, 10],   # SENSOR:  x, y, temp
    2: [8, 12],       # ACTUATOR: id, value
    3: [10, 10],      # STATE: key, val
    4: [4, 8, 8],     # SIGNAL: type, channel, magnitude
    5: [8, 12],       # META: tag, seq
    6: [6, 6, 8],     # COMMAND: op, target, payload
    7: [8, 12],       # ERROR: code, detail
}

# Scheme-specific field names
SCHEME_FIELD_NAMES = {
    0: [],
    1: ["x", "y", "temp"],
    2: ["id", "value"],
    3: ["key", "val"],
    4: ["type", "channel", "magnitude"],
    5: ["tag", "seq"],
    6: ["op", "target", "payload"],
    7: ["code", "detail"],
}


# ── Encoding ───────────────────────────────────────────────────────────

def encode_24bit(scheme: int, fields: list) -> int:
    """Pack a scheme and field values into a 24-bit integer.

    Args:
        scheme: 4-bit scheme ID (0-15)
        fields: Field values, order matches the scheme's field widths

    Returns:
        24-bit integer

    Raises:
        ValueError: if scheme is invalid, field count mismatches, or
                    any field exceeds its bit budget
    """
    if not (0 <= scheme <= MAX_SCHEME):
        raise ValueError(f"Invalid scheme {scheme}, must be 0-{MAX_SCHEME}")

    field_widths = SCHEME_FIELD_WIDTHS.get(scheme, [])
    field_names = SCHEME_FIELD_NAMES.get(scheme, [])

    if len(fields) != len(field_widths):
        raise ValueError(
            f"Scheme {scheme} ({SCHEME_NAMES.get(scheme, 'UNKNOWN')}) expects "
            f"{len(field_widths)} fields, got {len(fields)}"
        )

    value = scheme << FIELD_BITS  # Top 4 bits = scheme

    offset = FIELD_BITS
    for i, (fw, fv) in enumerate(zip(field_widths, fields)):
        fname = field_names[i] if i < len(field_names) else f"field_{i}"
        max_fv = (1 << fw) - 1
        if not (0 <= fv <= max_fv):
            raise ValueError(
                f"Field '{fname}' value {fv} exceeds {fw}-bit max {max_fv}"
            )
        offset -= fw
        value |= (fv << offset)

    return value & MAX_VALUE


def cast_24bit(raw_value: int) -> int:
    """Clamp any integer to valid 24-bit range (0 to 0xFFFFFF).

    Negative values are wrapped modulo 2^24 into positive range.
    Overflowing values are masked to 24 bits.
    """
    return raw_value & MAX_VALUE


# ── Decoding ───────────────────────────────────────────────────────────

def decode_24bit(value: int) -> Tuple[int, list]:
    """Unpack a 24-bit integer into (scheme, fields).

    Args:
        value: 24-bit integer

    Returns:
        (scheme, list_of_field_values)
    """
    value = value & MAX_VALUE
    scheme = (value >> FIELD_BITS) & MAX_SCHEME
    field_widths = SCHEME_FIELD_WIDTHS.get(scheme, [])
    field_names = SCHEME_FIELD_NAMES.get(scheme, [])

    fields = []
    remaining = value & ((1 << FIELD_BITS) - 1)  # bottom 20 bits
    bit_pos = FIELD_BITS

    for i, fw in enumerate(field_widths):
        bit_pos -= fw
        fv = (remaining >> bit_pos) & ((1 << fw) - 1)
        fields.append(fv)

    return scheme, fields


# ── PLATO JSON Conversion ──────────────────────────────────────────────

def tile_to_plato_json(value_24bit: int, source: str) -> dict:
    """Convert a 24-bit tile into a PLATO-friendly JSON dict.

    Args:
        value_24bit: The raw 24-bit integer tile value
        source:      Source identifier, e.g. "go/agent-1"

    Returns:
        dict with keys: tile_type, scheme, fields, value, source, timestamp
    """
    import time
    scheme, fields = decode_24bit(value_24bit)
    scheme_name = SCHEME_NAMES.get(scheme, f"CUSTOM_{scheme}")
    field_names = SCHEME_FIELD_NAMES.get(scheme, [f"f{i}" for i in range(len(fields))])

    return {
        "type": "tile",
        "tile_type": scheme_name,
        "scheme": scheme,
        "scheme_name": scheme_name,
        "fields": {k: v for k, v in zip(field_names, fields)},
        "value": value_24bit,
        "source": source,
        "timestamp": time.time(),
    }


def plato_json_to_tile(data: dict) -> int:
    """Extract a 24-bit integer from a PLATO JSON dict.

    Accepts dicts with either a 'value' key (direct 24-bit int)
    or 'scheme' + 'fields' keys (will encode on the fly).
    """
    if "value" in data:
        return cast_24bit(int(data["value"]))
    if "scheme" in data and "fields" in data:
        return encode_24bit(int(data["scheme"]), list(map(int, data["fields"])))
    raise ValueError(
        "PLATO JSON must contain 'value' or ('scheme' + 'fields')"
    )


# ── Utilities ──────────────────────────────────────────────────────────

def format_tile(value_24bit: int) -> str:
    """Return a human-readable string for a tile."""
    scheme, fields = decode_24bit(value_24bit)
    scheme_name = SCHEME_NAMES.get(scheme, f"CUSTOM_{scheme}")
    field_names = SCHEME_FIELD_NAMES.get(scheme, [f"f{i}" for i in range(len(fields))])
    field_str = ", ".join(f"{k}={v}" for k, v in zip(field_names, fields))
    hex_str = f"0x{value_24bit:06X}"
    return f"[{scheme_name}] ({hex_str}) {field_str}"


def random_tile(max_scheme: int = 7) -> int:
    """Generate a random valid 24-bit tile (for testing)."""
    import random
    scheme = random.randint(0, max_scheme)
    field_widths = SCHEME_FIELD_WIDTHS.get(scheme, [])
    fields = [random.randint(0, (1 << fw) - 1) for fw in field_widths]
    return encode_24bit(scheme, fields)
