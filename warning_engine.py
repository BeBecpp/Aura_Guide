from __future__ import annotations

from typing import Dict, Optional

DIRECTION_TEXT = {
    "F": "Урд талд",
    "L": "Зүүн талд",
    "R": "Баруун талд",
    "B": "Ард талд",
}


class WarningEngine:
    def __init__(self):
        self.sensitivity = "normal"

    def set_sensitivity(self, value: str):
        if value in {"low", "normal", "high"}:
            self.sensitivity = value

    def thresholds(self):
        if self.sensitivity == "high":
            return {"warning": 160, "critical": 90, "very_close": 45}
        if self.sensitivity == "low":
            return {"warning": 90, "critical": 55, "very_close": 30}
        return {"warning": 120, "critical": 80, "very_close": 40}

    def severity_for_distance(self, distance: Optional[int]) -> str:
        if not isinstance(distance, int) or distance <= 0:
            return "no_data"
        t = self.thresholds()
        if distance <= t["very_close"]:
            return "very_close"
        if distance <= t["critical"]:
            return "critical"
        if distance <= t["warning"]:
            return "warning"
        return "safe"

    def evaluate(self, distances: Dict[str, Optional[int]]) -> Dict[str, object]:
        valid = {
            key: value
            for key, value in distances.items()
            if key in DIRECTION_TEXT and isinstance(value, int) and value > 0
        }
        if not valid:
            return {
                "direction": None,
                "distance": None,
                "severity": "no_data",
                "message": "Одоогоор дата ирээгүй байна",
            }

        nearest_direction = min(valid, key=valid.get)
        nearest_distance = valid[nearest_direction]
        severity = self.severity_for_distance(nearest_distance)

        if severity == "safe":
            return {
                "direction": None,
                "distance": None,
                "severity": "safe",
                "message": "Одоогоор ойр саад алга",
            }

        prefix = DIRECTION_TEXT[nearest_direction]
        if severity == "warning":
            msg = f"{prefix} саад байна"
        elif severity == "critical":
            msg = f"{prefix} ойр саад байна"
        else:
            msg = f"{prefix} маш ойр саад байна"

        return {
            "direction": nearest_direction,
            "distance": nearest_distance,
            "severity": severity,
            "message": msg,
        }
