from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Category(str, Enum):
    noise = "noise"
    billing = "billing"
    authentication = "authentication"
    data_ingestion = "data_ingestion"
    api = "api"
    performance = "performance"
    integration = "integration"
    configuration = "configuration"
    unknown = "unknown"


class MessageIn(BaseModel):
    customer_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)


class TriageResult(BaseModel):
    is_issue: bool
    category: Category
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    summary: str
    decision_reason: str


class Case(BaseModel):
    case_id: str
    customer_id: str
    title: str
    description: str
    category: Category
    severity: Severity
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    escalation_required: bool = False
    knowledge_match: str | None = None


class TicketDraft(BaseModel):
    case_id: str
    title: str
    description: str
    severity: Severity
    recommended_team: str
    status: str = "draft"
    external_id: str | None = None


class Incident(BaseModel):
    incident_id: str
    title: str
    case_ids: list[str]
    affected_customers: int
    suspected_area: str
    status: str = "potential"
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEvent(BaseModel):
    event_id: str
    event_type: str
    message: str
    case_id: str | None = None
    customer_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
