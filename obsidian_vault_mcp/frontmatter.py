from datetime import date
from pathlib import Path
import frontmatter as fm


def read(path: Path) -> tuple[dict, str]:
    post = fm.load(str(path))
    return dict(post.metadata), post.content


def write(path: Path, metadata: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = fm.Post(body, **metadata)
    path.write_text(fm.dumps(post))


def build_metadata(path: Path, tags: list[str] | None = None) -> dict:
    return {
        "title": Path(path).stem,
        "created": date.today(),
        "modified": date.today(),
        "tags": tags if tags is not None else [],
        "aliases": [],
    }


def merge_tags(existing: list[str], new: list[str]) -> list[str]:
    seen = set(existing)
    result = list(existing)
    for tag in new:
        if tag not in seen:
            result.append(tag)
            seen.add(tag)
    return result
