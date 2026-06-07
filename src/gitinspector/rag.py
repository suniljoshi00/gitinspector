import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from gitinspector.github_client import GitHubClient
from gitinspector.models import PullRequestRef, RepoContextSnippet

SOURCE_EXTENSIONS = {
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".ts",
    ".tsx",
}

SKIPPED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "vendor",
}


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    path: str
    start_line: int
    end_line: int
    content: str


def changed_paths_from_diff(diff: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r"^diff --git a/(.*?) b/(.*?)$", diff, re.MULTILINE):
        path = match.group(2)
        if path != "/dev/null" and path not in paths:
            paths.append(path)
    return paths


def is_indexable_path(path: str) -> bool:
    file_path = Path(path)
    if file_path.suffix.lower() not in SOURCE_EXTENSIONS:
        return False
    return not any(part in SKIPPED_PARTS for part in file_path.parts)


def chunk_text(path: str, text: str, max_lines: int = 80) -> list[IndexedChunk]:
    lines = text.splitlines()
    chunks: list[IndexedChunk] = []
    for start in range(0, len(lines), max_lines):
        selected = lines[start : start + max_lines]
        if not selected:
            continue
        content = "\n".join(selected)
        digest = hashlib.sha256(f"{path}:{start}:{content}".encode()).hexdigest()[:16]
        chunks.append(
            IndexedChunk(
                id=f"{path}:{start + 1}:{digest}",
                path=path,
                start_line=start + 1,
                end_line=start + len(selected),
                content=content,
            )
        )
    return chunks


def format_repo_context(snippets: list[RepoContextSnippet]) -> str:
    if not snippets:
        return "No related repository context was retrieved."

    formatted = []
    for snippet in snippets:
        formatted.append(
            f"File: {snippet.path}:{snippet.start_line}-{snippet.end_line}\n"
            f"```text\n{snippet.content}\n```"
        )
    return "\n\n".join(formatted)


class RepoRAG:
    def __init__(
        self,
        github: GitHubClient,
        persist_dir: str,
        top_k: int,
        max_file_bytes: int = 120_000,
    ) -> None:
        self.github = github
        self.persist_dir = persist_dir
        self.top_k = top_k
        self.max_file_bytes = max_file_bytes

    async def retrieve(self, pr: PullRequestRef, diff: str) -> list[RepoContextSnippet]:
        if not pr.base_sha:
            return []

        chromadb = _import_chromadb()
        client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(collection_name(pr))
        collection_size = collection.count()
        if collection_size == 0:
            await self._index_repository(collection, pr)
            collection_size = collection.count()
        if collection_size == 0:
            return []

        query = "\n".join(changed_paths_from_diff(diff)) + "\n\n" + diff[:6_000]
        result = collection.query(
            query_texts=[query],
            n_results=min(self.top_k, collection_size),
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        snippets: list[RepoContextSnippet] = []
        for document, metadata in zip(documents, metadatas):
            snippets.append(
                RepoContextSnippet(
                    path=str(metadata["path"]),
                    start_line=int(metadata["start_line"]),
                    end_line=int(metadata["end_line"]),
                    content=document,
                )
            )
        return snippets

    async def _index_repository(self, collection, pr: PullRequestRef) -> None:
        tree = await self.github.get_repository_tree(pr.owner, pr.repo, pr.base_sha)
        for item in tree:
            path = item.get("path", "")
            if item.get("type") != "blob" or not is_indexable_path(path):
                continue
            if int(item.get("size") or 0) > self.max_file_bytes:
                continue

            text = await self.github.get_file_text(pr.owner, pr.repo, path, pr.base_sha)
            chunks = chunk_text(path, text)
            if not chunks:
                continue
            collection.add(
                ids=[chunk.id for chunk in chunks],
                documents=[chunk.content for chunk in chunks],
                metadatas=[
                    {
                        "path": chunk.path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                    }
                    for chunk in chunks
                ],
            )


def collection_name(pr: PullRequestRef) -> str:
    raw = f"{pr.owner}_{pr.repo}_{pr.base_sha}".lower()
    safe = re.sub(r"[^a-z0-9_-]+", "_", raw)[:63].strip("_")
    return safe or "gitinspector_repo"


def _import_chromadb():
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
    try:
        import chromadb
    except ImportError as error:
        raise RuntimeError(
            'RAG is enabled but chromadb is not installed. Run: pip install -e ".[dev]"'
        ) from error
    return chromadb
