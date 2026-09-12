from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .llm import LLMProvider


def _pct(value: int, total: int) -> float:
    return round(value / total * 100, 1) if total else 0.0


def _grade(pass_rate: float) -> str:
    if pass_rate >= 95:
        return "excellent"
    if pass_rate >= 85:
        return "good"
    if pass_rate >= 70:
        return "needs_review"
    return "poor"


async def run_evaluation(provider: LLMProvider, path: str = "data/evaluation.json") -> dict:
    """Run the public synthetic triage benchmark against a provider.

    The report intentionally separates issue detection, category classification,
    and severity classification instead of hiding them behind one aggregate
    score. This keeps regressions visible and the benchmark easy to inspect.
    """

    dataset = json.loads(Path(path).read_text(encoding="utf-8"))
    rows: list[dict] = []
    issue_ok = 0
    category_ok = 0
    severity_ok = 0
    by_language: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "passed": 0, "issue_ok": 0, "category_ok": 0, "severity_ok": 0}
    )
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    category_confusion: Counter[tuple[str, str]] = Counter()

    for item in dataset:
        result = await provider.triage(item["message"])
        language = item.get("language", "unknown")
        issue_match = result.is_issue == item["expected_issue"]
        category_match = result.category.value == item["expected_category"]
        severity_match = result.severity.value == item["expected_severity"]
        row_pass = issue_match and category_match and severity_match

        issue_ok += int(issue_match)
        category_ok += int(category_match)
        severity_ok += int(severity_match)

        lang = by_language[language]
        lang["total"] += 1
        lang["passed"] += int(row_pass)
        lang["issue_ok"] += int(issue_match)
        lang["category_ok"] += int(category_match)
        lang["severity_ok"] += int(severity_match)

        expected_category = item["expected_category"]
        actual_category = result.category.value
        by_category[expected_category]["total"] += 1
        by_category[expected_category]["correct"] += int(category_match)
        category_confusion[(expected_category, actual_category)] += 1

        rows.append(
            {
                "id": item["id"],
                "language": language,
                "message": item["message"],
                "expected": {
                    "is_issue": item["expected_issue"],
                    "category": expected_category,
                    "severity": item["expected_severity"],
                },
                "actual": {
                    "is_issue": result.is_issue,
                    "category": actual_category,
                    "severity": result.severity.value,
                    "confidence": result.confidence,
                },
                "matches": {
                    "issue": issue_match,
                    "category": category_match,
                    "severity": severity_match,
                },
                "pass": row_pass,
            }
        )

    total = len(dataset)
    passed = sum(1 for row in rows if row["pass"])
    pass_rate = _pct(passed, total)

    language_metrics = {}
    for language, values in sorted(by_language.items()):
        language_metrics[language] = {
            "dataset_size": values["total"],
            "passed": values["passed"],
            "pass_rate_pct": _pct(values["passed"], values["total"]),
            "issue_accuracy_pct": _pct(values["issue_ok"], values["total"]),
            "category_accuracy_pct": _pct(values["category_ok"], values["total"]),
            "severity_accuracy_pct": _pct(values["severity_ok"], values["total"]),
        }

    category_metrics = {
        category: {
            "dataset_size": values["total"],
            "correct": values["correct"],
            "accuracy_pct": _pct(values["correct"], values["total"]),
        }
        for category, values in sorted(by_category.items())
    }

    confusion = [
        {"expected": expected, "actual": actual, "count": count}
        for (expected, actual), count in sorted(category_confusion.items())
        if expected != actual
    ]

    return {
        "dataset_size": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": pass_rate,
        "grade": _grade(pass_rate),
        "issue_accuracy_pct": _pct(issue_ok, total),
        "category_accuracy_pct": _pct(category_ok, total),
        "severity_accuracy_pct": _pct(severity_ok, total),
        "by_language": language_metrics,
        "by_category": category_metrics,
        "category_confusion": confusion,
        "provider": getattr(provider, "last_telemetry", {}).get("provider"),
        "model": getattr(provider, "last_telemetry", {}).get("model"),
        "results": rows,
    }
