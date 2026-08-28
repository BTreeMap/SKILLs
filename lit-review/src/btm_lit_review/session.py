"""Session storage: where a review lives, and how its three files are read."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    eliminate,
    is_pathlike,
    resolve,
    state_root,
    tree_bytes,
)
from btm_lit_review.paper import Paper, paper_from_json
from btm_lit_review.report import emit, signal


@dataclass(frozen=True, slots=True)
class Session:
    root: Path

    @property
    def protocol_path(self) -> Path:
        return self.root / "protocol.json"

    @property
    def papers_path(self) -> Path:
        return self.root / "papers.jsonl"

    @property
    def log_path(self) -> Path:
        return self.root / "search_log.jsonl"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sessions_root() -> Path:
    return state_root("lit-review") / "sessions"


def session_ids() -> list[str]:
    root = sessions_root()
    if not root.exists():
        return []
    return sorted(entry.name for entry in root.iterdir() if entry.is_dir())


def resolved_session(ref: str) -> Path:
    """Eliminate a session Resolution at the shell, rendering its signal."""
    full, note = eliminate(
        resolve(ref, session_ids()), ref, "session", hint="run init first"
    )
    if note:
        signal(note)
    return sessions_root() / full


def session_path(argument: str) -> Path:
    if is_pathlike(argument):
        return Path(argument).expanduser()
    return resolved_session(argument)


def open_session(root: str) -> Session:
    session = Session(session_path(root))
    if not session.protocol_path.is_file():
        raise CommandError(f"no session at {session.root}: run init first")
    return session


def load_protocol(session: Session) -> dict[str, Any]:
    try:
        protocol = json.loads(session.protocol_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CommandError(f"unreadable protocol.json: {err}") from err
    if not isinstance(protocol, dict):
        raise CommandError("protocol.json must hold a JSON object")
    return protocol


def criteria_hash(protocol: Mapping[str, Any]) -> str:
    canonical = json.dumps(protocol.get("criteria"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def require_criteria(protocol: Mapping[str, Any]) -> None:
    criteria = protocol.get("criteria") or {}
    if not criteria.get("include") or not criteria.get("exclude"):
        raise CommandError(
            "protocol.json has empty inclusion or exclusion criteria; "
            "fill both lists before searching (criteria precede search)"
        )


def load_papers(session: Session) -> dict[str, Paper]:
    papers: dict[str, Paper] = {}
    for line in session.papers_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            paper = paper_from_json(json.loads(line))
            papers[paper.key] = paper
    return papers


def atomic_write(path: Path, content: str) -> None:
    scratch = path.with_suffix(path.suffix + ".tmp")
    scratch.write_text(content, encoding="utf-8")
    os.replace(scratch, path)


def save_papers(session: Session, papers: Mapping[str, Paper]) -> None:
    lines = [json.dumps(asdict(paper), ensure_ascii=False) for paper in papers.values()]
    atomic_write(session.papers_path, "\n".join(lines) + ("\n" if lines else ""))


def read_log(session: Session) -> list[dict[str, Any]]:
    lines = session.log_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_log(session: Session, entry: Mapping[str, Any]) -> None:
    with session.log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cmd_clean(args: argparse.Namespace) -> int:
    root = sessions_root()
    if args.all and args.session:
        raise CommandError("pass a session or --all, one of the two")
    if args.all:
        if not root.is_dir():
            emit({"removed": None, "bytes_freed": 0})
            return 0
        freed = tree_bytes(root)
        shutil.rmtree(root)
        emit({"removed": str(root), "bytes_freed": freed})
        return 0
    if args.session is None:
        listing = (
            [
                {"session": entry.name, "bytes": tree_bytes(entry)}
                for entry in sorted(root.iterdir())
                if entry.is_dir()
            ]
            if root.is_dir()
            else []
        )
        emit(
            {
                "sessions_root": str(root),
                "sessions": listing,
                "next": "pass a session identifier or --all to remove and free space",
            }
        )
        return 0
    target = session_path(args.session)
    if not (target / "protocol.json").is_file():
        raise CommandError(
            f"{target} holds no session (protocol.json absent); refusing to remove"
        )
    freed = tree_bytes(target)
    shutil.rmtree(target)
    emit({"removed": str(target), "bytes_freed": freed})
    return 0
