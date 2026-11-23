import re

import pytest

from app import patient_identity as pi


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setattr(pi, "_clinical_cache", None)


def test_abha_id_is_deterministic_and_formatted():
    a = pi._synthetic_abha_id(42)
    assert a == pi._synthetic_abha_id(42)
    assert re.fullmatch(r"\d{2}-\d{4}-\d{4}-\d{4}", a)
    assert len({pi._synthetic_abha_id(i) for i in range(50)}) == 50


def test_name_cycles_first_then_last_names():
    nf, nl = len(pi._FIRST_NAMES), len(pi._LAST_NAMES)
    assert pi._synthetic_name(0) == f"{pi._FIRST_NAMES[0]} {pi._LAST_NAMES[0]}"
    assert pi._synthetic_name(1) == f"{pi._FIRST_NAMES[1]} {pi._LAST_NAMES[0]}"
    assert pi._synthetic_name(nf) == f"{pi._FIRST_NAMES[0]} {pi._LAST_NAMES[1]}"
    assert pi._synthetic_name(nf * nl) == pi._synthetic_name(0)


def test_build_identity_maps_clinical_columns(vitaldb_fake):
    ident = pi.build_identity("Bed-A", 7)
    assert (ident["bed_id"], ident["case_id"]) == ("Bed-A", 7)
    assert ident["name"] == pi._synthetic_name(7)
    assert ident["abha_id"] == pi._synthetic_abha_id(7)
    assert (ident["age"], ident["sex"], ident["department"]) == (40, "F", "General surgery")
    assert (ident["procedure"], ident["diagnosis"], ident["asa_class"]) == ("Op", "Dx", 2)
    assert ident["disclaimer"] == pi.DISCLAIMER


def test_clinical_row_cached_per_case(vitaldb_fake):
    pi.build_identity("a", 7)
    pi.build_identity("b", 7)
    pi.build_identity("c", 8)
    loads = [c for c in vitaldb_fake.calls if c[0] == "load_clinical_data"]
    assert loads == [("load_clinical_data", (7,)), ("load_clinical_data", (8,))]


def test_missing_clinical_row_gives_none_fields(vitaldb_fake, monkeypatch):
    from conftest import FakeFrame

    monkeypatch.setattr(vitaldb_fake, "load_clinical_data", lambda caseids: FakeFrame([]))
    ident = pi.build_identity("Bed-X", 3)
    assert all(ident[k] is None for k in ("age", "sex", "department", "procedure", "diagnosis", "asa_class"))
    assert ident["name"] == pi._synthetic_name(3)


def test_abha_digits_are_the_first_fourteen_digits_of_the_seeded_hash():
    import hashlib

    digest = hashlib.sha256(b"demo-abha-42").hexdigest()
    digits = "".join(c for c in digest if c.isdigit())[:14]
    assert pi._synthetic_abha_id(42).replace("-", "") == digits
