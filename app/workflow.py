from threading import Lock
from uuid import uuid4

from .db import SQLiteStore
from .incidents import IncidentDetector
from .knowledge import retrieve
from .llm import LLMProvider, build_provider
from .models import AuditEvent, Case, Severity, TicketDraft
from .ticketing import MockTicketing


class SupportWorkflow:
    def __init__(self, store: SQLiteStore | None = None, provider: LLMProvider | None = None):
        self.store = store or SQLiteStore()
        self.llm = provider or build_provider()
        self.detector = IncidentDetector()
        self.cases = self.store.load_cases()
        self.tickets = self.store.load_tickets()
        self.incidents = self.store.load_incidents()
        self.audit_events = self.store.load_audit_events()
        self._case_id_lock = Lock()

    async def process(self, customer_id: str, text: str) -> dict:
        self._audit("message_received", "Incoming support message received", customer_id=customer_id)
        triage = await self.llm.triage(text)
        telemetry = dict(getattr(self.llm, "last_telemetry", {}) or {})
        self._audit(
            "triage_completed",
            "Message triage completed",
            customer_id=customer_id,
            metadata={
                "is_issue": triage.is_issue,
                "category": triage.category.value,
                "severity": triage.severity.value,
                "confidence": triage.confidence,
                "telemetry": telemetry,
            },
        )

        if not triage.is_issue:
            self._audit("message_closed", "No active technical issue detected", customer_id=customer_id)
            return {
                "triage": triage.model_dump(mode="json"),
                "case": None,
                "ticket": None,
                "incident": None,
                "telemetry": telemetry,
            }

        kb = retrieve(triage.category)
        escalate = triage.severity in {Severity.high, Severity.critical} or kb is None

        # Keep sequential demo case IDs unique for concurrent requests inside one
        # application process. A production multi-process deployment should move
        # identity allocation/uniqueness into the database transaction layer.
        with self._case_id_lock:
            case_id = self._next_case_id()
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

        self._audit(
            "case_created",
            f"Case {case_id} created",
            case_id=case_id,
            customer_id=customer_id,
            metadata={"category": triage.category.value, "severity": triage.severity.value},
        )

        if kb:
            self._audit("knowledge_retrieved", "Knowledge guidance retrieved", case_id=case_id, customer_id=customer_id)
        else:
            self._audit("knowledge_miss", "No matching knowledge guidance found", case_id=case_id, customer_id=customer_id)

        ticket: TicketDraft | None = None
        if escalate:
            ticket = MockTicketing.build_draft(case_id, text, triage)
            self.tickets[case_id] = ticket
            self.store.save_ticket(ticket)
            self._audit(
                "ticket_drafted",
                "Ticket draft prepared; explicit approval required",
                case_id=case_id,
                customer_id=customer_id,
                metadata={"recommended_team": ticket.recommended_team},
            )

        incident = self.detector.detect(case, self.cases, self.incidents)
        if incident:
            if all(existing.incident_id != incident.incident_id for existing in self.incidents):
                self.incidents.append(incident)
                self._audit(
                    "incident_detected",
                    f"Potential incident {incident.incident_id} detected",
                    case_id=case_id,
                    customer_id=customer_id,
                    metadata={
                        "affected_customers": incident.affected_customers,
                        "case_ids": incident.case_ids,
                        "suspected_area": incident.suspected_area,
                    },
                )
            self.store.save_incident(incident)

        return {
            "triage": triage.model_dump(mode="json"),
            "case": case.model_dump(mode="json"),
            "ticket": ticket.model_dump(mode="json") if ticket else None,
            "incident": incident.model_dump(mode="json") if incident else None,
            "telemetry": telemetry,
        }

    def approve(self, case_id: str) -> TicketDraft:
        ticket = self.tickets[case_id]
        created_count = sum(1 for t in self.tickets.values() if t.status == "created") + 1
        ticket = MockTicketing.approve(ticket, created_count)
        self.tickets[case_id] = ticket
        self.store.save_ticket(ticket)
        case = self.get_case(case_id)
        self._audit(
            "ticket_approved",
            f"Ticket for {case_id} approved by human action",
            case_id=case_id,
            customer_id=case.customer_id if case else None,
            metadata={"external_id": ticket.external_id},
        )
        return ticket

    def reset(self) -> None:
        self.store.clear()
        self.cases = []
        self.tickets = {}
        self.incidents = []
        self.audit_events = []

    def stats(self) -> dict:
        return {
            "open_cases": sum(1 for c in self.cases if c.status == "open"),
            "incidents": len(self.incidents),
            "ticket_drafts": sum(1 for t in self.tickets.values() if t.status == "draft"),
            "tickets_created": sum(1 for t in self.tickets.values() if t.status == "created"),
        }

    def telemetry(self) -> dict:
        triage_events = [event for event in self.audit_events if event.event_type == "triage_completed"]
        token_in = 0
        token_out = 0
        total_cost = 0.0
        known_costs = 0
        latest = {}
        for event in triage_events:
            data = event.metadata.get("telemetry") or {}
            latest = data or latest
            token_in += data.get("input_tokens") or 0
            token_out += data.get("output_tokens") or 0
            if data.get("estimated_cost_usd") is not None:
                total_cost += float(data["estimated_cost_usd"])
                known_costs += 1
        return {
            "llm_calls": len(triage_events),
            "input_tokens": token_in,
            "output_tokens": token_out,
            "estimated_cost_usd": round(total_cost, 6) if known_costs else None,
            "latest_provider": latest.get("provider"),
            "latest_model": latest.get("model"),
            "latest_latency_ms": latest.get("latency_ms"),
        }

    def get_case(self, case_id: str) -> Case | None:
        return next((case for case in self.cases if case.case_id == case_id), None)

    def case_detail(self, case_id: str) -> dict | None:
        case = self.get_case(case_id)
        if not case:
            return None
        ticket = self.tickets.get(case_id)
        incidents = [incident for incident in self.incidents if case_id in incident.case_ids]
        audit = [event for event in self.audit_events if event.case_id == case_id]
        return {
            "case": case.model_dump(mode="json"),
            "ticket": ticket.model_dump(mode="json") if ticket else None,
            "incidents": [incident.model_dump(mode="json") for incident in incidents],
            "audit": [event.model_dump(mode="json") for event in audit],
        }

    def audit(self, limit: int = 50) -> list[dict]:
        events = self.audit_events[-max(1, min(limit, 200)):]
        return [event.model_dump(mode="json") for event in reversed(events)]

    def _audit(
        self,
        event_type: str,
        message: str,
        *,
        case_id: str | None = None,
        customer_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            message=message,
            case_id=case_id,
            customer_id=customer_id,
            metadata=metadata or {},
        )
        self.audit_events.append(event)
        self.store.save_audit_event(event)

    def _next_case_id(self) -> str:
        if not self.cases:
            return "CASE-0001"
        current = max(int(case.case_id.split("-")[-1]) for case in self.cases)
        return f"CASE-{current + 1:04d}"
