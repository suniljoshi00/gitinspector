from gitinspector.models import DismissedFinding, Finding, PullRequestRef, ReviewResult
from gitinspector.state import ReviewStateStore
from gitinspector.workflow import ReviewWorkflow


class FakeGitHub:
    def __init__(self) -> None:
        self.posted = False

    async def get_pull_request_diff(self, pr: PullRequestRef) -> str:
        return """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -0,0 +1 @@
+eval(user_input)
"""

    async def post_summary(self, pr: PullRequestRef, result: ReviewResult, diff: str = ""):
        self.posted = True
        return {"ok": True}


class FakeReviewer:
    async def review(self, diff: str, repo_context: str = "") -> ReviewResult:
        return ReviewResult(
            summary="Found one issue.",
            quality_score=20,
            findings=[
                Finding(
                    path="app.py",
                    line=1,
                    severity="high",
                    category="security",
                    title="Unsafe eval",
                    explanation="User input reaches eval.",
                    suggestion="Use a parser.",
                    confidence=0.95,
                )
            ],
        )


def test_feedback_memory_filters_dismissed_findings(tmp_path) -> None:
    store = ReviewStateStore(str(tmp_path / "reviews.db"))
    pr = PullRequestRef(owner="octo", repo="demo", number=1, head_sha="abc")
    finding = Finding(
        path="app.py",
        line=1,
        severity="high",
        category="security",
        title="Unsafe eval",
        explanation="User input reaches eval.",
        suggestion="Use a parser.",
        confidence=0.95,
    )

    store.record_dismissed_finding(
        DismissedFinding(
            owner="octo",
            repo="demo",
            path="app.py",
            category="security",
            title="Unsafe eval",
            reason="Known safe in this test harness.",
        )
    )

    assert store.filter_dismissed_findings(pr, [finding]) == []


async def test_langgraph_workflow_runs_review_and_posts(tmp_path) -> None:
    github = FakeGitHub()
    workflow = ReviewWorkflow(
        github=github,
        reviewer=FakeReviewer(),
        max_diff_characters=10_000,
        post_comments=True,
        state_store=ReviewStateStore(str(tmp_path / "reviews.db")),
    )
    pr = PullRequestRef(owner="octo", repo="demo", number=1, head_sha="abc")

    result = await workflow.run(pr)

    assert result.quality_score == 20
    assert len(result.findings) == 1
    assert github.posted
