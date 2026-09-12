from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
import re
import time

import httpx

from .models import Category, Severity, TriageResult


class LLMProvider(ABC):
    def __init__(self) -> None:
        self.last_telemetry: dict = {}

    @abstractmethod
    async def triage(self, text: str) -> TriageResult:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Deterministic provider used for the zero-cost public demo."""

    def __init__(self) -> None:
        super().__init__()

    async def triage(self, text: str) -> TriageResult:
        started = time.perf_counter()
        t = text.lower()
        if any(x in t for x in [
            "thank you", "thanks", "good morning", "works now", "resolved",
            "спасибо", "доброе утро", "всё работает", "все работает", "решено",
        ]):
            result = TriageResult(
                is_issue=False,
                category=Category.noise,
                severity=Severity.low,
                confidence=0.97,
                summary="No active technical issue",
                decision_reason="The message is conversational or reports that the issue is resolved.",
            )
            self._set_telemetry(started)
            return result

        rules = [
            (Category.authentication, ["login", "log in", "sign in", "token", "password", "войти", "авторизац", "токен", "парол"]),
            (Category.data_ingestion, ["import", "sync", "data", "ingestion", "update", "импорт", "синхрон", "данн", "загрузк"]),
            (Category.api, ["api", "429", "rate limit", "endpoint", "апи", "эндпоинт", "лимит запрос"]),
            (Category.integration, ["integration", "connector", "connected", "интеграц", "коннектор", "подключен"]),
            (Category.performance, ["slow", "latency", "timeout", "медлен", "задержк", "тайм-аут", "таймаут"]),
            (Category.configuration, ["setting", "configuration", "notification", "настрой", "конфигурац", "уведомлен"]),
            (Category.billing, ["invoice", "billing", "payment", "счёт", "счет", "оплат", "платёж", "платеж"]),
        ]
        category = Category.unknown
        for candidate, words in rules:
            if any(word in t for word in words):
                category = candidate
                break

        critical = any(x in t for x in [
            "all users", "none of our users", "complete outage", "entire company",
            "ни один пользователь", "все пользователи", "полный сбой", "вся компания",
        ])
        high = critical or any(x in t for x in [
            "6 hours", "stopped", "failing", "failed", "timeout",
            "6 часов", "останов", "не работает", "ошибк", "тайм-аут", "таймаут",
        ])
        severity = Severity.critical if critical else Severity.high if high else Severity.medium
        summary = re.sub(r"\s+", " ", text).strip()[:100]
        result = TriageResult(
            is_issue=True,
            category=category,
            severity=severity,
            confidence=0.91,
            summary=summary,
            decision_reason="The message describes an active service or configuration problem.",
        )
        self._set_telemetry(started)
        return result

    def _set_telemetry(self, started: float) -> None:
        self.last_telemetry = {
            "provider": "mock",
            "model": "deterministic-rules",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
        }


@dataclass
class OpenAICompatibleProvider(LLMProvider):
    base_url: str
    api_key: str
    model: str

    def __post_init__(self) -> None:
        LLMProvider.__init__(self)

    async def triage(self, text: str) -> TriageResult:
        started = time.perf_counter()
        prompt = (
            "Classify this synthetic support message. Return ONLY compact JSON with keys: "
            "is_issue, category, severity, confidence, summary, decision_reason. "
            "Allowed categories: noise,billing,authentication,data_ingestion,api,performance,integration,configuration,unknown. "
            "Allowed severities: low,medium,high,critical. The input can be English or Russian.\n\nMessage: " + text
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

        usage = data.get("usage") or {}
        self.last_telemetry = {
            "provider": "openai_compatible",
            "model": data.get("model") or self.model,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "estimated_cost_usd": None,
        }
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
