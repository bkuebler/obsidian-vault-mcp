import datetime
import subprocess
from pathlib import Path
from urllib.parse import unquote

from obsidian_vault_mcp import frontmatter as fm

PROTECTED_ROOT_FILES = {"AGENTS.md", "CLAUDE.md"}


class Vault:
    def __init__(self, root: Path, enforce_frontmatter: bool = True) -> None:
        self.root = root.resolve()
        self.enforce_frontmatter = enforce_frontmatter

    def resolve(self, path: str) -> Path:
        decoded = unquote(path)
        if ".." in Path(decoded).parts:
            raise ValueError(f"Path traversal detected: {path!r}")
        resolved = (self.root / decoded).resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Path traversal detected: {path!r}")
        return resolved

    def _assert_not_protected(self, resolved: Path) -> None:
        if resolved.parent == self.root and resolved.name in PROTECTED_ROOT_FILES:
            raise PermissionError(f"Protected file: {resolved.name!r}")

    def note_create(
        self, path: str, content: str, tags: list[str] | None = None
    ) -> None:
        target = self.resolve(path)
        self._assert_not_protected(target)
        if self.enforce_frontmatter:
            metadata = fm.build_metadata(target, tags=tags)
        else:
            metadata = {"tags": tags} if tags else {}
        fm.write(target, metadata, content)

    def note_read(self, path: str) -> tuple[dict, str]:
        target = self.resolve(path)
        self._assert_not_protected(target)
        if not target.exists():
            raise FileNotFoundError(f"Note not found: {path!r}")
        return fm.read(target)

    def note_update(
        self,
        path: str,
        content: str | None = None,
        append: bool = False,
        tags: list[str] | None = None,
    ) -> None:
        if append and content is None:
            raise ValueError("append=True requires content")
        metadata, body = self.note_read(path)
        if content is not None:
            body = f"{body}\n{content}" if append else content
        if tags is not None:
            metadata["tags"] = fm.merge_tags(metadata.get("tags", []), tags)
        if self.enforce_frontmatter:
            metadata["modified"] = datetime.date.today()
        target = self.resolve(path)
        fm.write(target, metadata, body)

    def note_delete(self, path: str) -> None:
        target = self.resolve(path)
        self._assert_not_protected(target)
        if not target.exists():
            raise FileNotFoundError(f"Note not found: {path!r}")
        target.unlink()

    def note_list(self, folder: str | None = None) -> list[dict]:
        base = self.resolve(folder) if folder else self.root
        entries = []
        for md_file in sorted(base.rglob("*.md")):
            if md_file.parent == self.root and md_file.name in PROTECTED_ROOT_FILES:
                continue
            metadata, _ = fm.read(md_file)
            rel = md_file.relative_to(self.root)
            entries.append(
                {
                    "path": str(rel),
                    "title": metadata.get("title", md_file.stem),
                }
            )
        return entries

    def note_search(
        self,
        query: str,
        tags: list[str] | None = None,
        folder: str | None = None,
    ) -> list[dict]:
        base = self.resolve(folder) if folder else self.root
        result = subprocess.run(
            ["grep", "-r", "-i", "-l", "-e", query, "--", str(base)],
            capture_output=True,
            text=True,
        )
        matched_files = [
            Path(p) for p in result.stdout.splitlines() if p.endswith(".md")
        ]
        entries = []
        for md_file in matched_files:
            metadata, _ = fm.read(md_file)
            if tags is not None:
                file_tags = metadata.get("tags", [])
                if not all(t in file_tags for t in tags):
                    continue
            rel = md_file.relative_to(self.root)
            entries.append(
                {
                    "path": str(rel),
                    "title": metadata.get("title", md_file.stem),
                }
            )
        return entries
