from app.services import SupportWorkflow


def test_noise_does_not_create_case():
    w = SupportWorkflow()
    result = w.process("customer-a", "Thanks, works now")
    assert result["case"] is None
    assert len(w.cases) == 0


def test_high_severity_issue_creates_ticket_draft():
    w = SupportWorkflow()
    result = w.process("customer-a", "Our data imports are failing with timeout errors")
    assert result["case"]["escalation_required"] is True
    assert result["ticket"]["status"] == "draft"


def test_three_customers_trigger_potential_incident():
    w = SupportWorkflow()
    for customer in ["customer-a", "customer-b"]:
        result = w.process(customer, "Data imports stopped and are failing")
        assert result["incident"] is None
    result = w.process("customer-c", "Data sync stopped and imports are failing")
    assert result["incident"] is not None
    assert result["incident"]["affected_customers"] == 3


def test_ticket_requires_explicit_approval():
    w = SupportWorkflow()
    result = w.process("customer-a", "Data imports have stopped for 6 hours")
    case_id = result["case"]["case_id"]
    assert w.tickets[case_id].status == "draft"
    ticket = w.approve(case_id)
    assert ticket.status == "created"
    assert ticket.external_id.startswith("MOCK-")
