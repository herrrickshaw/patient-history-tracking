from __future__ import annotations

import re

from app import patient_identity, prescriptions


def test_synthetic_id_is_deterministic_and_well_formed():
    a = patient_identity._synthetic_abha_id(42)
    assert a == patient_identity._synthetic_abha_id(42)
    assert re.fullmatch(r"\d{2}-\d{4}-\d{4}-\d{4}", a)
    assert a != patient_identity._synthetic_abha_id(43)


def test_synthetic_name_is_deterministic():
    assert patient_identity._synthetic_name(0) == "Aarav Sharma"
    assert patient_identity._synthetic_name(1) == "Priya Sharma"


def test_orders_by_department():
    base = {o["drug"] for o in prescriptions.generate_orders(None)}
    assert "Morphine" not in base
    assert "Morphine" in {o["drug"] for o in prescriptions.generate_orders("General Surgery")}
    assert "Metoprolol" in {o["drug"] for o in prescriptions.generate_orders("Cardiology")}
    assert all(o["status"] == "active" and o["next_due"] is None for o in prescriptions.generate_orders(None))
