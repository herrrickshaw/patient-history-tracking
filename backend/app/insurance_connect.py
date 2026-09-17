"""Synthetic insurance-connect layer, keyed by the same (fake) ABHA ID
as patient_identity.py.

Modelled on two real patterns, used here only as a design reference:
  - Germany's gematik Telematikinfrastruktur: a statutory insurer
    electronically confirms coverage when a patient's eGK (health
    card) is read at admission, and receives the billing claim at
    discharge.
  - India's ABDM Health Claims Exchange (HCX): standardises eligibility
    checks and claim submission between providers and payers, linked
    by the patient's ABHA number.

This module invents everything -- insurer names, policy numbers,
approval decisions -- and never calls a real insurer, payer network,
or claims clearinghouse. No real financial transaction occurs.
"""
from __future__ import annotations

import hashlib

DISCLAIMER = (
    "Simulated insurance connect, patterned after Germany's gematik TI "
    "eligibility-verification model and India's ABDM Health Claims Exchange "
    "(HCX). Insurer names, policy numbers, and claim decisions are invented; "
    "no real insurer, payer, or claims network is involved."
)

_INSURERS = [
    "Yojana Mutual Health",
    "Concordia Health Assurance",
    "Sahayata General Insurance",
    "Nordkreis Krankenkasse (demo)",
    "Bharosa Health Trust",
]

_records: dict[str, dict] = {}


def _hash_int(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest(), 16)


def _policy_number(abha_id: str) -> str:
    h = _hash_int("policy", abha_id)
    return f"POL-{h % 10**9:09d}"


def check_eligibility(abha_id: str) -> dict:
    insurer = _INSURERS[_hash_int("insurer", abha_id) % len(_INSURERS)]
    eligible = _hash_int("eligible", abha_id) % 20 != 0  # ~95% eligible
    record = _records.setdefault(abha_id, {"insurer": insurer, "policy_number": _policy_number(abha_id)})
    record["eligibility_status"] = "eligible" if eligible else "coverage_lapsed"
    record["authorization_ref"] = f"AUTH-{_hash_int('auth', abha_id, str(record.get('_checks', 0))) % 10**8:08d}"
    record["_checks"] = record.get("_checks", 0) + 1
    return {
        "insurer": record["insurer"],
        "policy_number": record["policy_number"],
        "status": record["eligibility_status"],
        "authorization_ref": record["authorization_ref"],
    }


def submit_claim(abha_id: str, encounter: dict) -> dict:
    record = _records.setdefault(abha_id, {"insurer": _INSURERS[0], "policy_number": _policy_number(abha_id)})
    claim_seq = record.get("_claims", 0) + 1
    record["_claims"] = claim_seq
    claim_id = f"CLM-{_hash_int('claim', abha_id, str(claim_seq)) % 10**10:010d}"
    amount = 80 + (_hash_int("amount", abha_id, str(claim_seq)) % 420)  # illustrative units, currency intentionally unspecified
    approved = _hash_int("approve", abha_id, str(claim_seq)) % 10 != 0  # ~90% auto-approved
    claim = {
        "claim_id": claim_id,
        "insurer": record["insurer"],
        "amount_estimate": amount,
        "status": "approved" if approved else "under_review",
        "procedure": encounter.get("procedure"),
        "department": encounter.get("department"),
    }
    record["last_claim"] = claim
    return claim


def get_record(abha_id: str) -> dict | None:
    return _records.get(abha_id)
