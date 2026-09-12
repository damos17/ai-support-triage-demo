from .models import Category


KNOWLEDGE_BASE = {
    Category.authentication: "Check identity-provider status, token expiry, and account access configuration.",
    Category.data_ingestion: "Check ingestion health, recent processing timestamps, and retry failed imports.",
    Category.api: "Check request limits, credentials, response codes, and recent API changes.",
    Category.integration: "Verify integration credentials, permissions, and the latest successful synchronization.",
    Category.configuration: "Review the relevant workspace configuration and compare it with the documented defaults.",
}


def retrieve(category: Category) -> str | None:
    """Return a synthetic knowledge-base recommendation for the demo."""
    return KNOWLEDGE_BASE.get(category)
