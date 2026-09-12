from __future__ import annotations

import json
from pathlib import Path

from .llm import LLMProvider


async def run_evaluation(provider: LLMProvider, path: str = "data/evaluation.json") -> dict:
    dataset = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    issue_ok = 0
    category_ok = 0
    severity_ok = 0

    for item in dataset:
        result = await provider.triage(item["message"])
        issue_match = result.is_issue == item["expected_issue"]
        category_match = result.category.value == item["expected_category"]
        severity_match = result.severity.value == item["expected_severity"]
        issue_ok += int(issue_match)
        category_ok += int(category_match)
        severity_ok += int(severity_match)
        rows.append(
            {
                "id": item["id"],
                "message": item["message"],
                "expected": {
                    "is_issue": item["expected_issue"],
                    "category": item["expected_category"],
                    "severity": item["expected_severity"],
                },
                "actual": {
                    "is_issue": result.is_issue,
                    "category": result.category.value,
                    "severity": result.severity.value,
                    "confidence": result.confidence,
                },
                "pass": issue_match and category_match and severity_match,
            }
        )

    total = len(dataset)
    passed = sum(1 for row in rows if row["pass"])
    pct = lambda value: round(value / total * 100, 1) if total else 0.0
    return {
        "dataset_size": total,
        "passed": passed,
        "pass_rate_pct": pct(passed),
        "issue_accuracy_pct": pct(issue_ok),
        "category_accuracy_pct": pct(category_ok),
        "severity_accuracy_pct": pct(severity_ok),
        "provider": getattr(provider, "last_telemetry", {}).get("provider"),
        "model": getattr(provider, "last_telemetry", {}).get("model"),
        "results": rows,
    }
