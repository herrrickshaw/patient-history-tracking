"""Shared fixtures. Everything is synthetic and offline:

* ``vitaldb`` (network dataset client) is replaced by a small in-memory fake
  *before* any app module is imported;
* the SQLite layer is pointed at a temp file per test;
* OCR (``pytesseract``) is patched where used.
No real patient data and no clinical reference values are involved: assertions
check the code's own control flow and arithmetic.
"""
import sys
import types
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeRow:
    def __init__(self, data):
        self._d = data

    def to_dict(self):
        return dict(self._d)


class FakeFrame:
    def __init__(self, rows):
        self._rows = rows
        self.iloc = self

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, i):
        return FakeRow(self._rows[i])


fake_vitaldb = types.ModuleType("vitaldb")
fake_vitaldb.calls = []


def _load_case(case_id, tracks, interval=1):
    fake_vitaldb.calls.append(("load_case", case_id, tuple(tracks), interval))
    return fake_vitaldb.case_data(case_id, tracks, interval)


def _case_data(case_id, tracks, interval):
    n = 5 if interval == 1 else int(5 / interval)
    return np.tile(np.arange(len(tracks), dtype=float), (n, 1)) + case_id


def _load_clinical(caseids):
    fake_vitaldb.calls.append(("load_clinical_data", tuple(caseids)))
    return FakeFrame([{"age": 40, "sex": "F", "department": "General surgery", "opname": "Op", "dx": "Dx", "asa": 2}])


fake_vitaldb.load_case = _load_case
fake_vitaldb.case_data = _case_data
fake_vitaldb.load_clinical_data = _load_clinical
fake_vitaldb.find_cases = lambda tracks: list(range(100, 130))
sys.modules["vitaldb"] = fake_vitaldb

import pytest  # noqa: E402


@pytest.fixture
def vitaldb_fake(monkeypatch):
    fake_vitaldb.calls.clear()
    monkeypatch.setattr(fake_vitaldb, "case_data", _case_data)
    monkeypatch.setattr(fake_vitaldb, "load_clinical_data", _load_clinical)
    monkeypatch.setattr(fake_vitaldb, "find_cases", lambda tracks: list(range(100, 130)))
    return fake_vitaldb


@pytest.fixture
def db(tmp_path, monkeypatch):
    from app import db as appdb

    monkeypatch.setattr(appdb, "DB_PATH", tmp_path / "nested" / "app.db")
    monkeypatch.setattr(appdb, "_conn", None)
    appdb.init_db()
    yield appdb
    if appdb._conn is not None:
        appdb._conn.close()
    monkeypatch.setattr(appdb, "_conn", None)
