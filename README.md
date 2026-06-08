# GitInspector

GitInspector is a fully local, zero-cost GitHub pull request review agent. It
receives GitHub webhooks, fetches PR diffs through GitHub's free API, reviews
them with a local Ollama model, and can post a structured summary back to the PR.
It also indexes source files from the PR's base commit into local ChromaDB so
reviews can reference related repository context without sending code to paid
APIs.

## Current MVP

- Verifies GitHub webhook signatures
- Handles opened, reopened, and synchronized pull requests
- Reviews unified diffs with a local Ollama coding model
- Retrieves related source snippets with local ChromaDB RAG
- Produces validated, structured findings
- Optionally posts a pull request review summary with inline comments on changed lines
- Stores review job state in SQLite to avoid duplicate reviews for the same commit
- Exposes GitHub PR, diff, and file tools through a custom MCP server

## Requirements

- Python 3.11+
- Git
- Ollama
- A free GitHub personal access token

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
ollama pull qwen2.5-coder:7b
```

Set `GITHUB_TOKEN` and `GITHUB_WEBHOOK_SECRET` in `.env`. Keep
`POST_GITHUB_COMMENTS=false` until webhook handling has been tested.

RAG is enabled by default:

```env
RAG_ENABLED=true
RAG_PERSIST_DIR=.gitinspector/chroma
RAG_TOP_K=5
REVIEW_STATE_DB=.gitinspector/reviews.db
```

The first review for a repository commit may be slower because GitInspector
fetches source files through the GitHub API and builds a local vector index.

## Run

Start Ollama, then launch the API:

```powershell
ollama serve
uvicorn gitinspector.main:app --reload
```

Health check: `http://127.0.0.1:8000/health`

Run the MCP server over stdio:

```powershell
python -m gitinspector.mcp_server
```

Run tests:

```powershell
pytest
```

## Next Milestones

1. Add a LangGraph workflow with specialized review stages.
2. Store dismissed suggestions as feedback memory.
3. Add evaluation fixtures containing intentionally buggy PRs.
