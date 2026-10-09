"""One citable record per reference: the lit-review corpus read as Works,
then the index registry, in the one order every member's `cite` shares.

The corpus is another member's file, so this module reads only the fields
`Work` shares with lit-review's `Paper` and ignores the rest. Reading it is
O(rows); a lookup in it is one dict probe, so the corpus answers before
any request is spent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import ConfigDict

from btm_corekit.indexes.registry import INDEXES, lookup
from btm_corekit.indexes.work import (
    ByArxiv,
    ByDoi,
    Citation,
    MaybeArxivId,
    MaybeCount,
    MaybeDoi,
    MaybeYear,
    Work,
    normalize_arxiv_id,
    normalize_doi,
)
from btm_corekit.records.models import Model, NonEmpty, parse_model
from btm_corekit.report.channels import signal
from btm_corekit.report.errors import CommandError, UpstreamError
from btm_corekit.store.clock import now_iso
from btm_corekit.store.fsio import read_jsonl
from btm_corekit.store.sessions import (
    LIT_REVIEW_CORPUS,
    LIT_REVIEW_SESSIONS,
    Connection,
)

CITE_CAP_BYTES = 16 * 1024 * 1024
"""One record is kilobytes; the cap bounds a stall, as in lit-review."""

ORDER: Mapping[type[ByDoi] | type[ByArxiv], tuple[str, ...]] = {
    ByDoi: ("openalex", "semanticscholar", "crossref"),
    ByArxiv: ("arxiv",),
}
"""The indexes asked for each identifier kind, first answer wins."""


class Shelved(Model):
    """One `papers.jsonl` row as a `Work`. lit-review owns the file and writes
    its review state beside these fields, so extras are ignored; a row
    without a key is a corrupt corpus, refused by name."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    key: NonEmpty
    title: str | None = None
    authors: tuple[str, ...] = ()
    year: MaybeYear = None
    venue: str | None = None
    doi: MaybeDoi = None
    arxiv_id: MaybeArxivId = None
    openalex_id: str | None = None
    cited_by_count: MaybeCount = None
    abstract: str | None = None
    pdf_url: str | None = None
    landing_url: str | None = None

    def work(self) -> Work:
        """Every `Work` field named, so a field added there is a type error
        here; `Paper` keeps no publication date."""
        return Work(
            title=self.title,
            authors=self.authors,
            year=self.year,
            venue=self.venue,
            doi=self.doi,
            arxiv_id=self.arxiv_id,
            openalex_id=self.openalex_id,
            cited_by=self.cited_by_count,
            abstract=self.abstract,
            pdf_url=self.pdf_url,
            landing_url=self.landing_url,
            published=None,
        )


@dataclass(frozen=True, slots=True)
class Shelf:
    """A lit-review corpus read whole: works by key, every alias to its key,
    and the date the file last changed, which is when its records stood."""

    path: Path
    works: Mapping[str, Work]
    aliases: Mapping[str, str]
    as_of: str

    @property
    def name(self) -> str:
        """The corpus session: the directory holding the file."""
        return self.path.parent.name

    def find(self, ref: str) -> str | None:
        """The key a corpus key, DOI, or arXiv id names, in any case or
        spelling the normalizers accept; None where the corpus lacks it."""
        given = ref.strip()
        if given in self.works:
            return given
        candidates = (
            given.lower(),
            f"doi:{normalize_doi(given)}",
            f"arxiv:{normalize_arxiv_id(given)}",
        )
        return next((self.aliases[c] for c in candidates if c in self.aliases), None)


def read_shelf(path: Path) -> Shelf:
    """The corpus at `path` (a `papers.jsonl`); O(rows)."""
    if not path.is_file():
        raise CommandError(f"no corpus at {path}: name a lit-review session")
    rows = [
        parse_model(Shelved, raw, f"{path}: corpus record") for raw in read_jsonl(path)
    ]
    aliases: dict[str, str] = {}
    for row in rows:
        aliases[row.key.lower()] = row.key
        if row.doi:
            aliases[f"doi:{row.doi}"] = row.key
        if row.arxiv_id:
            aliases[f"arxiv:{row.arxiv_id}"] = row.key
    changed = datetime.fromtimestamp(path.stat().st_mtime, UTC).date().isoformat()
    return Shelf(path, {row.key: row.work() for row in rows}, aliases, changed)


def corpus_path(ref: str) -> Path:
    """The `papers.jsonl` a lit-review session id or directory names."""
    return LIT_REVIEW_SESSIONS.dir_of(ref) / LIT_REVIEW_CORPUS


def corpus_connection(path: Path) -> Connection:
    """The connection a session records to the lit-review session holding `path`."""
    session = path.parent
    return Connection(
        skill=LIT_REVIEW_SESSIONS.skill, session=session.name, path=str(session)
    )


def parsed_ref(raw: str) -> ByDoi | ByArxiv | None:
    """A DOI before an arXiv id: arXiv's own DOI names the paper either way."""
    if doi := normalize_doi(raw):
        return ByDoi(doi)
    if arxiv_id := normalize_arxiv_id(raw):
        return ByArxiv(arxiv_id)
    return None


def cited(work: Work, key: str | None, source: str, retrieved: str) -> Citation:
    return Citation.model_validate(
        {**work.model_dump(), "key": key, "source": source, "retrieved": retrieved}
    )


def cite(raw: str, shelf: Shelf | None, client: httpx.Client) -> Citation:
    """The corpus first, then each index the identifier's kind names. A miss
    everywhere is exit 1; a miss where some index failed upstream is exit 2,
    since a retry may reach it."""
    if shelf is not None and (key := shelf.find(raw)) is not None:
        return cited(shelf.works[key], key, shelf.name, shelf.as_of)
    ref = parsed_ref(raw)
    if ref is None:
        held = f" and corpus {shelf.name} holds no such key" if shelf else ""
        raise CommandError(f"{raw!r} is no DOI or arXiv id{held}")
    if shelf is not None:
        signal(f"corpus {shelf.name} lacks {raw}; asking the indexes")
    failed: list[str] = []
    for name in ORDER[type(ref)]:
        try:
            work = lookup(INDEXES[name], client, CITE_CAP_BYTES, ref)
        except UpstreamError as err:
            failed.append(f"{name}: {err}")
            continue
        if work is not None:
            return cited(work, None, name, now_iso()[:10])
    asked = ", ".join(ORDER[type(ref)])
    if failed:
        raise UpstreamError(f"{raw} unresolved; failed upstream: {'; '.join(failed)}")
    raise CommandError(f"no record for {raw} in {asked}; check the identifier")
