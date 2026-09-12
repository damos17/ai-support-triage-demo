import asyncio

from app.evaluation import run_evaluation
from app.llm import MockLLMProvider


def test_mock_provider_passes_public_evaluation_dataset():
    report = asyncio.run(run_evaluation(MockLLMProvider()))
    assert report["dataset_size"] == 8
    assert report["passed"] == 8
    assert report["pass_rate_pct"] == 100.0
    assert report["issue_accuracy_pct"] == 100.0
    assert report["category_accuracy_pct"] == 100.0
    assert report["severity_accuracy_pct"] == 100.0
