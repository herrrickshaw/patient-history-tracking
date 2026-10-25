"""OCR line parsers on synthetic text (Tesseract itself is not invoked)."""
import pytest

from app import lab_ocr, prescription_ocr


def test_prescription_line_fields():
    (c,) = prescription_ocr.parse_candidates("Paracetamol 500mg PO TDS")
    assert (c["drug"], c["dose"], c["route"], c["frequency_abbrev"]) == ("Paracetamol", "500mg", "PO", "TDS")
    assert c["frequency_sim_sec"] == prescription_ocr.FREQUENCY_MAP["TDS"]


def test_prn_has_no_repeat_cadence_and_short_lines_skipped():
    out = prescription_ocr.parse_candidates("ok\nOndansetron 4 mg IV SOS")
    assert len(out) == 1
    assert out[0]["frequency_abbrev"] == "SOS" and out[0]["frequency_sim_sec"] is None


def test_iv_infusion_route_is_matched_whole():
    """'IV' preceded 'IV infusion' in the alternation, so the longer route could never match."""
    (c,) = prescription_ocr.parse_candidates("Normal Saline 100 ml IV infusion")
    assert c["route"] == "IV INFUSION"
    assert c["drug"] == "Normal Saline"


def test_lab_line_with_range_flags_low_and_high():
    out = lab_ocr.parse_candidates("Hemoglobin 9.8 g/dL (12.0-15.5)\nWBC 12.4 x10^9/L (4.0-11.0)\nPatient: Synth")
    assert [(c["test"], c["value"], c["flag"]) for c in out] == [("Hemoglobin", "9.8", "low"), ("WBC", "12.4", "high")]
    assert out[0]["unit"] == "g/dL" and out[0]["reference_range"] == "12.0-15.5"


def test_lab_flag_text_used_when_no_range():
    (c,) = lab_ocr.parse_candidates("Potassium 5.9 mmol/L HIGH")
    assert c["flag"] == "high" and c["value"] == "5.9"


def test_lab_value_boundary_is_normal():
    (c,) = lab_ocr.parse_candidates("Sodium 135 mEq/L (135-145)")
    assert c["flag"] == "normal"


def test_thousands_separators_are_read_as_one_number():
    """'2,50,000' (Indian grouping) / '250,000' were read as value '2' / '250'."""
    a, b = lab_ocr.parse_candidates("Platelet Count 2,50,000 /µL (1,50,000-4,50,000)\n"
                                    "Platelets 120,000 /µL (150,000-450,000)")
    assert (a["value"], a["flag"]) == ("250000", "normal")
    assert (b["value"], b["flag"]) == ("120000", "low")
