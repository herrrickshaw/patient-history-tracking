import hashlib
import re

import pytest

from app import discharge_summary, health_record, insurance_connect


def find_abha(pred, limit=5000):
    for i in range(limit):
        a = f"synthetic-{i}"
        if pred(a):
            return a
    raise AssertionError("no synthetic id satisfied predicate")


# ---------------- health_record ----------------

def test_health_record_pushes_through_to_db(db):
    health_record.push_event("P", "admission", "Bed-A", 3, {"k": "v"})
    (e,) = health_record.get_timeline("P")
    assert (e["type"], e["source"], e["sim_t"], e["payload"]) == ("admission", "Bed-A", 3, {"k": "v"})
    assert health_record.get_timeline("other") == []
    assert "Simulated" in health_record.DISCLAIMER


# ---------------- insurance_connect ----------------

def test_hash_int_is_sha256_of_pipe_joined_parts():
    assert insurance_connect._hash_int("a", "b") == int(hashlib.sha256(b"a|b").hexdigest(), 16)
    assert insurance_connect._hash_int("a|b") == insurance_connect._hash_int("a", "b")
    assert insurance_connect._hash_int("a", "b") != insurance_connect._hash_int("b", "a")


def test_insurer_and_policy_are_deterministic_and_well_formed():
    for i in range(30):
        a = f"id-{i}"
        assert insurance_connect._insurer(a) in insurance_connect._INSURERS
        assert insurance_connect._insurer(a) == insurance_connect._insurer(a)
        assert re.fullmatch(r"POL-\d{9}", insurance_connect._policy_number(a))
    assert len({insurance_connect._policy_number(f"id-{i}") for i in range(30)}) > 1


def test_eligibility_counts_checks_and_changes_auth_ref(db):
    a = "abha-1"
    first = insurance_connect.check_eligibility(a)
    second = insurance_connect.check_eligibility(a)
    assert re.fullmatch(r"AUTH-\d{8}", first["authorization_ref"])
    assert first["authorization_ref"] != second["authorization_ref"]
    assert (first["insurer"], first["policy_number"]) == (second["insurer"], second["policy_number"])
    rec = insurance_connect.get_record(a)
    assert rec["_checks"] == 2
    assert rec["authorization_ref"] == second["authorization_ref"]
    assert insurance_connect.get_record("never") is None


def test_eligibility_status_follows_hash_rule(db):
    lapsed = find_abha(lambda a: insurance_connect._hash_int("eligible", a) % 20 == 0)
    ok = find_abha(lambda a: insurance_connect._hash_int("eligible", a) % 20 != 0)
    assert insurance_connect.check_eligibility(lapsed)["status"] == "coverage_lapsed"
    assert insurance_connect.check_eligibility(ok)["status"] == "eligible"


def test_claim_fields_counter_and_status_rule(db):
    a = "abha-claim"
    c1 = insurance_connect.submit_claim(a, {"procedure": "P", "department": "D"})
    c2 = insurance_connect.submit_claim(a, {})
    assert re.fullmatch(r"CLM-\d{10}", c1["claim_id"])
    assert c1["claim_id"] != c2["claim_id"]
    assert 80 <= c1["amount_estimate"] < 500
    assert (c1["procedure"], c1["department"]) == ("P", "D")
    assert (c2["procedure"], c2["department"]) == (None, None)
    rec = insurance_connect.get_record(a)
    assert rec["_claims"] == 2 and rec["last_claim"] == c2
    expected = "approved" if insurance_connect._hash_int("approve", a, "1") % 10 != 0 else "under_review"
    assert c1["status"] == expected


def test_claim_review_branch(db):
    review = find_abha(lambda a: insurance_connect._hash_int("approve", a, "1") % 10 == 0)
    approved = find_abha(lambda a: insurance_connect._hash_int("approve", a, "1") % 10 != 0)
    assert insurance_connect.submit_claim(review, {})["status"] == "under_review"
    assert insurance_connect.submit_claim(approved, {})["status"] == "approved"


def test_claim_after_eligibility_keeps_both_counters(db):
    a = "abha-both"
    insurance_connect.check_eligibility(a)
    insurance_connect.submit_claim(a, {})
    rec = insurance_connect.get_record(a)
    assert (rec["_checks"], rec["_claims"]) == (1, 1)
    assert rec["eligibility_status"] in ("eligible", "coverage_lapsed")


# ---------------- discharge_summary ----------------

IDENTITY = {"abha_id": "A-1", "name": "Test Person", "age": 33, "sex": "F", "department": "Dept", "procedure": "Proc", "diagnosis": "Dx"}


def build(**over):
    kw = dict(
        identity=IDENTITY, admitted_sim_t=10, discharged_sim_t=50,
        vitals_range={"HR": {"min": 1, "max": 9, "last": 5}},
        alert_events=[{"sim_t": 12, "payload": {"message": "HR high (9 bpm)", "vital": "HR"}}],
        medication_events=[{"sim_t": 14, "payload": {"drug": "DrugX", "dose": "1g", "route": "IV"}}],
        claim={"insurer": "Ins", "claim_id": "C1", "amount_estimate": 99, "status": "approved"},
    )
    kw.update(over)
    return discharge_summary.build(**kw)


def test_build_computes_duration_defaults_labs_and_persists(db):
    s = build()
    assert s["duration_sim_sec"] == 40
    assert s["lab_results"] == []
    assert (s["abha_id"], s["name"], s["age"], s["department"]) == ("A-1", "Test Person", 33, "Dept")
    assert s["disclaimer"] == discharge_summary.DISCLAIMER
    assert discharge_summary.latest("A-1") == s
    assert discharge_summary.latest("nobody") is None


def test_build_optional_identity_fields_default_to_none(db):
    s = build(identity={"abha_id": "A-2", "name": "N"})
    assert (s["age"], s["sex"], s["department"], s["procedure"], s["diagnosis"]) == (None,) * 5


def lab(test="Glucose", value="5", unit="mg/dL", rng="1-9", flag="normal"):
    return {"sim_t": 20, "payload": {"test": test, "value": value, "unit": unit, "reference_range": rng, "flag": flag}}


def test_render_html_contains_sections_and_labels(db):
    s = build(lab_events=[lab()])
    html = discharge_summary.render_html(s)
    assert "Test Person" in html and "A-1" in html
    assert "Heart rate (bpm)" in html
    assert "<td>1</td><td>9</td><td>5</td>" in html
    assert "t=12s" in html and "HR high (9 bpm)" in html
    assert "DrugX 1g (IV)" in html
    assert "<td>Glucose</td><td>5 mg/dL</td><td>1-9</td><td>normal</td>" in html
    assert "Ins" in html and "claim C1" in html and "99 units" in html
    assert "SYNTHETIC DEMO DOCUMENT" in html
    assert html.count("None recorded") == 0


def test_render_html_empty_sections(db):
    s = build(alert_events=[], medication_events=[], vitals_range={})
    html = discharge_summary.render_html(s)
    assert html.count("None recorded") == 3  # alerts, medications, labs
    assert "<table><thead><tr><th>Test</th>" not in html


def test_render_html_unknown_vital_key_and_missing_values_and_alert_fallback(db):
    s = build(
        vitals_range={"ZZ": {"min": None, "max": 3}},
        alert_events=[{"sim_t": 1, "payload": {"vital": "HR"}}],
        claim=None,
    )
    html = discharge_summary.render_html(s)
    assert "<td>ZZ</td><td>—</td><td>3</td><td>—</td>" in html
    assert "t=1s — HR" in html
    assert "claim —" in html


def test_render_html_lab_unit_none_renders_blank(db):
    s = build(lab_events=[lab(unit=None)])
    assert "<td>5 </td>" in discharge_summary.render_html(s)


def test_render_html_escapes_untrusted_text(db):
    s = build(identity={**IDENTITY, "name": "<script>alert(1)</script>"}, lab_events=[lab(test="<b>x</b>")])
    html = discharge_summary.render_html(s)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>x</b>" not in html and "&lt;b&gt;x&lt;/b&gt;" in html


def test_esc_none_vs_zero():
    assert discharge_summary._esc(None) == "—"
    assert discharge_summary._esc(0) == "0"
    assert discharge_summary._esc("a&b") == "a&amp;b"
