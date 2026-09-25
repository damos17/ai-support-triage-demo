import asyncio
import importlib

from fastapi.testclient import TestClient


def load_app(monkeypatch, **env):
    for key in ("DEMO_THEME", "FRAME_ANCESTORS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.main as main
    return importlib.reload(main)


def test_default_forbids_framing_and_has_no_theme(monkeypatch):
    main = load_app(monkeypatch)
    response = TestClient(main.app).get("/")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "/theme/" not in response.text


def test_frame_ancestors_allows_listed_origins(monkeypatch):
    main = load_app(monkeypatch, FRAME_ANCESTORS="https://example.com")
    response = TestClient(main.app).get("/")
    assert "X-Frame-Options" not in response.headers
    assert "frame-ancestors https://example.com;" in response.headers["Content-Security-Policy"]


def test_damos_theme_is_injected_and_served(monkeypatch):
    main = load_app(monkeypatch, DEMO_THEME="damos")
    client = TestClient(main.app)
    html = client.get("/").text
    assert 'class="theme-damos"' in html
    assert '/theme/damos.css' in html
    assert client.get("/theme/damos.css").status_code == 200


def test_unknown_theme_is_ignored(monkeypatch):
    main = load_app(monkeypatch, DEMO_THEME="nope")
    assert "/theme/" not in TestClient(main.app).get("/").text


def test_max_cases_resets_shared_state(monkeypatch):
    monkeypatch.setenv("DEMO_MAX_CASES", "2")
    from app.workflow import SupportWorkflow

    wf = SupportWorkflow()
    wf.reset()
    text = "Our data imports stopped and are failing with timeout errors."
    for customer in ("a", "b", "c"):
        asyncio.run(wf.process(customer, text))
    assert len(wf.cases) <= 2
    wf.reset()
