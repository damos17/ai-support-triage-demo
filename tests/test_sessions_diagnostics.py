import html
import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, sessions: bool):
    monkeypatch.setenv("DEMO_SESSIONS", "1" if sessions else "")
    import app.main as main
    return TestClient(importlib.reload(main).app)


def test_sessions_are_private(monkeypatch):
    client_a = make_client(monkeypatch, sessions=True)
    from app.main import app
    client_b = TestClient(app)
    r = client_a.post("/api/messages", json={"customer_id": "vertex-retail", "text": "Payment failed, invoice charged twice"})
    assert r.status_code == 200 and r.cookies.get("triage_sid")
    assert client_a.get("/api/stats").json()["open_cases"] == 1
    assert client_b.get("/api/stats").json()["open_cases"] == 0
    assert client_b.get("/api/cases").json() == []


def test_incident_inside_one_session(monkeypatch):
    client = make_client(monkeypatch, sessions=True)
    texts = [
        "Our data imports stopped and are failing with timeout errors.",
        "Data imports stopped and are failing with timeout errors for us too.",
        "Our data imports stopped and are failing with repeated timeout errors.",
    ]
    last = None
    for customer, text in zip(["a-co", "b-co", "c-co"], texts):
        last = client.post("/api/messages", json={"customer_id": customer, "text": text}).json()
    assert last["incident"]["affected_customers"] == 3


def test_diagnostics_logs_and_sql(monkeypatch):
    client = make_client(monkeypatch, sessions=True)
    d = client.post("/api/messages", json={"customer_id": "vertex-retail", "text": "Деньги за подписку списались дважды, а счёт так и не пришёл."}).json()
    diag = d["diagnostics"]
    sql = html.unescape(diag["sql"])  # the API escapes all text as HTML
    assert sql.lstrip().upper().startswith("SELECT")
    assert "'vertex-retail'" in sql
    assert diag["rows"] == [["INV-2291", 2, 9800]]
    assert any(line["match"] for line in diag["logs"])
    assert d["ticket"] is not None


def test_noise_has_no_diagnostics(monkeypatch):
    client = make_client(monkeypatch, sessions=True)
    d = client.post("/api/messages", json={"customer_id": "x", "text": "Спасибо, теперь всё работает."}).json()
    assert d["diagnostics"] is None


def test_diagnostics_database_is_read_only():
    from app import diagnostics
    import sqlite3
    import pytest
    from contextlib import closing
    with closing(diagnostics._connect()) as conn, pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM payments")
