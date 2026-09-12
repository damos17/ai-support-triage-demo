from .db import SQLiteStore
from .incidents import IncidentDetector
from .knowledge import retrieve
from .llm import LLMProvider, build_provider
from .models import Case, Severity, TicketDraft
from .ticketing import MockTicketing


class SupportWorkflow:
    def __init__(self, store: SQLiteStore | None = None, provider: LLMProvider | None = None):
        self.store = store or SQLiteStore()
        self.llm = provider or build_provider()
        self.detector = IncidentDetector()
        self.cases = self.store.load_cases()
        self.tickets = self.store.load_tickets()
        self.incidents = self.store.load_incidents()

    async def process(self, customer_id: str, text: str) -> dict:
        triage = await self.llm.triage(text)
        if not triage.is_issue:
            return {
                "triage": triage.model_dump(mode="json"),
                "case": None,
                "ticket": None,
                "incident": None,
            }

        case_id = self._next_case_id()
        kb = retrieve(triage.category)
        escalate = triage.severity in {Severity.high, Severity.critical} or kb is None
        case = Case(
            case_id=case_id,
            customer_id=customer_id,
            title=triage.summary,
            description=text,
            category=triage.category,
            severity=triage.severity,
            escalation_required=escalate,
            knowledge_match=kb,
        )
        self.cases.append(case)
        self.store.save_case(case)

        ticket: TicketDraft | None = None
        if escalate:
            ticket = MockTicketing.build_draft(case_id, text, triage)
            self.tickets[case_id] = ticket
            self.store.save_ticket(ticket)

        incident = self.detector.detect(case, self.cases, self.incidents)
        if incident:
            if all(existing.incident_id != incident.incident_id for existing in self.incidents):
                self.incidents.append(incident)
            self.store.save_incident(incident)

        return {
            "triage": triage.model_dump(mode="json"),
            "case": case.model_dump(mode="json"),
            "ticket": ticket.model_dump(mode="json") if ticket else None,
            "incident": incident.model_dump(mode="json") if incident else None,
        }

    def approve(self, case_id: str) -> TicketDraft:
        ticket = self.tickets[case_id]
        created_count = sum(1 for t in self.tickets.values() if t.status == "created") + 1
        ticket = MockTicketing.approve(ticket, created_count)
        self.tickets[case_id] = ticket
        self.store.save_ticket(ticket)
        return ticket

    def reset(self) -> None:
        self.store.clear()
        self.cases = []
        self.tickets = {}
        self.incidents = []

    def stats(self) -> dict:
        return {
            "open_cases": sum(1 for c in self.cases if c.status == "open"),
            "incidents": len(self.incidents),
            "ticket_drafts": sum(1 for t in self.tickets.values() if t.status == "draft"),
            "tickets_created": sum(1 for t in self.tickets.values() if t.status == "created"),
        }

    def _next_case_id(self) -> str:
        if not self.cases:
            return "CASE-0001"
        current = max(int(case.case_id.split("-")[-1]) for case in self.cases)
        return f"CASE-{current + 1:04d}"
