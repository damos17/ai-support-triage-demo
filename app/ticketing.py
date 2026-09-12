from .models import Category, TicketDraft, TriageResult


class MockTicketing:
    """Ticket drafts are safe to create. External IDs require explicit approval."""

    @staticmethod
    def build_draft(case_id: str, text: str, triage: TriageResult) -> TicketDraft:
        return TicketDraft(
            case_id=case_id,
            title=triage.summary,
            description=text,
            severity=triage.severity,
            recommended_team=MockTicketing._team(triage.category),
        )

    @staticmethod
    def approve(ticket: TicketDraft, ordinal: int) -> TicketDraft:
        if ticket.status != "draft":
            return ticket
        ticket.status = "created"
        ticket.external_id = f"MOCK-{100 + ordinal}"
        return ticket

    @staticmethod
    def _team(category: Category) -> str:
        return {
            Category.authentication: "Identity",
            Category.data_ingestion: "Data Platform",
            Category.api: "API Platform",
            Category.performance: "Platform Reliability",
            Category.integration: "Integrations",
        }.get(category, "Support Engineering")
