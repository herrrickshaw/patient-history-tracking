import io

import pytest
from PIL import Image

from app import prescription_ocr as po


def one(text):
    out = po.parse_candidates(text)
    assert len(out) == 1, out
    return out[0]


def test_full_line_parsed_into_fields():
    c = one("Paracetamol 500mg PO BD")
    assert c == {
        "raw_line": "Paracetamol 500mg PO BD",
        "drug": "Paracetamol",
        "dose": "500mg",
        "route": "PO",
        "frequency_abbrev": "BD",
        "frequency_sim_sec": po.FREQUENCY_MAP["BD"],
    }


@pytest.mark.parametrize("abbr", sorted(po.FREQUENCY_MAP))
def test_every_frequency_abbreviation_maps_through_the_table(abbr):
    c = one(f"Drugname 5 mg {abbr.lower()}")
    assert c["frequency_abbrev"] == abbr
    assert c["frequency_sim_sec"] == po.FREQUENCY_MAP[abbr]


def test_dose_with_space_decimal_and_units_variants():
    assert one("Foo 2.5 mg")["dose"] == "2.5 mg"
    assert one("Foo 10 IU")["dose"] == "10 IU"
    assert one("Foo 3 units")["dose"] == "3 units"
    assert one("Foo 4 unit")["dose"] == "4 unit"


def test_route_upper_cased_and_optional_fields_none():
    assert one("Foo 5mg iv")["route"] == "IV"
    c = one("Mystery syrup")
    assert (c["dose"], c["route"], c["frequency_abbrev"], c["frequency_sim_sec"]) == (None, None, None, None)
    assert c["drug"] == "Mystery syrup"


def test_drug_strips_trailing_punctuation_left_after_removals():
    assert one("Foo, 5 mg PO;")["drug"] == "Foo"
    assert one("Foo - 5mg -")["drug"] == "Foo"


def test_drug_falls_back_to_whole_line_when_nothing_remains():
    c = one("500mg PO")
    assert c["drug"] == "500mg PO"


def test_frequency_must_be_a_whole_word():
    assert one("Bodacious 5 mg")["frequency_abbrev"] is None
    assert one("Foo ODD")["frequency_abbrev"] is None


def test_short_and_blank_lines_skipped_and_order_preserved():
    assert po.parse_candidates("") == []
    assert po.parse_candidates("\n ab \n   \n") == []
    assert [c["drug"] for c in po.parse_candidates("Alpha 1 mg\nBeta 2 mg")] == ["Alpha", "Beta"]


def test_extract_text(monkeypatch):
    monkeypatch.setattr(po.pytesseract, "image_to_string", lambda im: f"size={im.size}")
    buf = io.BytesIO()
    Image.new("L", (3, 4)).save(buf, format="PNG")
    assert po.extract_text(buf.getvalue()) == "size=(3, 4)"
    with pytest.raises(Exception):
        po.extract_text(b"garbage")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="ROUTE_PATTERN lists IV before \"IV infusion\", so the longer alternative is unreachable")
def test_iv_infusion_route_recognised_as_a_whole():
    """The route regex lists "IV" before "IV infusion", so the longer alias can
    never match; "IV infusion" is truncated to "IV" and the word is left in the drug name."""
    c = one("Normal Saline 100 ml iv infusion")
    assert c["route"] == "IV INFUSION"


def test_three_character_line_is_kept_but_two_is_skipped():
    assert po.parse_candidates("PRN")[0]["frequency_abbrev"] == "PRN"
    assert po.parse_candidates("PR") == []


def test_frequency_table_pins_the_documented_demo_cadences():
    # Characterisation of the illustrative compressed schedule (sim-seconds).
    assert po.FREQUENCY_MAP == {
        "OD": 120, "QD": 120, "BD": 90, "BID": 90, "TDS": 60, "TID": 60,
        "QID": 45, "QDS": 45, "HS": 150, "STAT": None, "PRN": None, "SOS": None,
    }
