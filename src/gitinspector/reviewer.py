import json

import httpx

from gitinspector.models import ReviewResult


SYSTEM_PROMPT = """You are a careful senior code reviewer.
Review the supplied pull request diff using the related repository context when
it helps explain conventions, existing helpers, or likely regressions. Identify
concrete bugs, security risks, performance problems, maintainability issues, and
missing tests. Avoid style-only comments and speculation. Return valid JSON matching:
{
  "summary": "short overall assessment",
  "quality_score": 0,
  "findings": [{
    "path": "file/path.py",
    "line": 1,
    "severity": "critical|high|medium|low",
    "category": "bug|security|performance|maintainability|testing",
    "title": "short title",
    "explanation": "why this matters",
    "suggestion": "specific fix",
    "confidence": 0.0
  }]
}
Use an empty findings array when there are no concrete issues."""


class OllamaReviewer:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def review(self, diff: str, repo_context: str = "") -> ReviewResult:
        user_prompt = (
            "Related repository context:\n"
            f"{repo_context or 'No related repository context was retrieved.'}\n\n"
            "Pull request diff:\n"
            f"{diff}"
        )
        async with httpx.AsyncClient(base_url=self._base_url, timeout=180) as client:
            response = await client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()

        content = response.json()["message"]["content"]
        return ReviewResult.model_validate(json.loads(content))
