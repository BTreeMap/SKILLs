"""Session filesystem: meta, ledger, paper text, and the linked corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, ConfigDict

from btm_corekit import (
    CommandError,
    Count,
    Doi,
    EventLog,
    Model,
    NonEmpty,
    SessionStore,
    parse_model,
    read_jsonl,
)
from btm_peer_review.constants import Level

STORE = SessionStore("peer-review", marker="session.json", hint="run init first")
LIT_STORE = SessionStore(
    "lit-review", marker="protocol.json", hint="run lit-review init first"
)
LEDGER = "ledger.jsonl"
PAPER = "paper.txt"

_DATE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")


def _dated(value: str) -> str:
    if not _DATE.fullmatch(value):
        raise ValueError("write the date as YYYY, YYYY-MM, or YYYY-MM-DD")
    return value


Date = Annotated[str, AfterValidator(_dated)]
"""The version of the paper reviewed. One quantifier per class, so the
backtracking engine stays linear."""


def event_log(directory: Path) -> EventLog:
    return EventLog(directory / LEDGER, STORE.hint)


def paper_path(directory: Path) -> Path:
    return directory / PAPER


class Meta(Model):
    """Session facts fixed at init, extended by ingest and link."""

    title: NonEmpty
    date: Date
    level: Level
    created: str = ""
    corpus: str | None = None
    pages: Count = 0

    @property
    def year(self) -> int:
        """The pattern has already proved the leading four digits."""
        return int(self.date[:4])


def read_meta(directory: Path) -> Meta:
    return STORE.read_meta(directory, Meta)


def write_meta(directory: Path, meta: Meta) -> None:
    STORE.write_meta(directory, meta)
    event_log(directory).touch()


def update_meta(directory: Path, meta: Meta, **changes: object) -> Meta:
    """Edits go through the validators; `model_copy` would skip them."""
    updated = meta.with_(**changes)
    write_meta(directory, updated)
    return updated


class Record(Model):
    """One linked corpus paper, as prior work may cite it. Another skill owns
    the file and writes a dozen more fields, so extras are ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    key: NonEmpty
    year: int | None = None
    title: str = ""
    status: str = "candidate"
    doi: Doi | None = None
    arxiv_id: str | None = None


@dataclass(frozen=True, slots=True)
class Corpus:
    """The linked lit-review corpus: its records, indexed by every alias."""

    path: Path
    records: tuple[Record, ...]
    aliases: dict[str, Record]

    def lookup(self, ref: str) -> Record | None:
        return self.aliases.get(ref.strip().lower())


def load_corpus(path: Path) -> Corpus:
    """Another skill owns this file, so it is decoded, not assumed. Fields
    beyond the four this review reads are ignored."""
    if not path.is_file():
        raise CommandError(f"no corpus at {path}: link a lit-review session")
    records = [
        parse_model(Record, raw, f"{path}: corpus record") for raw in read_jsonl(path)
    ]
    aliases: dict[str, Record] = {}
    for record in records:
        aliases[record.key.lower()] = record
        if record.doi:
            aliases[f"doi:{record.doi}".lower()] = record
        if record.arxiv_id:
            aliases[f"arxiv:{record.arxiv_id}".lower()] = record
    return Corpus(path, tuple(records), aliases)


def corpus_of(meta: Meta) -> Corpus | None:
    return load_corpus(Path(meta.corpus)) if meta.corpus else None
