"""Shared fixtures: stub `vitaldb` (no network) and give each test a fresh SQLite file."""
from __future__ import annotations

import sys
import types

import pytest

if "vitaldb" not in sys.modules:
    sys.modules["vitaldb"] = types.ModuleType("vitaldb")  # real lib is never needed in tests

from app import db, main  # noqa: E402


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Point app.db at a throw-away file and reset its cached connection."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(db, "_conn", None)
    db.init_db()
    yield db
    if db._conn is not None:
        db._conn.close()
        db._conn = None


@pytest.fixture()
def client(fresh_db, monkeypatch):
    """TestClient with one fake bed; startup hooks (which load VitalDB) are not run."""
    from fastapi.testclient import TestClient

    identity = {"bed_id": "Bed-1", "abha_id": "11-2222-3333-4444", "name": "Test Patient"}
    monkeypatch.setattr(main, "bed_identities", {"Bed-1": identity})
    monkeypatch.setattr(main, "beds", {"Bed-1": object()})
    monkeypatch.setattr(main, "sim_t", 100)
    return TestClient(main.app)
