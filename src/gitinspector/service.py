from gitinspector.github_client import GitHubClient
from gitinspector.models import PullRequestRef, ReviewResult
from gitinspector.rag import RepoRAG, format_repo_context
from gitinspector.reviewer import OllamaReviewer
from gitinspector.state import ReviewStateStore


class ReviewService:
    def __init__(
        self,
        github: GitHubClient,
        reviewer: OllamaReviewer,
        max_diff_characters: int,
        post_comments: bool,
        rag: RepoRAG | None = None,
        state_store: ReviewStateStore | None = None,
    ) -> None:
        self.github = github
        self.reviewer = reviewer
        self.max_diff_characters = max_diff_characters
        self.post_comments = post_comments
        self.rag = rag
        self.state_store = state_store

    async def review_pull_request(self, pr: PullRequestRef) -> ReviewResult:
        if self.state_store and self.state_store.has_successful_review(pr):
            return ReviewResult(
                summary="Skipped because this pull request commit was already reviewed.",
                quality_score=100,
                findings=[],
            )

        if self.state_store:
            self.state_store.mark_started(pr)

        try:
            diff = await self.github.get_pull_request_diff(pr)
            snippets = await self.rag.retrieve(pr, diff) if self.rag else []
            repo_context = format_repo_context(snippets)
            result = await self.reviewer.review(
                diff[: self.max_diff_characters],
                repo_context=repo_context,
            )
            if self.post_comments:
                await self.github.post_summary(pr, result, diff=diff)
            if self.state_store:
                self.state_store.mark_completed(pr)
            return result
        except Exception as error:
            if self.state_store:
                self.state_store.mark_failed(pr, str(error))
            raise
