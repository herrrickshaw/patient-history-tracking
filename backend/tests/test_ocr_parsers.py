from __future__ import annotations

from app import lab_ocr, prescription_ocr


def test_prescription_line_is_split_into_fields():
    (c,) = prescription_ocr.parse_candidates("Paracetamol 500mg PO TDS")
    assert c["drug"] == "Paracetamol"
    assert c["dose"] == "500mg"
    assert c["route"] == "PO"
    assert c["frequency_abbrev"] == "TDS"
    assert c["frequency_sim_sec"] == 60


def test_prescription_stat_has_no_cadence_and_short_lines_are_dropped():
    cands = prescription_ocr.parse_candidates("ab\nMorphine 2mg IV STAT")
    assert len(cands) == 1
    assert cands[0]["frequency_abbrev"] == "STAT"
    assert cands[0]["frequency_sim_sec"] is None


def test_lab_line_value_unit_range_and_flag():
    (c,) = lab_ocr.parse_candidates("Hemoglobin 9.5 g/dL (12-16)")
    assert (c["test"], c["value"], c["unit"], c["reference_range"], c["flag"]) == (
        "Hemoglobin", "9.5", "g/dL", "12-16", "low",
    )


def test_lab_text_flag_and_unknown_lines_skipped():
    cands = lab_ocr.parse_candidates("Patient: John\nCRP 40 mg/dL HIGH")
    assert len(cands) == 1
    assert cands[0]["test"] == "CRP" and cands[0]["flag"] == "high"
