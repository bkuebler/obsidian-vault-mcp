from datetime import date
from obsidian_vault_mcp.frontmatter import read, write, build_metadata, merge_tags


# --- 3.1 Read ---


def test_read_returns_metadata_and_body(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntitle: My Note\ntags:\n  - foo\n---\nHello world\n")
    metadata, body = read(f)
    assert metadata["title"] == "My Note"
    assert metadata["tags"] == ["foo"]
    assert body.strip() == "Hello world"


def test_read_file_without_frontmatter(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("Just plain markdown\n")
    metadata, body = read(f)
    assert metadata == {}
    assert "Just plain markdown" in body


# --- 3.2 Write ---


def test_write_creates_file_with_frontmatter(tmp_path):
    f = tmp_path / "note.md"
    write(f, {"title": "Test"}, "Body text")
    content = f.read_text()
    assert content.startswith("---")
    assert "title: Test" in content


def test_write_roundtrip(tmp_path):
    f = tmp_path / "note.md"
    metadata = {"title": "Round trip", "tags": ["a", "b"]}
    body = "Some content here"
    write(f, metadata, body)
    recovered_meta, recovered_body = read(f)
    assert recovered_meta["title"] == "Round trip"
    assert recovered_meta["tags"] == ["a", "b"]
    assert recovered_body.strip() == body


def test_write_creates_parent_dirs(tmp_path):
    f = tmp_path / "Sessions" / "2026-06-01-topic.md"
    write(f, {"title": "Topic"}, "Content")
    assert f.exists()


# --- 3.3 Default frontmatter fields ---


def test_build_metadata_title_from_stem(tmp_path):
    path = tmp_path / "Sessions" / "2026-05-30-topic.md"
    metadata = build_metadata(path)
    assert metadata["title"] == "2026-05-30-topic"


def test_build_metadata_created_today(tmp_path):
    path = tmp_path / "note.md"
    metadata = build_metadata(path)
    assert metadata["created"] == date.today()


def test_build_metadata_modified_today(tmp_path):
    path = tmp_path / "note.md"
    metadata = build_metadata(path)
    assert metadata["modified"] == date.today()


def test_build_metadata_empty_aliases(tmp_path):
    path = tmp_path / "note.md"
    metadata = build_metadata(path)
    assert metadata["aliases"] == []


def test_build_metadata_tags_included(tmp_path):
    path = tmp_path / "note.md"
    metadata = build_metadata(path, tags=["session", "work"])
    assert metadata["tags"] == ["session", "work"]


def test_build_metadata_no_tags(tmp_path):
    path = tmp_path / "note.md"
    metadata = build_metadata(path)
    assert metadata["tags"] == []


# --- 3.4 Tag merging ---


def test_merge_tags_adds_new():
    assert merge_tags(["a"], ["b"]) == ["a", "b"]


def test_merge_tags_no_duplicates():
    assert merge_tags(["a"], ["a"]) == ["a"]


def test_merge_tags_preserves_order():
    result = merge_tags(["a", "b"], ["c", "a"])
    assert result.index("a") < result.index("c")
