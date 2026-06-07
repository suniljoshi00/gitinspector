from gitinspector.github_client import GitHubClient
from gitinspector.models import PullRequestRef, ReviewResult
from gitinspector.rag import RepoRAG, format_repo_context
from gitinspector.reviewer import OllamaReviewer


class ReviewService:
    def __init__(
        self,
        github: GitHubClient,
        reviewer: OllamaReviewer,
        max_diff_characters: int,
        post_comments: bool,
        rag: RepoRAG | None = None,
    ) -> None:
        self.github = github
        self.reviewer = reviewer
        self.max_diff_characters = max_diff_characters
        self.post_comments = post_comments
        self.rag = rag

    async def review_pull_request(self, pr: PullRequestRef) -> ReviewResult:
        diff = await self.github.get_pull_request_diff(pr)
        snippets = await self.rag.retrieve(pr, diff) if self.rag else []
        repo_context = format_repo_context(snippets)
        result = await self.reviewer.review(
            diff[: self.max_diff_characters],
            repo_context=repo_context,
        )
        if self.post_comments:
            await self.github.post_summary(pr, result)
        return result
