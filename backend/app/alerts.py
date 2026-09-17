"""Threshold-based alarm rules, the same style of logic IntelliICU-class
dashboards use to turn raw vitals into caregiver-facing alerts.
"""
from __future__ import annotations

# (vital_key, low_critical, low_warning, high_warning, high_critical, unit)
RULES = [
    ("HR", 40, 50, 120, 150, "bpm"),
    ("SPO2", 85, 90, 101, 101, "%"),  # 100% SpO2 is healthy; no high-side alarm
    ("NIBP_SBP", 70, 90, 160, 180, "mmHg"),
    ("RR", 6, 10, 24, 30, "/min"),
    ("TEMP", 34.0, 35.5, 38.3, 39.5, "°C"),
]


def evaluate(vitals: dict[str, float | None]) -> list[dict]:
    alerts = []
    for key, lo_crit, lo_warn, hi_warn, hi_crit, unit in RULES:
        value = vitals.get(key)
        if value is None:
            continue
        if value <= lo_crit or value >= hi_crit:
            level = "critical"
        elif value <= lo_warn or value >= hi_warn:
            level = "warning"
        else:
            continue
        direction = "low" if value <= lo_warn else "high"
        alerts.append(
            {
                "vital": key,
                "level": level,
                "message": f"{key} {direction} ({value} {unit})",
            }
        )
    return alerts
