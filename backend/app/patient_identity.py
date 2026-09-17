"""Synthetic patient-identity card, standing in for the ABHA (Ayushman
Bharat Health Account) linkage a real Indian hospital system shows on
a patient's chart.

Everything here is FAKE and generated: VitalDB cases carry no patient
name or national health ID, so both are invented deterministically
from the case id purely for demo purposes. This never calls, mimics,
or claims to be the real ABHA/NHA API -- see DISCLAIMER below, which
the frontend must always display alongside this data.
"""
from __future__ import annotations

import hashlib

import vitaldb

DISCLAIMER = (
    "Synthetic demo record. Not a real ABHA (Ayushman Bharat Health Account) "
    "number and not connected to any government health ID system."
)

_FIRST_NAMES = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Kavya", "Arjun", "Meera", "Sanjay", "Divya"]
_LAST_NAMES = ["Sharma", "Iyer", "Reddy", "Menon", "Kapoor", "Nair", "Gupta", "Rao", "Verma", "Pillai"]

_clinical_cache: dict[int, dict] | None = None


def _clinical_row(case_id: int) -> dict:
    global _clinical_cache
    if _clinical_cache is None:
        _clinical_cache = {}
    if case_id not in _clinical_cache:
        df = vitaldb.load_clinical_data(caseids=[case_id])
        _clinical_cache[case_id] = df.iloc[0].to_dict() if len(df) else {}
    return _clinical_cache[case_id]


def _synthetic_abha_id(case_id: int) -> str:
    digest = hashlib.sha256(f"demo-abha-{case_id}".encode()).hexdigest()
    digits = "".join(c for c in digest if c.isdigit())[:14].ljust(14, "0")
    return f"{digits[0:2]}-{digits[2:6]}-{digits[6:10]}-{digits[10:14]}"


def _synthetic_name(case_id: int) -> str:
    first = _FIRST_NAMES[case_id % len(_FIRST_NAMES)]
    last = _LAST_NAMES[(case_id // len(_FIRST_NAMES)) % len(_LAST_NAMES)]
    return f"{first} {last}"


def build_identity(bed_id: str, case_id: int) -> dict:
    clinical = _clinical_row(case_id)
    return {
        "bed_id": bed_id,
        "case_id": case_id,
        "name": _synthetic_name(case_id),
        "abha_id": _synthetic_abha_id(case_id),
        "age": clinical.get("age"),
        "sex": clinical.get("sex"),
        "department": clinical.get("department"),
        "procedure": clinical.get("opname"),
        "diagnosis": clinical.get("dx"),
        "asa_class": clinical.get("asa"),
        "disclaimer": DISCLAIMER,
    }
