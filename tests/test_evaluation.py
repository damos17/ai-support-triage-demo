import asyncio

from app.evaluation import run_evaluation
from app.llm import MockLLMProvider


def test_mock_provider_passes_public_evaluation_dataset():
    report = asyncio.run(run_evaluation(MockLLMProvider()))
    assert report["dataset_size"] == 16
    assert report["passed"] == 16
    assert report["failed"] == 0
    assert report["pass_rate_pct"] == 100.0
    assert report["grade"] == "excellent"
    assert report["issue_accuracy_pct"] == 100.0
    assert report["category_accuracy_pct"] == 100.0
    assert report["severity_accuracy_pct"] == 100.0
    assert report["by_language"]["en"]["dataset_size"] == 8
    assert report["by_language"]["ru"]["dataset_size"] == 8
    assert report["by_language"]["en"]["pass_rate_pct"] == 100.0
    assert report["by_language"]["ru"]["pass_rate_pct"] == 100.0
    assert report["category_confusion"] == []
    assert all(row["pass"] for row in report["results"])
