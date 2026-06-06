from gitinspector.github_client import GitHubClient
from gitinspector.models import PullRequestRef, ReviewResult
from gitinspector.reviewer import OllamaReviewer


class ReviewService:
    def __init__(
        self,
        github: GitHubClient,
        reviewer: OllamaReviewer,
        max_diff_characters: int,
        post_comments: bool,
    ) -> None:
        self.github = github
        self.reviewer = reviewer
        self.max_diff_characters = max_diff_characters
        self.post_comments = post_comments

    async def review_pull_request(self, pr: PullRequestRef) -> ReviewResult:
        diff = await self.github.get_pull_request_diff(pr)
        result = await self.reviewer.review(diff[: self.max_diff_characters])
        if self.post_comments:
            await self.github.post_summary(pr, result)
        return result

