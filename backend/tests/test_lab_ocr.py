import io

import pytest
from PIL import Image

from app import lab_ocr


def one(text):
    out = lab_ocr.parse_candidates(text)
    assert len(out) == 1, out
    return out[0]


def test_full_line_with_range_computes_flag_from_range():
    c = one("Hemoglobin 13.5 g/dL (12.0-16.0)")
    assert c == {
        "raw_line": "Hemoglobin 13.5 g/dL (12.0-16.0)",
        "test": "Hemoglobin",
        "value": "13.5",
        "unit": "g/dL",
        "reference_range": "12.0-16.0",
        "flag": "normal",
    }


@pytest.mark.parametrize(
    "value,flag",
    [("11.9", "low"), ("12.0", "normal"), ("16.0", "normal"), ("16.1", "high")],
)
def test_range_flag_boundaries_are_inclusive(value, flag):
    assert one(f"Creatinine {value} mg/dL (12.0-16.0)")["flag"] == flag


def test_flag_text_used_when_no_range_and_lowercased():
    assert one("Glucose 250 mg/dL HIGH")["flag"] == "high"
    assert one("Sodium 140 mmol/L Normal")["flag"] == "normal"


def test_range_takes_precedence_over_flag_text():
    assert one("Glucose 5 mg/dL (1-10) HIGH")["flag"] == "normal"


def test_no_flag_when_nothing_to_go_on():
    c = one("TSH 2.5")
    assert (c["value"], c["unit"], c["reference_range"], c["flag"]) == ("2.5", None, None, None)


def test_value_missing_leaves_value_and_unit_none():
    c = one("Hemoglobin pending")
    assert (c["value"], c["unit"], c["flag"]) == (None, None, None)


def test_flag_text_without_value_still_recorded():
    assert one("CRP pending CRITICAL")["flag"] == "critical"


def test_test_name_matching_is_case_insensitive_whole_word_and_keeps_input_case():
    assert one("hemoglobin 10 g/dL")["test"] == "hemoglobin"
    assert one("PLATELET COUNT 200 K/µL")["test"] == "PLATELET COUNT"
    assert lab_ocr.parse_candidates("Hbxyz 10 g/dL") == []
    assert lab_ocr.parse_candidates("SALTY 10") == []


def test_longer_alias_preferred_where_listed_first():
    assert one("Platelet Count 250")["test"] == "Platelet Count"
    assert one("White Blood Cell 7.1 x10^9/L")["test"] == "White Blood Cell"


def test_value_is_taken_after_the_test_name_only():
    # digits before the analyte name (e.g. a row number) must not become the value
    c = one("12 Potassium 4.1 mmol/L")
    assert c["value"] == "4.1"


def test_noise_short_and_blank_lines_skipped_and_order_preserved():
    text = "\n  \nab\nPatient Name: X\nGlucose 90 mg/dL\n\nUrea 30 mg/dL\nPage 1\n"
    assert [c["test"] for c in lab_ocr.parse_candidates(text)] == ["Glucose", "Urea"]
    assert lab_ocr.parse_candidates("") == []


def test_extract_text_decodes_image_and_calls_tesseract(monkeypatch):
    seen = {}

    def fake(image):
        seen["size"] = image.size
        return "Glucose 1"

    monkeypatch.setattr(lab_ocr.pytesseract, "image_to_string", fake)
    buf = io.BytesIO()
    Image.new("RGB", (7, 5)).save(buf, format="PNG")
    assert lab_ocr.extract_text(buf.getvalue()) == "Glucose 1"
    assert seen["size"] == (7, 5)


def test_extract_text_rejects_non_image_bytes():
    with pytest.raises(Exception):
        lab_ocr.extract_text(b"not an image")


def test_three_character_analyte_line_is_kept_without_a_value():
    out = lab_ocr.parse_candidates("TSH")
    assert [(c["test"], c["value"]) for c in out] == [("TSH", None)]
