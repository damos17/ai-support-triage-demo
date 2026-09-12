from collections import Counter

from .models import Case, Incident


class IncidentDetector:
    """Similarity-light demo correlator.

    v0.2 deliberately uses transparent category + token overlap logic so the
    public demo remains reproducible without model downloads or API calls.
    """

    def __init__(self, min_customers: int = 3, min_overlap: float = 0.35):
        self.min_customers = min_customers
        self.min_overlap = min_overlap

    def detect(self, case: Case, cases: list[Case], incidents: list[Incident]) -> Incident | None:
        candidates = [c for c in cases if c.category == case.category]
        related = [c for c in candidates if self._similar(case.description, c.description)]
        customers = {c.customer_id for c in related}
        if len(customers) < self.min_customers:
            return None

        existing = next((i for i in incidents if i.suspected_area == case.category.value), None)
        if existing:
            existing.case_ids = [c.case_id for c in related]
            existing.affected_customers = len(customers)
            return existing

        return Incident(
            incident_id=f"INC-{len(incidents)+1:03d}",
            title=f"Potential {case.category.value.replace('_', ' ')} incident",
            case_ids=[c.case_id for c in related],
            affected_customers=len(customers),
            suspected_area=case.category.value,
        )

    def _similar(self, a: str, b: str) -> bool:
        left = self._tokens(a)
        right = self._tokens(b)
        if not left or not right:
            return False
        overlap = len(left & right) / max(1, len(left | right))
        return overlap >= self.min_overlap

    @staticmethod
    def _tokens(text: str) -> set[str]:
        stop = {"the", "a", "an", "our", "is", "are", "has", "have", "with", "since", "this", "and", "for"}
        return {token.strip(".,:;!?()[]{}\"'").lower() for token in text.split() if len(token) > 2} - stop
