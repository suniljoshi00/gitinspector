import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from gitinspector.config import get_settings
from gitinspector.github_client import GitHubClient
from gitinspector.models import DismissedFinding, PullRequestRef
from gitinspector.rag import RepoRAG
from gitinspector.reviewer import OllamaReviewer
from gitinspector.security import verify_github_signature
from gitinspector.service import ReviewService
from gitinspector.state import ReviewStateStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitInspector", version="0.1.0")


def build_review_service() -> ReviewService:
    settings = get_settings()
    github = GitHubClient(settings.github_token, settings.github_api_url)
    rag = (
        RepoRAG(github, settings.rag_persist_dir, settings.rag_top_k)
        if settings.rag_enabled
        else None
    )
    return ReviewService(
        github=github,
        reviewer=OllamaReviewer(settings.ollama_base_url, settings.ollama_model),
        max_diff_characters=settings.max_diff_characters,
        post_comments=settings.post_github_comments,
        rag=rag,
        state_store=ReviewStateStore(settings.review_state_db),
    )


async def run_review(pr: PullRequestRef) -> None:
    service = build_review_service()
    try:
        result = await service.review_pull_request(pr)
        logger.info(
            "Reviewed %s/%s#%s: score=%s findings=%s",
            pr.owner,
            pr.repo,
            pr.number,
            result.quality_score,
            len(result.findings),
        )
    except Exception:
        logger.exception("Review failed for %s/%s#%s", pr.owner, pr.repo, pr.number)
    finally:
        await service.github.close()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/feedback/dismissed", status_code=201)
async def dismiss_finding(finding: DismissedFinding) -> dict[str, str]:
    settings = get_settings()
    ReviewStateStore(settings.review_state_db).record_dismissed_finding(finding)
    return {"status": "recorded"}


@app.post("/webhooks/github", status_code=202)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, str]:
    settings = get_settings()
    body = await request.body()
    if not verify_github_signature(
        body,
        x_hub_signature_256,
        settings.github_webhook_secret,
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    supported_actions = {"opened", "reopened", "synchronize"}
    if x_github_event != "pull_request" or payload.get("action") not in supported_actions:
        return {"status": "ignored"}

    repo = payload["repository"]
    pull_request = payload["pull_request"]
    pr = PullRequestRef(
        owner=repo["owner"]["login"],
        repo=repo["name"],
        number=payload["number"],
        head_sha=pull_request["head"]["sha"],
        base_sha=pull_request["base"]["sha"],
    )
    background_tasks.add_task(run_review, pr)
    return {"status": "accepted"}
