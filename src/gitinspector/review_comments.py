import re

from gitinspector.models import Finding


def added_lines_by_path(diff: str) -> dict[str, set[int]]:
    added_lines: dict[str, set[int]] = {}
    current_path: str | None = None
    new_line: int | None = None

    for raw_line in diff.splitlines():
        file_match = re.match(r"^diff --git a/(.*?) b/(.*?)$", raw_line)
        if file_match:
            current_path = file_match.group(2)
            added_lines.setdefault(current_path, set())
            new_line = None
            continue

        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk_match:
            new_line = int(hunk_match.group(1))
            continue

        if current_path is None or new_line is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines[current_path].add(new_line)
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        else:
            new_line += 1

    return added_lines


def build_inline_review_comments(
    findings: list[Finding],
    diff: str,
    limit: int = 10,
) -> list[dict[str, object]]:
    reviewable_lines = added_lines_by_path(diff)
    comments: list[dict[str, object]] = []

    for finding in findings:
        if len(comments) >= limit:
            break
        if finding.line is None:
            continue
        if finding.line not in reviewable_lines.get(finding.path, set()):
            continue

        body = (
            f"**{finding.severity.upper()} {finding.category}: {finding.title}**\n\n"
            f"{finding.explanation}\n\n"
            f"Suggested fix: {finding.suggestion}\n\n"
            f"Confidence: {finding.confidence:.0%}"
        )
        comments.append(
            {
                "path": finding.path,
                "line": finding.line,
                "side": "RIGHT",
                "body": body,
            }
        )

    return comments
