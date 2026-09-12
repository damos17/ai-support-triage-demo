import re
from collections import defaultdict
from .models import Category, Severity, TriageResult, Case, TicketDraft, Incident


KB = {
    Category.authentication: "Check identity-provider status, token expiry, and account access configuration.",
    Category.data_ingestion: "Check ingestion health, recent processing timestamps, and retry failed imports.",
    Category.api: "Check request limits, credentials, response codes, and recent API changes.",
    Category.integration: "Verify integration credentials, permissions, and the latest successful synchronization.",
    Category.configuration: "Review the relevant workspace configuration and compare it with the documented defaults.",
}


class MockLLMProvider:
    """Deterministic, zero-cost provider used by default for the public demo."""

    def triage(self, text: str) -> TriageResult:
        t = text.lower()
        if any(x in t for x in ["thank you", "thanks", "good morning", "works now", "resolved"]):
            return TriageResult(is_issue=False, category=Category.noise, severity=Severity.low,
                                confidence=.97, summary="No active technical issue",
                                decision_reason="The message is conversational or reports that the issue is resolved.")

        rules = [
            (Category.authentication, ["login", "log in", "sign in", "token", "password"]),
            (Category.data_ingestion, ["import", "sync", "data", "ingestion", "update"]),
            (Category.api, ["api", "429", "rate limit", "endpoint"]),
            (Category.integration, ["integration", "connector", "connected"]),
            (Category.performance, ["slow", "latency", "timeout"]),
            (Category.configuration, ["setting", "configuration", "notification"]),
            (Category.billing, ["invoice", "billing", "payment"]),
        ]
        category = Category.unknown
        for candidate, words in rules:
            if any(word in t for word in words):
                category = candidate
                break

        critical = any(x in t for x in ["all users", "none of our users", "complete outage", "entire company"])
        high = critical or any(x in t for x in ["6 hours", "stopped", "failing", "failed", "timeout"])
        severity = Severity.critical if critical else Severity.high if high else Severity.medium
        summary = re.sub(r"\s+", " ", text).strip()[:100]
        return TriageResult(is_issue=True, category=category, severity=severity, confidence=.91,
                            summary=summary,
                            decision_reason="The message describes an active service or configuration problem.")


class SupportWorkflow:
    def __init__(self):
        self.llm = MockLLMProvider()
        self.cases: list[Case] = []
        self.tickets: dict[str, TicketDraft] = {}
        self.incidents: list[Incident] = []

    def process(self, customer_id: str, text: str) -> dict:
        triage = self.llm.triage(text)
        if not triage.is_issue:
            return {"triage": triage.model_dump(mode="json"), "case": None, "ticket": None, "incident": None}

        case_id = f"CASE-{len(self.cases)+1:04d}"
        kb = KB.get(triage.category)
        escalate = triage.severity in {Severity.high, Severity.critical} or kb is None
        case = Case(case_id=case_id, customer_id=customer_id, title=triage.summary,
                    description=text, category=triage.category, severity=triage.severity,
                    escalation_required=escalate, knowledge_match=kb)
        self.cases.append(case)

        ticket = None
        if escalate:
            ticket = TicketDraft(case_id=case_id, title=triage.summary, description=text,
                                 severity=triage.severity, recommended_team=self._team(triage.category))
            self.tickets[case_id] = ticket

        incident = self._detect_incident(case)
        return {"triage": triage.model_dump(mode="json"), "case": case.model_dump(mode="json"),
                "ticket": ticket.model_dump(mode="json") if ticket else None,
                "incident": incident.model_dump(mode="json") if incident else None}

    def approve(self, case_id: str) -> TicketDraft:
        ticket = self.tickets[case_id]
        ticket.status = "created"
        ticket.external_id = f"MOCK-{100 + len([t for t in self.tickets.values() if t.status == 'created'])}"
        return ticket

    def _detect_incident(self, case: Case) -> Incident | None:
        related = [c for c in self.cases if c.category == case.category]
        customers = {c.customer_id for c in related}
        if len(customers) < 3:
            return None
        existing = next((i for i in self.incidents if i.suspected_area == case.category.value), None)
        if existing:
            existing.case_ids = [c.case_id for c in related]
            existing.affected_customers = len(customers)
            return existing
        incident = Incident(incident_id=f"INC-{len(self.incidents)+1:03d}",
                            title=f"Potential {case.category.value.replace('_', ' ')} incident",
                            case_ids=[c.case_id for c in related], affected_customers=len(customers),
                            suspected_area=case.category.value)
        self.incidents.append(incident)
        return incident

    @staticmethod
    def _team(category: Category) -> str:
        return {
            Category.authentication: "Identity",
            Category.data_ingestion: "Data Platform",
            Category.api: "API Platform",
            Category.performance: "Platform Reliability",
            Category.integration: "Integrations",
        }.get(category, "Support Engineering")
