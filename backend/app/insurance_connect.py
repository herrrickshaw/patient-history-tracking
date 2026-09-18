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

Backed by SQLite (backend/app/db.py) so eligibility/claim history
survives a server restart.
"""
from __future__ import annotations

import hashlib

from . import db

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


def _hash_int(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest(), 16)


def _insurer(abha_id: str) -> str:
    return _INSURERS[_hash_int("insurer", abha_id) % len(_INSURERS)]


def _policy_number(abha_id: str) -> str:
    h = _hash_int("policy", abha_id)
    return f"POL-{h % 10**9:09d}"


def check_eligibility(abha_id: str) -> dict:
    existing = db.get_insurance_record(abha_id)
    checks = (existing["_checks"] if existing else 0) + 1
    insurer = _insurer(abha_id)
    policy_number = _policy_number(abha_id)
    eligible = _hash_int("eligible", abha_id) % 20 != 0  # ~95% eligible
    status = "eligible" if eligible else "coverage_lapsed"
    auth_ref = f"AUTH-{_hash_int('auth', abha_id, str(checks)) % 10**8:08d}"
    db.upsert_insurance_eligibility(abha_id, insurer, policy_number, status, auth_ref, checks)
    return {"insurer": insurer, "policy_number": policy_number, "status": status, "authorization_ref": auth_ref}


def submit_claim(abha_id: str, encounter: dict) -> dict:
    existing = db.get_insurance_record(abha_id)
    claims = (existing["_claims"] if existing else 0) + 1
    insurer = _insurer(abha_id)
    policy_number = _policy_number(abha_id)
    claim_id = f"CLM-{_hash_int('claim', abha_id, str(claims)) % 10**10:010d}"
    amount = 80 + (_hash_int("amount", abha_id, str(claims)) % 420)  # illustrative units, currency intentionally unspecified
    approved = _hash_int("approve", abha_id, str(claims)) % 10 != 0  # ~90% auto-approved
    claim = {
        "claim_id": claim_id,
        "insurer": insurer,
        "amount_estimate": amount,
        "status": "approved" if approved else "under_review",
        "procedure": encounter.get("procedure"),
        "department": encounter.get("department"),
    }
    db.upsert_insurance_claim(abha_id, insurer, policy_number, claim, claims)
    return claim


def get_record(abha_id: str) -> dict | None:
    return db.get_insurance_record(abha_id)
