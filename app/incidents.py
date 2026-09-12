from .models import Case, Incident
from .similarity import SimilarityEngine, TokenCosineSimilarity


class IncidentDetector:
    """Cross-customer incident correlator with a pluggable similarity boundary."""

    def __init__(
        self,
        min_customers: int = 3,
        min_similarity: float = 0.45,
        similarity: SimilarityEngine | None = None,
    ):
        self.min_customers = min_customers
        self.min_similarity = min_similarity
        self.similarity = similarity or TokenCosineSimilarity()

    def detect(self, case: Case, cases: list[Case], incidents: list[Incident]) -> Incident | None:
        candidates = [c for c in cases if c.category == case.category]
        related = [c for c in candidates if self.similarity.score(case.description, c.description) >= self.min_similarity]
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

    def score(self, left: str, right: str) -> float:
        return self.similarity.score(left, right)
