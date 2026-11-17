"""Simulated insurance connect: deterministic per synthetic ID, persisted counters."""
import re

from app import insurance_connect as ic

ABHA = "12-3456-7890-1234"   # synthetic


def test_eligibility_is_deterministic_and_counts_checks(fresh_db):
    a = ic.check_eligibility(ABHA)
    b = ic.check_eligibility(ABHA)
    assert (a["insurer"], a["policy_number"], a["status"]) == (b["insurer"], b["policy_number"], b["status"])
    assert a["authorization_ref"] != b["authorization_ref"]          # new auth per check
    assert re.fullmatch(r"POL-\d{9}", a["policy_number"])
    assert ic.get_record(ABHA)["_checks"] == 2


def test_claims_numbered_per_patient(fresh_db):
    c1 = ic.submit_claim(ABHA, {"procedure": "synthetic", "department": "General"})
    c2 = ic.submit_claim(ABHA, {"procedure": "synthetic", "department": "General"})
    assert c1["claim_id"] != c2["claim_id"]
    assert 80 <= c1["amount_estimate"] < 500
    assert c1["status"] in {"approved", "under_review"}
