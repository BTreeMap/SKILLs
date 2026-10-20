"""Book filesystem: the marker, human-owned files, chained appends under a
lock, and the strategy and proposal listings."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from btm_corekit import CommandError, SessionStore, parse_model, state_root
from btm_finance.ledger import Kind, chained, last_line
from btm_finance.models import BookMeta, Limits, Preferences, Status

SKILL = "finance"
MARKER = "book.json"
HINT = "run start <book path> first"
PAD_DIR = Path("ledger", "pad")


@dataclass(frozen=True, slots=True)
class Book:
    root: Path
    meta: BookMeta

    @property
    def ledger(self) -> Path:
        return self.root / "ledger"

    def path_of(self, kind: Kind) -> Path:
        return self.ledger / kind.file

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise CommandError(f"{path} is missing: {HINT}") from err
    except (OSError, ValueError) as err:
        raise CommandError(f"unreadable {path}: {err}") from err


def open_book(ref: str) -> Book:
    """The book at a path; its marker must exist, so a typo never makes one."""
    root = Path(ref).expanduser()
    if not (root / MARKER).is_file():
        raise CommandError(f"no book at {root}: {HINT}")
    return Book(
        root, parse_model(BookMeta, read_json(root / MARKER), str(root / MARKER))
    )


def load_limits(book: Book) -> Limits:
    path = book.root / "limits.json"
    return parse_model(Limits, read_json(path), str(path))


def load_preferences(book: Book) -> Preferences:
    path = book.root / "preferences.json"
    return parse_model(Preferences, read_json(path), str(path))


@dataclass(frozen=True, slots=True)
class PadStore(SessionStore):
    """The kernel pad, kept inside the book under `ledger/pad/`; `--known`
    stays the skill's cross-session pad."""

    def directory(self, ref: str) -> Path:
        return open_book(ref).root / PAD_DIR


PAD = PadStore(SKILL, marker=MARKER, hint=HINT)


def held_out_path(book_id: str) -> Path:
    """Outside the book, so nothing the agent edits on a branch holds it."""
    return state_root(SKILL) / book_id / "held-out.json"


def held_out_list(book: Book) -> tuple[str, frozenset[str]]:
    """The salt and member digests `start` wrote; read by `score` alone."""
    path = held_out_path(book.meta.id)
    if not path.is_file():
        raise CommandError(
            f"no held-out list for book {book.meta.id} on this machine; "
            "the operator restores it from backup before any score"
        )
    data = read_json(path)
    data = data if isinstance(data, dict) else {}
    salt, members = data.get("salt"), data.get("members")
    if not isinstance(salt, str) or not isinstance(members, list):
        raise CommandError(f"unreadable held-out list {path}: salt or members missing")
    return salt, frozenset(str(member) for member in members)


def ledger_files(book: Book) -> list[Path]:
    """Every chained file under `ledger/`; the pad is not chained."""
    pad = book.root / PAD_DIR
    return sorted(
        path for path in book.ledger.rglob("*.jsonl") if pad not in path.parents
    )


def run_files(book: Book) -> list[Path]:
    """The lead's `runs.jsonl` and each agent's `runs/<agent>.jsonl`: one table."""
    own = book.path_of(Kind.RUN)
    agents = sorted((book.ledger / "runs").glob("*.jsonl"))
    return ([own] if own.is_file() else []) + agents


def read_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.is_file() else b""


@contextmanager
def locked(path: Path) -> Iterator[IO[bytes]]:
    """The file opened for append and read under an exclusive lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if sys.platform == "win32":
            # ponytail: POSIX advisory lock only; a Windows book is unsupported.
            raise CommandError("record needs a POSIX file lock; Windows is unsupported")
        import fcntl  # noqa: PLC0415 - POSIX-only module, imported past the guard

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield handle


def append_chained(path: Path, records: Sequence[Mapping[str, Any]]) -> list[str]:
    """Append records as chained lines; the receipt is their ids. A file whose
    last line lacks its newline is a cut write: refused, never repaired."""
    with locked(path) as handle:
        handle.seek(0)
        data = handle.read()
        if data and not data.endswith(b"\n"):
            raise CommandError(
                f"{path} ends in a cut line; restore it from backup, then record"
            )
        lines = chained(last_line(data), records)
        handle.write(b"".join(line + b"\n" for line in lines))
        handle.flush()
        os.fsync(handle.fileno())
    return [str(record["id"]) for record in records]


def status_of(raw: str) -> Status | None:
    try:
        return Status(raw)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Strategy:
    name: str
    status: Status | None
    raw: str


def strategies(book: Book) -> list[Strategy]:
    """Each `strategies/<name>/` with its one-word `status`; an unknown word
    keeps its raw text so the view can name it."""
    root = book.root / "strategies"
    found: list[Strategy] = []
    for directory in sorted(root.iterdir() if root.is_dir() else []):
        if not directory.is_dir():
            continue
        status_file = directory / "status"
        raw = (
            status_file.read_text(encoding="utf-8").strip()
            if status_file.is_file()
            else ""
        )
        found.append(Strategy(directory.name, status_of(raw), raw))
    return found


def proposal_dates(book: Book) -> list[str]:
    root = book.root / "proposals"
    return sorted(path.stem for path in root.glob("*.json")) if root.is_dir() else []


def version_of(path: Path) -> int:
    """1 for `<day>.json`, n for `<day>.<n>.json`."""
    tail = path.stem.partition(".")[2]
    return int(tail) if tail.isdigit() else 1


def proposal_versions(book: Book, day: str) -> list[Path]:
    """`proposals/<day>.json`, then each `<day>.<n>.json`, by version."""
    root = book.root / "proposals"
    found = [root / f"{day}.json", *root.glob(f"{day}.*.json")]
    kept = [path for path in found if path.is_file() and version_of(path) > 0]
    return sorted(set(kept), key=version_of)


def proposal_target(book: Book, day: str, *, force: bool) -> Path:
    """Where `advise` writes: `<day>.json` once; with `force`, the next
    `<day>.<n>.json`, n from 2."""
    taken = proposal_versions(book, day)
    if not taken:
        return book.root / "proposals" / f"{day}.json"
    if not force:
        raise CommandError(
            f"proposals/{taken[-1].name} exists; a proposal is written once: "
            "pass --force to write the next version beside it"
        )
    return book.root / "proposals" / f"{day}.{version_of(taken[-1]) + 1}.json"


def previous_proposal(book: Book, day: str) -> Path | None:
    """The newest version of the latest proposal dated before `day`."""
    days = sorted({stem.partition(".")[0] for stem in proposal_dates(book)})
    earlier = [d for d in days if d < day]
    versions = proposal_versions(book, earlier[-1]) if earlier else []
    return versions[-1] if versions else None
