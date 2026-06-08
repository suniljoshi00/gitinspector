# GitInspector

GitInspector is a fully local, zero-cost GitHub pull request review agent. It
receives GitHub webhooks, fetches PR diffs through GitHub's free API, retrieves
related repository context with local RAG, reviews the change with Ollama, and
posts structured PR reviews with inline comments.

## Features

- Secure GitHub webhook listener with HMAC signature verification
- Automatic reviews for opened, reopened, and synchronized pull requests
- Custom MCP server exposing GitHub PR, diff, and file tools
- LangGraph workflow for fetch, RAG retrieval, review, feedback filtering, and posting
- Local ChromaDB RAG over source files from the PR base commit
- Ollama-powered review using a local coding model
- Structured findings with severity, category, confidence, and suggested fixes
- Inline GitHub review comments on changed lines
- SQLite review state to avoid duplicate reviews for the same commit
- Feedback memory for dismissed suggestions
- No paid APIs required

## Architecture

```text
GitHub Pull Request
        |
        v
GitHub Webhook
        |
        v
FastAPI /webhooks/github
        |
        v
LangGraph Review Workflow
   |         |          |
   |         |          +--> SQLite review state + feedback memory
   |         +--------------> ChromaDB repository RAG
   +------------------------> GitHub MCP/API tools
        |
        v
Ollama local model
        |
        v
GitHub PR review summary + inline comments
```

## Requirements

- Python 3.11+
- Git
- Ollama
- Cloudflare Tunnel for local webhook demos
- A free GitHub personal access token

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
ollama pull qwen2.5-coder:7b
```

Configure `.env`:

```env
GITHUB_TOKEN=github_pat_replace_me
GITHUB_WEBHOOK_SECRET=replace_with_a_long_random_value
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
POST_GITHUB_COMMENTS=false
RAG_ENABLED=true
RAG_PERSIST_DIR=.gitinspector/chroma
RAG_TOP_K=5
REVIEW_STATE_DB=.gitinspector/reviews.db
```

Keep `POST_GITHUB_COMMENTS=false` until webhook delivery has been tested.

## Run

Start Ollama:

```powershell
ollama serve
```

Start GitInspector:

```powershell
uvicorn gitinspector.main:app --reload
```

Health check:

```text
http://127.0.0.1:8000/health
```

Expose the local webhook:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

GitHub webhook settings:

```text
Payload URL: https://your-tunnel.trycloudflare.com/webhooks/github
Content type: application/json
Secret: same value as GITHUB_WEBHOOK_SECRET
Events: Pull requests
```

## MCP Server

Run the MCP server over stdio:

```powershell
python -m gitinspector.mcp_server
```

Available tools include:

- `get_pull_request`
- `get_pull_request_diff`
- `get_file`

## Feedback Memory

Record a dismissed suggestion:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/feedback/dismissed `
  -ContentType application/json `
  -Body '{
    "owner": "suniljoshi00",
    "repo": "git-inspector-test-repo",
    "path": "calculator.py",
    "category": "security",
    "title": "Unsafe eval",
    "reason": "Accepted for a controlled demo fixture"
  }'
```

Future reviews for the same repository suppress matching findings.

## Tests

```powershell
pytest
```

## Resume Bullets

- Built GitInspector, a fully local autonomous GitHub PR review agent using FastAPI, MCP, LangGraph, ChromaDB, SQLite, and Ollama.
- Implemented webhook-triggered review workflows with secure signature verification, repository-level RAG, structured findings, inline PR comments, and duplicate-review prevention.
- Designed feedback memory for dismissed suggestions, allowing the agent to suppress repeated low-value findings without using paid APIs.

## Roadmap

- Add an evaluation suite with intentionally vulnerable pull requests
- Add richer feedback matching with embeddings
- Add deployment templates for local Docker Compose demos
