from gitinspector.rag import changed_paths_from_diff, chunk_text, is_indexable_path


def test_changed_paths_from_diff_extracts_unique_paths() -> None:
    diff = """diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
diff --git a/src/util.ts b/src/util.ts
index 333..444 100644
--- a/src/util.ts
+++ b/src/util.ts
diff --git a/app.py b/app.py
index 555..666 100644
"""

    assert changed_paths_from_diff(diff) == ["app.py", "src/util.ts"]


def test_is_indexable_path_keeps_source_files_only() -> None:
    assert is_indexable_path("src/gitinspector/main.py")
    assert is_indexable_path("web/App.tsx")
    assert not is_indexable_path("README.md")
    assert not is_indexable_path("node_modules/pkg/index.js")


def test_chunk_text_records_line_ranges() -> None:
    text = "\n".join(f"line {index}" for index in range(1, 6))

    chunks = chunk_text("app.py", text, max_lines=2)

    assert len(chunks) == 3
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 2
    assert chunks[-1].start_line == 5
    assert chunks[-1].end_line == 5
