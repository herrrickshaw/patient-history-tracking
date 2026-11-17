"""Synthetic ABHA-style identity (no VitalDB call)."""
import re

from app import patient_identity as pi


def test_synthetic_abha_format_and_determinism():
    a = pi._synthetic_abha_id(42)
    assert re.fullmatch(r"\d{2}-\d{4}-\d{4}-\d{4}", a)
    assert a == pi._synthetic_abha_id(42) != pi._synthetic_abha_id(43)


def test_synthetic_name_cycles_through_lists():
    assert pi._synthetic_name(0) == "Aarav Sharma"
    assert pi._synthetic_name(11) == "Priya Iyer"


def test_identity_carries_disclaimer(monkeypatch):
    monkeypatch.setattr(pi, "_clinical_row", lambda case_id: {"age": 50, "sex": "F", "department": "General"})
    ident = pi.build_identity("BED-1", 7)
    assert ident["disclaimer"] == pi.DISCLAIMER and ident["age"] == 50
