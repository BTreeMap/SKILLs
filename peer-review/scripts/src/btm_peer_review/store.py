"""Session filesystem: meta, ledger, paper text, and the linked corpus."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from btm_corekit import (
    CommandError,
    EventLog,
    SessionStore,
    is_digits,
    now_iso,
    parse_enum,
    read_jsonl,
    require,
)
from btm_peer_review.constants import Level

STORE = SessionStore("peer-review", marker="session.json", hint="run init first")
LIT_STORE = SessionStore(
    "lit-review", marker="protocol.json", hint="run lit-review init first"
)
LEDGER = "ledger.jsonl"
DATE_WIDTHS = (4, 2, 2)  # YYYY, MM, DD
PAPER = "paper.txt"


def event_log(directory: Path) -> EventLog:
    return EventLog(directory / LEDGER, STORE.hint)


def paper_path(directory: Path) -> Path:
    return directory / PAPER


def year_of(date: str) -> int:
    """YYYY, YYYY-MM, or YYYY-MM-DD; the year, or the invariant it broke."""
    parts = date.split("-")
    widths = DATE_WIDTHS[: len(parts)]
    require(
        1 <= len(parts) <= len(DATE_WIDTHS)
        and all(
            is_digits(part) and len(part) == width
            for part, width in zip(parts, widths, strict=True)
        ),
        "date is YYYY, YYYY-MM, or YYYY-MM-DD",
    )
    return int(parts[0])


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
    path = STORE.meta_path(directory)
    raw = STORE.read_meta(directory)
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
    STORE.write_meta(directory, meta.view())
    event_log(directory).touch()


def update_meta(directory: Path, meta: Meta, **changes: Any) -> Meta:
    updated = replace(meta, **changes)
    write_meta(directory, updated)
    return updated


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
