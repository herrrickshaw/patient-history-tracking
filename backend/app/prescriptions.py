"""Synthetic medication/prescription tracker for the current encounter.

Drug names are real generics (for realism), but doses, routes, and
administration timing are illustrative demo values on a compressed
schedule -- not real dosing intervals, not medical advice, and not
connected to any pharmacy or EMR system.
"""
from __future__ import annotations

DISCLAIMER = (
    "Synthetic prescription/administration tracker. Drug names are real "
    "generics for realism, but doses, routes, and timing are illustrative "
    "demo values on a compressed schedule -- not real dosing intervals, not "
    "medical advice, and not connected to any pharmacy or EMR system."
)

# (drug, dose, route, demo_frequency_sim_sec) -- frequency 0 means a single
# continuous order (e.g. an infusion) rather than a repeating dose.
DEFAULT_ORDERS = [
    ("Paracetamol", "1g", "IV", 60),
    ("Ondansetron", "4mg", "IV", 90),
    ("Normal Saline", "100mL/hr", "IV infusion", 0),
    ("Cefazolin", "1g", "IV", 120),
]
SURGERY_EXTRA = [("Morphine", "2mg", "IV", 45)]
CARDIAC_EXTRA = [("Metoprolol", "25mg", "PO", 90)]


def generate_orders(department: str | None) -> list[dict]:
    dept = (department or "").lower()
    orders = list(DEFAULT_ORDERS)
    if "surg" in dept:
        orders += SURGERY_EXTRA
    if "cardi" in dept:
        orders += CARDIAC_EXTRA
    return [
        {"drug": drug, "dose": dose, "route": route, "frequency_sim_sec": freq, "status": "active", "next_due": None}
        for drug, dose, route, freq in orders
    ]
