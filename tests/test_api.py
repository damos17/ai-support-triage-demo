from fastapi.testclient import TestClient

import app.main as main_module
from app.db import SQLiteStore
from app.llm import MockLLMProvider
from app.workflow import SupportWorkflow


def build_client(tmp_path) -> TestClient:
    main_module.workflow = SupportWorkflow(
        store=SQLiteStore(str(tmp_path / "api.db")),
        provider=MockLLMProvider(),
    )
    return TestClient(main_module.app)


def test_health_dashboard_favicon_and_security_headers(tmp_path):
    client = build_client(tmp_path)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "0.6.0"

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "AI Support Triage Agent" in dashboard.text
    assert "v0.6" in dashboard.text
    assert dashboard.headers["x-content-type-options"] == "nosniff"
    assert dashboard.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in dashboard.headers["content-security-policy"]

    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 200
    assert favicon.headers["content-type"].startswith("image/svg+xml")


def test_message_case_detail_and_approval_flow(tmp_path):
    client = build_client(tmp_path)

    response = client.post(
        "/api/messages",
        json={
            "customer_id": "atlas-studio",
            "text": "None of our users can log in since this morning.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["triage"]["is_issue"] is True
    assert payload["case"] is not None
    assert payload["ticket"]["status"] == "draft"

    case_id = payload["case"]["case_id"]
    detail = client.get(f"/api/cases/{case_id}")
    assert detail.status_code == 200
    assert detail.json()["case"]["case_id"] == case_id

    approved = client.post(f"/api/tickets/{case_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "created"
    assert approved.json()["external_id"].startswith("MOCK-")


def test_unknown_case_and_ticket_return_404(tmp_path):
    client = build_client(tmp_path)

    assert client.get("/api/cases/CASE-9999").status_code == 404
    assert client.post("/api/tickets/CASE-9999/approve").status_code == 404


def test_evaluation_endpoint_shape(tmp_path):
    client = build_client(tmp_path)

    response = client.get("/api/evaluation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_size"] >= 16
    assert "pass_rate_pct" in payload
    assert "by_language" in payload
    assert "by_category" in payload


def test_dynamic_message_content_is_html_escaped(tmp_path):
    client = build_client(tmp_path)

    response = client.post(
        "/api/messages",
        json={
            "customer_id": "<img src=x onerror=alert(1)>",
            "text": "<img src=x onerror=alert(1)> timeout error",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert "<img" not in payload["case"]["description"]
    assert "&lt;img" in payload["case"]["description"]
    assert "<img" not in payload["case"]["customer_id"]
    assert "&lt;img" in payload["case"]["customer_id"]
