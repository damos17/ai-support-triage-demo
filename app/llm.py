from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
import re

import httpx

from .models import Category, Severity, TriageResult


class LLMProvider(ABC):
    @abstractmethod
    async def triage(self, text: str) -> TriageResult:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Deterministic provider used for the zero-cost public demo."""

    async def triage(self, text: str) -> TriageResult:
        t = text.lower()
        if any(x in t for x in ["thank you", "thanks", "good morning", "works now", "resolved"]):
            return TriageResult(
                is_issue=False,
                category=Category.noise,
                severity=Severity.low,
                confidence=0.97,
                summary="No active technical issue",
                decision_reason="The message is conversational or reports that the issue is resolved.",
            )

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
        return TriageResult(
            is_issue=True,
            category=category,
            severity=severity,
            confidence=0.91,
            summary=summary,
            decision_reason="The message describes an active service or configuration problem.",
        )


@dataclass
class OpenAICompatibleProvider(LLMProvider):
    base_url: str
    api_key: str
    model: str

    async def triage(self, text: str) -> TriageResult:
        prompt = (
            "Classify this synthetic support message. Return ONLY compact JSON with keys: "
            "is_issue, category, severity, confidence, summary, decision_reason. "
            "Allowed categories: noise,billing,authentication,data_ingestion,api,performance,integration,configuration,unknown. "
            "Allowed severities: low,medium,high,critical.\n\nMessage: " + text
        )
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        return TriageResult.model_validate_json(content)


def build_provider() -> LLMProvider:
    mode = os.getenv("LLM_MODE", "mock").lower()
    if mode == "mock":
        return MockLLMProvider()
    if mode == "openai_compatible":
        base_url = os.getenv("LLM_BASE_URL", "").strip()
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()
        if not all([base_url, api_key, model]):
            raise RuntimeError("LLM_BASE_URL, LLM_API_KEY and LLM_MODEL are required in openai_compatible mode")
        return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
    raise RuntimeError(f"Unsupported LLM_MODE: {mode}")
