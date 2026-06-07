from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["critical", "high", "medium", "low"]
Category = Literal["bug", "security", "performance", "maintainability", "testing"]


class Finding(BaseModel):
    path: str
    line: int | None = None
    severity: Severity
    category: Category
    title: str
    explanation: str
    suggestion: str
    confidence: float = Field(ge=0, le=1)


class ReviewResult(BaseModel):
    summary: str
    quality_score: int = Field(ge=0, le=100)
    findings: list[Finding] = Field(default_factory=list)


class PullRequestRef(BaseModel):
    owner: str
    repo: str
    number: int
    head_sha: str
    base_sha: str = ""


class RepoContextSnippet(BaseModel):
    path: str
    start_line: int
    end_line: int
    content: str
