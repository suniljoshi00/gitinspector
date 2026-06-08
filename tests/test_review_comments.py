from gitinspector.models import Finding
from gitinspector.review_comments import added_lines_by_path, build_inline_review_comments


SAMPLE_DIFF = """diff --git a/calculator.py b/calculator.py
index 1111111..2222222 100644
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,7 @@
 def divide(a, b):
     return a / b
+
+def execute_calculation(expression):
+    return eval(expression)
diff --git a/README.md b/README.md
index 3333333..4444444 100644
--- a/README.md
+++ b/README.md
@@ -1 +1,2 @@
 # Demo
+More text
"""


def test_added_lines_by_path_tracks_new_line_numbers() -> None:
    assert added_lines_by_path(SAMPLE_DIFF) == {
        "calculator.py": {3, 4, 5},
        "README.md": {2},
    }


def test_build_inline_review_comments_keeps_reviewable_findings() -> None:
    findings = [
        Finding(
            path="calculator.py",
            line=5,
            severity="high",
            category="security",
            title="Unsafe eval",
            explanation="User input reaches eval.",
            suggestion="Parse allowed arithmetic operators instead.",
            confidence=0.95,
        ),
        Finding(
            path="calculator.py",
            line=1,
            severity="low",
            category="maintainability",
            title="Existing line",
            explanation="This line was not added in the PR.",
            suggestion="Skip it.",
            confidence=0.5,
        ),
    ]

    comments = build_inline_review_comments(findings, SAMPLE_DIFF)

    assert len(comments) == 1
    assert comments[0]["path"] == "calculator.py"
    assert comments[0]["line"] == 5
    assert comments[0]["side"] == "RIGHT"
    assert "Unsafe eval" in str(comments[0]["body"])
