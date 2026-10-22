"""Every git call the engine makes, one subprocess each, no shell. Paths are
relative to `root` (the book, possibly nested in a larger repository); a
failed call raises `CommandError` naming what it read."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import btm_finance
from btm_corekit import CommandError

NOT_REPOSITORY = "book must be a git repository"
SEPARATOR = "\x1f"  # between hash, date, subject in one log header line
HEADER = "\x1e"  # opens each commit's header line


@dataclass(frozen=True, slots=True)
class Commit:
    """One commit touching the paths asked about: `files` relative to root,
    `date` committer date ISO 8601, `blobs` each file's blob id after it."""

    hash: str
    subject: str
    files: tuple[str, ...]
    date: str
    blobs: tuple[tuple[str, str | None], ...] = ()


def binary() -> str:
    found = shutil.which("git")
    if found is None:
        raise CommandError("no git on PATH; the book is a git repository")
    return found


def call(root: Path, args: Sequence[str], what: str) -> bytes:
    """stdout of `git -C root <args>`; any failure names `what`."""
    try:
        done = subprocess.run(
            [binary(), "-C", str(root), *args], capture_output=True, check=True
        )
    except subprocess.CalledProcessError as err:
        said = err.stderr.decode(errors="replace").strip()
        raise CommandError(f"git {args[0]} failed on {what}: {said}") from None
    return done.stdout


def lines(raw: bytes) -> list[str]:
    return raw.decode("utf-8", errors="replace").splitlines()


def inside(root: Path) -> bool:
    """`root` lies in a work tree."""
    done = subprocess.run(
        [binary(), "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        check=False,
    )
    return done.returncode == 0


def repository_at(root: Path) -> None:
    """Refuses `root` outside any work tree."""
    if not inside(root):
        raise CommandError(NOT_REPOSITORY)


def init(root: Path) -> None:
    """A new repository at `root` on branch `main`."""
    call(root, ["init", "-q", "-b", "main"], str(root))


def head(root: Path) -> str | None:
    """HEAD's hash; None before the first commit."""
    repository_at(root)
    done = subprocess.run(
        [binary(), "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
        capture_output=True,
        check=False,
    )
    return done.stdout.decode().strip() or None


def commit(root: Path, paths: Sequence[str], subject: str) -> str:
    """Stage and commit exactly `paths` (ignored files skipped), leaving any
    other staged change alone; the new HEAD."""
    call(root, ["add", "-A", "--", *paths], ", ".join(paths))
    call(root, ["commit", "-q", "-m", subject, "--", *paths], ", ".join(paths))
    found = head(root)
    if found is None:  # pragma: no cover - the commit just made one
        raise CommandError(f"git commit made no HEAD for {', '.join(paths)}")
    return found


def dirty(root: Path, paths: Sequence[str]) -> frozenset[str]:
    """Each file under `paths` that differs from HEAD (staged or not) or is
    untracked and not ignored."""
    repository_at(root)
    shown = ", ".join(paths)
    untracked = lines(
        call(root, ["ls-files", "--others", "--exclude-standard", "--", *paths], shown)
    )
    if head(root) is None:
        tracked = lines(call(root, ["ls-files", "--", *paths], shown))
        return frozenset(untracked + tracked)
    changed = lines(
        call(root, ["diff", "--relative", "--name-only", "HEAD", "--", *paths], shown)
    )
    return frozenset(untracked + changed)


def blob(root: Path, rev: str, path: str) -> str:
    """Blob id of `path` at `rev` (a commit or `HEAD`): survives rebase."""
    repository_at(root)
    found = call(root, ["rev-parse", f"{rev}:./{path}"], f"{path} at {rev}")
    return found.decode().strip()


def tree_blobs(root: Path, paths: Sequence[str]) -> dict[str, str]:
    """Blob id at HEAD of each committed file under `paths` (plain paths or
    directories, no globs); empty before the first commit."""
    repository_at(root)
    if head(root) is None:
        return {}
    found: dict[str, str] = {}
    for line in lines(
        call(root, ["ls-tree", "-r", "HEAD", "--", *paths], ", ".join(paths))
    ):
        meta, _, path = line.partition("\t")
        kind, object_id = meta.split()[1:3]
        if kind == "blob":
            found[path] = object_id
    return found


def show_blob(root: Path, object_id: str) -> bytes:
    """A blob's bytes by id, wherever its commits went."""
    return call(root, ["cat-file", "blob", object_id], f"blob {object_id}")


def log_commits(root: Path, paths: Sequence[str]) -> list[Commit]:
    """Every commit touching `paths`, newest first, with each file of `paths`
    it touched and that file's blob id after it (None when deleted). One
    `git log --raw`: O(commits + files)."""
    repository_at(root)
    if head(root) is None:
        return []
    raw = call(
        root,
        [
            "log",
            "--relative",
            "--raw",
            "--no-abbrev",
            "--no-renames",
            f"--format={HEADER}%H{SEPARATOR}%cI{SEPARATOR}%s",
            "--",
            *paths,
        ],
        ", ".join(paths),
    ).decode("utf-8", errors="replace")
    found: list[Commit] = []
    for block in raw.split(HEADER)[1:]:
        header, _, rest = block.partition("\n")
        hash_, stamp, subject = header.split(SEPARATOR, 2)
        blobs: list[tuple[str, str | None]] = []
        for line in rest.splitlines():
            meta, tab, path = line.partition("\t")
            if not (tab and meta.startswith(":")):
                continue
            after = meta.split()[3]
            blobs.append((path, None if after.strip("0") == "" else after))
        files = tuple(path for path, _ in blobs)
        found.append(Commit(hash_, subject, files, stamp, tuple(blobs)))
    return found


def changed(root: Path, base: str, tip: str) -> list[str]:
    """Files `tip` changed since its merge base with `base`
    (`git diff --name-only base...tip`), relative to root."""
    repository_at(root)
    return lines(
        call(
            root,
            ["diff", "--relative", "--name-only", f"{base}...{tip}"],
            f"{base}...{tip}",
        )
    )


def skill_commit() -> str:
    """The skill checkout's HEAD; the package version when the skill is no
    checkout or git is absent."""
    root = Path(btm_finance.__file__).resolve().parents[3]
    if shutil.which("git") is None or not inside(root):
        return btm_finance.__version__
    found = head(root)
    return found or btm_finance.__version__
