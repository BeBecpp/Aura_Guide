from __future__ import annotations

from typing import Dict

VALID_KEYS = {"F", "L", "R", "B"}


def parse_sensor_line(line: str) -> Dict[str, int]:
    """Parse Arduino serial protocol: F:80,L:150,R:45,B:200."""
    result: Dict[str, int] = {}
    if not line:
        return result

    raw = line.strip().replace("\r", "").replace("\n", "")
    for part in raw.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip().upper()
        if key not in VALID_KEYS:
            continue
        try:
            distance = int(float(value.strip()))
        except ValueError:
            continue
        if 0 < distance <= 500:
            result[key] = distance
    return result
