import sqlite3
from pathlib import Path

from gitinspector.models import DismissedFinding, Finding, PullRequestRef


class ReviewStateStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def has_successful_review(self, pr: PullRequestRef) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM review_jobs
                WHERE owner = ?
                  AND repo = ?
                  AND pr_number = ?
                  AND head_sha = ?
                  AND status = 'completed'
                LIMIT 1
                """,
                (pr.owner, pr.repo, pr.number, pr.head_sha),
            ).fetchone()
        return row is not None

    def mark_started(self, pr: PullRequestRef) -> None:
        self._upsert(pr, "started", None)

    def mark_completed(self, pr: PullRequestRef) -> None:
        self._upsert(pr, "completed", None)

    def mark_failed(self, pr: PullRequestRef, error: str) -> None:
        self._upsert(pr, "failed", error[:1_000])

    def record_dismissed_finding(self, finding: DismissedFinding) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dismissed_findings (
                    owner, repo, path, category, title_key, title, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(owner, repo, path, category, title_key)
                DO UPDATE SET
                    title = excluded.title,
                    reason = excluded.reason,
                    created_at = CURRENT_TIMESTAMP
                """,
                (
                    finding.owner,
                    finding.repo,
                    finding.path,
                    finding.category,
                    normalize_title(finding.title),
                    finding.title,
                    finding.reason,
                ),
            )

    def filter_dismissed_findings(
        self,
        pr: PullRequestRef,
        findings: list[Finding],
    ) -> list[Finding]:
        if not findings:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT path, category, title_key
                FROM dismissed_findings
                WHERE owner = ? AND repo = ?
                """,
                (pr.owner, pr.repo),
            ).fetchall()

        dismissed = {(row[0], row[1], row[2]) for row in rows}
        return [
            finding
            for finding in findings
            if (
                finding.path,
                finding.category,
                normalize_title(finding.title),
            )
            not in dismissed
        ]

    def _upsert(self, pr: PullRequestRef, status: str, error: str | None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO review_jobs (
                    owner, repo, pr_number, head_sha, status, error, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(owner, repo, pr_number, head_sha)
                DO UPDATE SET
                    status = excluded.status,
                    error = excluded.error,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (pr.owner, pr.repo, pr.number, pr.head_sha, status, error),
            )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS review_jobs (
                    owner TEXT NOT NULL,
                    repo TEXT NOT NULL,
                    pr_number INTEGER NOT NULL,
                    head_sha TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner, repo, pr_number, head_sha)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dismissed_findings (
                    owner TEXT NOT NULL,
                    repo TEXT NOT NULL,
                    path TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner, repo, path, category, title_key)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)


def normalize_title(title: str) -> str:
    return " ".join(title.lower().strip().split())
