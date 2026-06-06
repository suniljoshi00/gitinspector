import pytest
from pydantic import ValidationError

from gitinspector.models import ReviewResult


def test_review_result_validates_structured_findings() -> None:
    result = ReviewResult.model_validate(
        {
            "summary": "One issue found.",
            "quality_score": 75,
            "findings": [
                {
                    "path": "app.py",
                    "line": 12,
                    "severity": "high",
                    "category": "security",
                    "title": "Unvalidated input",
                    "explanation": "User input reaches a command.",
                    "suggestion": "Validate against an allowlist.",
                    "confidence": 0.95,
                }
            ],
        }
    )

    assert result.findings[0].severity == "high"


def test_review_result_rejects_invalid_score() -> None:
    with pytest.raises(ValidationError):
        ReviewResult(summary="Invalid", quality_score=101)

