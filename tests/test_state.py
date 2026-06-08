from gitinspector.models import PullRequestRef
from gitinspector.state import ReviewStateStore


def test_state_store_detects_completed_review(tmp_path) -> None:
    store = ReviewStateStore(str(tmp_path / "reviews.db"))
    pr = PullRequestRef(
        owner="octo",
        repo="demo",
        number=1,
        head_sha="abc123",
        base_sha="base123",
    )

    assert not store.has_successful_review(pr)

    store.mark_started(pr)
    assert not store.has_successful_review(pr)

    store.mark_completed(pr)
    assert store.has_successful_review(pr)


def test_state_store_allows_retry_after_failure(tmp_path) -> None:
    store = ReviewStateStore(str(tmp_path / "reviews.db"))
    pr = PullRequestRef(owner="octo", repo="demo", number=2, head_sha="def456")

    store.mark_failed(pr, "temporary error")

    assert not store.has_successful_review(pr)

    store.mark_completed(pr)

    assert store.has_successful_review(pr)
