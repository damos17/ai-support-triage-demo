import asyncio

from app.db import SQLiteStore
from app.llm import MockLLMProvider
from app.workflow import SupportWorkflow


def make_workflow(tmp_path):
    store = SQLiteStore(str(tmp_path / "test.db"))
    return SupportWorkflow(store=store, provider=MockLLMProvider())


def test_noise_does_not_create_case(tmp_path):
    w = make_workflow(tmp_path)
    result = asyncio.run(w.process("customer-a", "Thanks, works now"))
    assert result["case"] is None
    assert len(w.cases) == 0
    assert result["telemetry"]["provider"] == "mock"


def test_high_severity_issue_creates_ticket_draft(tmp_path):
    w = make_workflow(tmp_path)
    result = asyncio.run(w.process("customer-a", "Our data imports are failing with timeout errors"))
    assert result["case"]["escalation_required"] is True
    assert result["ticket"]["status"] == "draft"


def test_three_customers_trigger_potential_incident(tmp_path):
    w = make_workflow(tmp_path)
    messages = [
        ("customer-a", "Our data imports stopped and are failing with timeout errors."),
        ("customer-b", "Data imports stopped and are failing with timeout errors for us too."),
        ("customer-c", "Our data imports stopped and are failing with repeated timeout errors."),
    ]
    for customer, message in messages[:2]:
        result = asyncio.run(w.process(customer, message))
        assert result["incident"] is None
    result = asyncio.run(w.process(*messages[2]))
    assert result["incident"] is not None
    assert result["incident"]["affected_customers"] == 3


def test_ticket_requires_explicit_approval(tmp_path):
    w = make_workflow(tmp_path)
    result = asyncio.run(w.process("customer-a", "Data imports have stopped for 6 hours"))
    case_id = result["case"]["case_id"]
    assert w.tickets[case_id].status == "draft"
    assert w.tickets[case_id].external_id is None
    ticket = w.approve(case_id)
    assert ticket.status == "created"
    assert ticket.external_id.startswith("MOCK-")
    assert any(event.event_type == "ticket_approved" for event in w.audit_events)


def test_audit_trail_and_case_detail(tmp_path):
    w = make_workflow(tmp_path)
    result = asyncio.run(w.process("customer-a", "Our data imports are failing with timeout errors"))
    case_id = result["case"]["case_id"]
    detail = w.case_detail(case_id)
    assert detail is not None
    assert detail["case"]["case_id"] == case_id
    assert detail["ticket"]["status"] == "draft"
    event_types = [event["event_type"] for event in detail["audit"]]
    assert "case_created" in event_types
    assert "ticket_drafted" in event_types


def test_telemetry_aggregates_triage_calls(tmp_path):
    w = make_workflow(tmp_path)
    asyncio.run(w.process("customer-a", "Thanks, works now"))
    asyncio.run(w.process("customer-b", "Our data imports are failing with timeout errors"))
    telemetry = w.telemetry()
    assert telemetry["llm_calls"] == 2
    assert telemetry["latest_provider"] == "mock"
    assert telemetry["estimated_cost_usd"] == 0.0


def test_state_and_audit_survive_restart(tmp_path):
    db_path = str(tmp_path / "persist.db")
    w1 = SupportWorkflow(store=SQLiteStore(db_path), provider=MockLLMProvider())
    asyncio.run(w1.process("customer-a", "Our data imports are failing with timeout errors"))

    w2 = SupportWorkflow(store=SQLiteStore(db_path), provider=MockLLMProvider())
    assert len(w2.cases) == 1
    assert w2.cases[0].customer_id == "customer-a"
    assert len(w2.audit_events) >= 4
    assert w2.telemetry()["llm_calls"] == 1
