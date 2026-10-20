"""The raw store: immutable parquet files under `data/raw/<source>/`, listed
with their sha256 in `data/manifest.json`; every read re-hashes the bytes.

A mismatch or a missing file appends one incident line and raises: exit 1
naming the file, which stays in place for the operator to judge.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field

from btm_corekit import (
    CommandError,
    Model,
    dump,
    make_id,
    now_iso,
    parse_model,
    write_atomic,
)
from btm_finance.data.tables import (
    SCHEMAS,
    Bars,
    EventRows,
    Loaded,
    Source,
    Table,
    date_of,
)
from btm_finance.ledger import Kind
from btm_finance.store import Book, append_chained

MANIFEST = Path("data", "manifest.json")
RAW = Path("data", "raw")
HISTORY_YEARS = 25
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Entry(Model):
    """One stored file; `through` is the last date its rows cover."""

    path: str
    sha256: Sha256
    rows: Annotated[int, Field(ge=1)]
    source: Source
    table: Table
    loaded_at: str
    since: date
    through: date


class Manifest(Model):
    files: tuple[Entry, ...] = ()


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def data_snapshot(manifest: Manifest) -> str:
    """sha256 over the sorted file digests, one per line: names and order of
    loads do not move it; any byte of any file does."""
    lines = "\n".join(sorted(entry.sha256 for entry in manifest.files))
    return sha256_of(lines.encode("ascii"))


def default_since(manifest: Manifest, source: Source, today: date) -> date:
    """The day after the source's last covered date, else 25 years back."""
    covered = [entry.through for entry in manifest.files if entry.source == source]
    if covered:
        return max(covered) + timedelta(days=1)
    try:
        return today.replace(year=today.year - HISTORY_YEARS)
    except ValueError:  # 29 February in a year that lacks it
        return today.replace(year=today.year - HISTORY_YEARS, day=28)


def stem_for(taken: Iterable[str], day: date) -> str:
    """`<day>`, else the first free `<day>-<n>` from 2: never a stored name."""
    used = set(taken)
    stem, number = day.isoformat(), 2
    while stem in used:
        stem, number = f"{day.isoformat()}-{number}", number + 1
    return stem


def stem_of(path: str) -> str:
    return Path(path).name.split(".", 1)[0]


def read_manifest(book: Book) -> Manifest:
    path = book.root / MANIFEST
    if not path.is_file():
        return Manifest()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise CommandError(f"unreadable {path}: {err}") from err
    return parse_model(Manifest, raw, str(path))


def incident(book: Book, entry: Entry, problem: str, found: str | None) -> None:
    record = {
        "id": make_id(["integrity", stem_of(entry.path)]),
        "ts": now_iso(),
        "kind": "integrity",
        "file": entry.path,
        "problem": problem,
        "expected": entry.sha256,
        "found": found,
    }
    append_chained(book.path_of(Kind.INCIDENT), [record])


def verified_bytes(book: Book, entry: Entry) -> bytes:
    """The file's bytes when their sha256 matches the manifest."""
    path = book.root / entry.path
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        problem = "listed in data/manifest.json but missing on disk"
        incident(book, entry, problem, None)
        raise CommandError(
            f"{entry.path} {problem}; incident logged; restore it from backup"
        ) from None
    found = sha256_of(data)
    if found != entry.sha256:
        problem = "sha256 differs from data/manifest.json"
        incident(book, entry, problem, found)
        raise CommandError(
            f"{entry.path} {problem}; incident logged; file left in place: "
            "restore it from backup"
        )
    return data


def read_entry(book: Book, entry: Entry) -> pa.Table:
    table = pq.read_table(pa.BufferReader(verified_bytes(book, entry)))
    if not table.schema.equals(SCHEMAS[entry.table]):
        raise CommandError(f"{entry.path} holds no {entry.table.value} schema")
    return table


def verify_all(book: Book, manifest: Manifest) -> int:
    """Re-hash every listed file. O(store bytes)."""
    for entry in manifest.files:
        verified_bytes(book, entry)
    return len(manifest.files)


@dataclass(frozen=True, slots=True)
class Stored:
    """Every verified table of one kind, with its load rank: higher is later."""

    bars: list[tuple[int, Bars]]
    events: list[tuple[int, EventRows]]


def load_order(manifest: Manifest) -> list[Entry]:
    """Entries by `loaded_at`, manifest position breaking ties."""
    ranked = sorted(enumerate(manifest.files), key=lambda pair: pair[1].loaded_at)
    return [entry for _, entry in ranked]


def read_store(book: Book, manifest: Manifest) -> Stored:
    bars: list[tuple[int, Bars]] = []
    events: list[tuple[int, EventRows]] = []
    for rank, entry in enumerate(load_order(manifest)):
        table = read_entry(book, entry)
        match entry.table:
            case Table.BARS:
                bars.append((rank, Bars.of(table)))
            case Table.EVENTS:
                events.append((rank, EventRows.of(table)))
    return Stored(bars, events)


def parquet_bytes(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return bytes(sink.getvalue().to_pybytes())


def write_new_file(path: Path, data: bytes) -> None:
    """Create-only: an existing file is never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def tables_of(loaded: Loaded) -> list[tuple[Table, pa.Table, date]]:
    """Each non-empty table with the last date it covers."""
    found: list[tuple[Table, pa.Table, date]] = []
    if loaded.bars is not None and len(loaded.bars):
        last = date_of(int(loaded.bars.date.max()))
        found.append((Table.BARS, loaded.bars.arrow(), last))
    if loaded.events is not None and len(loaded.events):
        last = date_of(int(loaded.events.knowledge_time.max()))
        found.append((Table.EVENTS, loaded.events.arrow(), last))
    return found


def store(  # noqa: PLR0913 - the book, its manifest, and one load's facts
    book: Book,
    manifest: Manifest,
    source: Source,
    loaded: Loaded,
    *,
    since: date,
    today: date,
) -> tuple[Manifest, Sequence[Entry]]:
    """Write each non-empty table as a new file, then the manifest listing it.
    A same-day reload takes the next numbered stem."""
    directory = book.root / RAW / source.value
    taken = [stem_of(entry.path) for entry in manifest.files if entry.source == source]
    if directory.is_dir():
        taken += [stem_of(path.name) for path in directory.iterdir()]
    stem = stem_for(taken, today)
    stamp = now_iso()
    added: list[Entry] = []
    for table, data, last in tables_of(loaded):
        payload = parquet_bytes(data)
        path = directory / f"{stem}.{table.value}.parquet"
        write_new_file(path, payload)
        added.append(
            Entry(
                path=book.relative(path),
                sha256=sha256_of(payload),
                rows=data.num_rows,
                source=source,
                table=table,
                loaded_at=stamp,
                since=since,
                through=last,
            )
        )
    if not added:
        return manifest, added
    updated = Manifest(files=(*manifest.files, *added))
    write_atomic(book.root / MANIFEST, json.dumps(dump(updated), indent=2) + "\n")
    return updated, added
