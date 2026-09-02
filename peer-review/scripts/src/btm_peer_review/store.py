"""Session filesystem: meta, ledger, paper text, and the linked corpus."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    SessionStore,
    append_jsonl,
    now_iso,
    read_jsonl,
    write_atomic,
)
from btm_peer_review.constants import DATE, Level
from btm_peer_review.state import parse_enum, require

STORE = SessionStore("peer-review", marker="session.json", hint="run init first")
LIT_STORE = SessionStore(
    "lit-review", marker="protocol.json", hint="run lit-review init first"
)
LEDGER = "ledger.jsonl"
PAPER = "paper.txt"


def meta_path(directory: Path) -> Path:
    return directory / STORE.marker


def ledger_path(directory: Path) -> Path:
    return directory / LEDGER


def paper_path(directory: Path) -> Path:
    return directory / PAPER


def year_of(date: str) -> int:
    match = DATE.fullmatch(date)
    require(match is not None, "date is YYYY, YYYY-MM, or YYYY-MM-DD")
    return int(match.group(1))


@dataclass(frozen=True, slots=True)
class Meta:
    """Session facts fixed at init, extended by ingest and link."""

    title: str
    date: str
    level: Level
    created: str
    corpus: str | None = None
    pages: int = 0

    @property
    def year(self) -> int:
        return year_of(self.date)

    def view(self) -> dict[str, Any]:
        return asdict(self)


def new_meta(title: str, date: str, level: Level) -> Meta:
    year_of(date)
    return Meta(title=title, date=date, level=level, created=now_iso())


def read_meta(directory: Path) -> Meta:
    path = meta_path(directory)
    if not path.is_file():
        raise CommandError(f"no session at {directory}: run init first")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CommandError(f"unreadable {path}: {err}") from err
    require(isinstance(raw, dict), f"{path} must hold a JSON object")
    level = parse_enum(Level, raw.get("level"), f"{path} level")
    title, date, created = raw.get("title"), raw.get("date"), raw.get("created")
    require(isinstance(title, str), f"{path} lacks a title")
    require(isinstance(date, str), f"{path} lacks a date")
    corpus, pages = raw.get("corpus"), raw.get("pages", 0)
    require(corpus is None or isinstance(corpus, str), f"{path} corpus must be a path")
    require(isinstance(pages, int), f"{path} pages must be an integer")
    year_of(date)
    return Meta(title, date, level, str(created or ""), corpus, pages)


def write_meta(directory: Path, meta: Meta) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    write_atomic(
        meta_path(directory), json.dumps(meta.view(), indent=2, ensure_ascii=False)
    )
    ledger_path(directory).touch()


def update_meta(directory: Path, meta: Meta, **changes: Any) -> Meta:
    updated = replace(meta, **changes)
    write_meta(directory, updated)
    return updated


def read_events(directory: Path) -> list[dict[str, Any]]:
    path = ledger_path(directory)
    if not path.exists():
        raise CommandError(f"no session at {directory}: run init first")
    return read_jsonl(path)


def append_events(directory: Path, admitted: list[dict[str, Any]]) -> None:
    stamp = now_iso()
    append_jsonl(ledger_path(directory), [{"t": stamp, **raw} for raw in admitted])


@dataclass(frozen=True, slots=True)
class Record:
    key: str
    year: int | None
    title: str
    status: str


@dataclass(frozen=True, slots=True)
class Corpus:
    """The linked lit-review corpus: its records, indexed by every alias."""

    path: Path
    records: tuple[Record, ...]
    aliases: dict[str, Record]

    def lookup(self, ref: str) -> Record | None:
        return self.aliases.get(ref.strip().lower())


def load_corpus(path: Path) -> Corpus:
    if not path.is_file():
        raise CommandError(f"no corpus at {path}: link a lit-review session")
    records: list[Record] = []
    aliases: dict[str, Record] = {}
    for raw in read_jsonl(path):
        key = raw.get("key")
        if not isinstance(key, str) or not key:
            continue
        year = raw.get("year")
        record = Record(
            key=key,
            year=year if isinstance(year, int) else None,
            title=str(raw.get("title", "")),
            status=str(raw.get("status", "candidate")),
        )
        records.append(record)
        aliases[key.lower()] = record
        if doi := raw.get("doi"):
            aliases[f"doi:{doi}".lower()] = record
        if arxiv := raw.get("arxiv_id"):
            aliases[f"arxiv:{arxiv}".lower()] = record
    return Corpus(path, tuple(records), aliases)


def corpus_of(meta: Meta) -> Corpus | None:
    return load_corpus(Path(meta.corpus)) if meta.corpus else None
