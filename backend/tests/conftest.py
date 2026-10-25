"""Test setup: backend/ on sys.path, a throwaway SQLite DB per test, and a
vitaldb stub (the real package downloads open VitalDB case data; tests must
stay offline). No real patient data is used anywhere in these tests.
"""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if "vitaldb" not in sys.modules:
    try:  # pragma: no cover
        import vitaldb  # noqa: F401
    except Exception:
        stub = types.ModuleType("vitaldb")

        def _offline(*a, **k):
            raise RuntimeError("vitaldb is stubbed in tests (no network)")

        stub.load_clinical_data = _offline
        stub.VitalFile = _offline
        stub.find_cases = _offline
        stub.load_case = _offline
        sys.modules["vitaldb"] = stub


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    from app import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(db, "_conn", None)
    db.init_db()
    yield db
    if db._conn is not None:
        db._conn.close()
