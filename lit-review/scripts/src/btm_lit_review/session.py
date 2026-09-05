"""Session storage: where a review lives, and how its three files are read."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    Model,
    NonEmpty,
    SessionStore,
    dump,
    parse_model,
    read_jsonl,
    write_atomic,
)
from btm_lit_review.constants import Level
from btm_lit_review.corpus.paper import Paper, paper_from_json

STORE = SessionStore("lit-review", marker="protocol.json", hint="run init first")


class Criteria(Model):
    """What a paper must show to be included, and what cuts it. Both lists
    stand before the first query; the script refuses to search without them."""

    include: tuple[NonEmpty, ...] = ()
    exclude: tuple[NonEmpty, ...] = ()


class Protocol(Model):
    """The review's frame, written at init and edited by hand thereafter."""

    question: NonEmpty
    level: Level = Level.FULL
    criteria: Criteria = Criteria()
    created: str = ""
    amendments: tuple[Any, ...] = ()  # free-form: the agent states each change

    @property
    def ready(self) -> bool:
        return bool(self.criteria.include and self.criteria.exclude)


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

    @property
    def snapshot_path(self) -> Path:
        return self.root / "snapshot.json"


def open_session(root: str) -> Session:
    return Session(STORE.directory(root))


def load_protocol(session: Session) -> Protocol:
    try:
        raw = json.loads(session.protocol_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CommandError(f"unreadable protocol.json: {err}") from err
    return parse_model(Protocol, raw, "protocol.json")


def criteria_hash(protocol: Protocol) -> str:
    canonical = json.dumps(dump(protocol.criteria), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def require_criteria(protocol: Protocol) -> None:
    if not protocol.ready:
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
    lines = [json.dumps(dump(paper), ensure_ascii=False) for paper in papers.values()]
    write_atomic(session.papers_path, "\n".join(lines) + ("\n" if lines else ""))
