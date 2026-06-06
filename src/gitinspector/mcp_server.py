import asyncio

from mcp.server.fastmcp import FastMCP

from gitinspector.config import get_settings
from gitinspector.github_client import GitHubClient
from gitinspector.models import PullRequestRef

mcp = FastMCP("GitInspector GitHub Tools")


def run(coroutine):
    return asyncio.run(coroutine)


def client() -> GitHubClient:
    settings = get_settings()
    return GitHubClient(settings.github_token, settings.github_api_url)


async def fetch_pull_request(pr: PullRequestRef) -> dict:
    github = client()
    try:
        return await github.get_pull_request(pr)
    finally:
        await github.close()


async def fetch_pull_request_diff(pr: PullRequestRef) -> str:
    github = client()
    try:
        return await github.get_pull_request_diff(pr)
    finally:
        await github.close()


async def fetch_file(owner: str, repo: str, path: str, ref: str) -> dict:
    github = client()
    try:
        return await github.get_file(owner, repo, path, ref)
    finally:
        await github.close()


@mcp.tool()
def get_pull_request(owner: str, repo: str, number: int, head_sha: str = "") -> dict:
    """Get metadata for a GitHub pull request."""
    return run(
        fetch_pull_request(
            PullRequestRef(owner=owner, repo=repo, number=number, head_sha=head_sha)
        )
    )


@mcp.tool()
def get_pull_request_diff(owner: str, repo: str, number: int, head_sha: str = "") -> str:
    """Get the unified diff for a GitHub pull request."""
    return run(
        fetch_pull_request_diff(
            PullRequestRef(owner=owner, repo=repo, number=number, head_sha=head_sha)
        )
    )


@mcp.tool()
def get_file(owner: str, repo: str, path: str, ref: str) -> dict:
    """Get a file from a GitHub repository at a specific ref."""
    return run(fetch_file(owner, repo, path, ref))


if __name__ == "__main__":
    mcp.run()
