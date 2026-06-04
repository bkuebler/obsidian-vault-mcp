import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_ALLOWED_URL = re.compile(r"^(https?|ssh|git)://")


@dataclass
class PullResult:
    conflict: bool
    files: list[str] = field(default_factory=list)


def _validate_url(url: str) -> None:
    if not _ALLOWED_URL.match(url):
        raise ValueError(f"Unsupported or unsafe git URL: {url!r}")


def init_vault(path: Path, url: str) -> None:
    _validate_url(url)
    if path.exists():
        subprocess.run(["git", "-C", str(path), "pull", "--rebase"], check=True)
    else:
        subprocess.run(["git", "clone", "--", url, str(path)], check=True)


def init_local_vault(path: Path) -> None:
    if not path.exists():
        subprocess.run(["git", "init", str(path)], check=True)


def commit(path: Path, message: str | None = None) -> None:
    if message is None:
        message = "vault sync"
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", message], check=True)


def commit_file(path: Path, filename: str, message: str) -> None:
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", message], check=True)


def push(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "push"], check=True)


def is_dirty(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def pull_rebase(path: Path) -> PullResult:
    result = subprocess.run(
        ["git", "-C", str(path), "pull", "--rebase"],
        capture_output=True,
    )
    if result.returncode == 0:
        return PullResult(conflict=False, files=[])
    unmerged = subprocess.run(
        ["git", "-C", str(path), "diff", "--name-only", "--diff-filter=U"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = [f for f in unmerged.stdout.strip().splitlines() if f]
    subprocess.run(["git", "-C", str(path), "rebase", "--abort"], check=True)
    return PullResult(conflict=True, files=files)


def reset_hard(path: Path, ref: str = "origin/HEAD") -> None:
    subprocess.run(["git", "-C", str(path), "reset", "--hard", ref], check=True)


def ahead_behind(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-list", "--left-right", "--count", "HEAD...@{u}"],
        check=True,
        capture_output=True,
        text=True,
    )
    ahead, behind = result.stdout.strip().split("\t")
    return int(ahead), int(behind)
