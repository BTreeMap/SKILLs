"""Session storage: where a review lives, and how its three files are read."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    SessionStore,
    read_jsonl,
    write_atomic,
)
from btm_lit_review.paper import Paper, paper_from_json

STORE = SessionStore("lit-review", marker="protocol.json", hint="run init first")


@dataclass(frozen=True, slots=True)
class Session:
    root: Path

    @property
    def protocol_path(self) -> Path:
        return self.root / STORE.marker

    @property
    def papers_path(self) -> Path:
        return self.root / "papers.jsonl"

    @property
    def log_path(self) -> Path:
        return self.root / "search_log.jsonl"

    @property
    def notebook_path(self) -> Path:
        return self.root / "notebook.jsonl"

    @property
    def citations_path(self) -> Path:
        return self.root / "citations.json"


def open_session(root: str) -> Session:
    return Session(STORE.directory(root))


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
    for record in read_jsonl(session.papers_path):
        paper = paper_from_json(record)
        papers[paper.key] = paper
    return papers


def save_papers(session: Session, papers: Mapping[str, Paper]) -> None:
    lines = [json.dumps(asdict(paper), ensure_ascii=False) for paper in papers.values()]
    write_atomic(session.papers_path, "\n".join(lines) + ("\n" if lines else ""))
