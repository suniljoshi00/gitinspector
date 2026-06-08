from typing import NotRequired, TypedDict

from langgraph.graph import END, StateGraph

from gitinspector.github_client import GitHubClient
from gitinspector.models import PullRequestRef, RepoContextSnippet, ReviewResult
from gitinspector.rag import RepoRAG, format_repo_context
from gitinspector.reviewer import OllamaReviewer
from gitinspector.state import ReviewStateStore


class ReviewWorkflowState(TypedDict):
    pr: PullRequestRef
    diff: NotRequired[str]
    snippets: NotRequired[list[RepoContextSnippet]]
    repo_context: NotRequired[str]
    result: NotRequired[ReviewResult]


class ReviewWorkflow:
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
        self.graph = self._build_graph()

    async def run(self, pr: PullRequestRef) -> ReviewResult:
        final_state = await self.graph.ainvoke({"pr": pr})
        return final_state["result"]

    def _build_graph(self):
        graph = StateGraph(ReviewWorkflowState)
        graph.add_node("fetch_diff", self._fetch_diff)
        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("review_code", self._review_code)
        graph.add_node("apply_feedback", self._apply_feedback)
        graph.add_node("post_review", self._post_review)
        graph.set_entry_point("fetch_diff")
        graph.add_edge("fetch_diff", "retrieve_context")
        graph.add_edge("retrieve_context", "review_code")
        graph.add_edge("review_code", "apply_feedback")
        graph.add_edge("apply_feedback", "post_review")
        graph.add_edge("post_review", END)
        return graph.compile()

    async def _fetch_diff(self, state: ReviewWorkflowState) -> dict:
        diff = await self.github.get_pull_request_diff(state["pr"])
        return {"diff": diff}

    async def _retrieve_context(self, state: ReviewWorkflowState) -> dict:
        snippets = await self.rag.retrieve(state["pr"], state["diff"]) if self.rag else []
        return {
            "snippets": snippets,
            "repo_context": format_repo_context(snippets),
        }

    async def _review_code(self, state: ReviewWorkflowState) -> dict:
        result = await self.reviewer.review(
            state["diff"][: self.max_diff_characters],
            repo_context=state.get("repo_context", ""),
        )
        return {"result": result}

    async def _apply_feedback(self, state: ReviewWorkflowState) -> dict:
        result = state["result"]
        if not self.state_store:
            return {"result": result}

        filtered_findings = self.state_store.filter_dismissed_findings(
            state["pr"],
            result.findings,
        )
        if len(filtered_findings) == len(result.findings):
            return {"result": result}

        return {
            "result": result.model_copy(
                update={
                    "findings": filtered_findings,
                    "summary": (
                        result.summary
                        + " Previously dismissed suggestions were suppressed."
                    ),
                }
            )
        }

    async def _post_review(self, state: ReviewWorkflowState) -> dict:
        result = state["result"]
        if self.post_comments:
            await self.github.post_summary(state["pr"], result, diff=state["diff"])
        return {"result": result}
