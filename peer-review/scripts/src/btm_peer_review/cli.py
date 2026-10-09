"""Argument surface and the process boundary."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, TypedDict

import btm_peer_review
from btm_corekit import (
    BATCH,
    JSON,
    LIT_REVIEW_CORPUS,
    LIT_REVIEW_SESSIONS,
    PAD_SCHEMA,
    REFS_SCHEMA,
    EventLog,
    Model,
    NonEmpty,
    Parser,
    Required,
    add_slot,
    content,
    corpus_link,
    dump,
    emit,
    gated,
    mint,
    now_iso,
    pad_ids,
    parse_model,
    require,
    run_cli,
    signal,
    text,
    wire_cite,
    wire_clean,
    wire_pad,
    wire_project,
    write_atomic,
)
from btm_peer_review.batch import BATCH_KEYS, SCHEMA, Context, NoteResult, expand_batch
from btm_peer_review.constants import BANKS, LEVEL_BANKS, Level, Severity, Standing
from btm_peer_review.ledger import replay
from btm_peer_review.state import Ledger
from btm_peer_review.store import (
    LEDGER,
    PAPER_TEXT,
    STORE,
    Meta,
    corpus_of,
    load_corpus,
)
from btm_peer_review.text import PaperText, parse_pages
from btm_peer_review.views import (
    ClaimView,
    Coverage,
    ObjectionView,
    cite_check,
    claim_views,
    coverage,
    echo_ratio,
    objection_views,
    recommendation,
    scaffold,
)

PAPER = Required("paper", inline=False)
EXTRACTION = Required("extraction", inline=False)
DRAFT = Required("draft", inline=False)


class Reviewed(Model):
    """The paper under review. A title carries colons, quotes and dashes, so
    it arrives as content rather than through argv."""

    title: NonEmpty


def cmd_init(args: argparse.Namespace) -> int:
    paper = content(Reviewed, PAPER, args)
    meta = parse_model(
        Meta,
        {
            "title": paper.title,
            "date": args.date,
            "level": args.level,
            "created": now_iso(),
            "project": args.project,
        },
        "the session",
    )
    made = STORE.create(args.session)
    STORE.write_meta(made.directory, meta)
    EventLog(made.directory / LEDGER).touch()
    emit(
        {
            "session": made.name,
            "dir": str(made.directory),
            **dump(meta),
            "next": "ingest the paper text",
        }
    )
    return 0


def _session(ref: str) -> tuple[Path, Meta]:
    directory = STORE.directory(ref)
    return directory, STORE.read_meta(directory, Meta)


def _paper(directory: Path) -> PaperText | None:
    path = directory / PAPER_TEXT
    return PaperText.from_file(path) if path.is_file() else None


def cmd_ingest(args: argparse.Namespace) -> int:
    directory, meta = _session(args.session)
    raw = text(EXTRACTION, args)
    pages = parse_pages(raw)
    require(any(body.strip() for _, body in pages), "the extraction holds no text")
    if len(pages) == 1 and "## PDF page" not in raw:
        signal("no page markers: the whole text counts as page 1")
    previously = (directory / PAPER_TEXT).is_file()
    write_atomic(directory / PAPER_TEXT, raw)
    paper = PaperText(pages)
    if previously:
        signal("paper text replaced; every standing re-derives against it")
    if paper.author_block():
        signal("page 1 carries an author block; the review names no author")
    if paper.limitations is None:
        signal("no Limitations heading found; the echo ratio stays unavailable")
    empty = [n for n, body in pages if not body.strip()]
    if empty:
        signal(f"{len(empty)} page(s) without text: {empty[:10]}")
    STORE.write_meta(directory, meta.with_(pages=len(pages)))
    emit(
        {
            "session": directory.name,
            "pages": len(pages),
            "limitations_section": paper.limitations is not None,
            "next": "note claims from abstract, introduction, and conclusion",
        }
    )
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    directory, meta = _session(args.session)
    papers = LIT_REVIEW_SESSIONS.dir_of(args.corpus) / LIT_REVIEW_CORPUS
    corpus = load_corpus(papers)
    linked = meta.with_(corpus=str(papers)).with_link(corpus_link(papers))
    STORE.write_meta(directory, linked)
    later = sum(1 for r in corpus.records if r.year is not None and r.year > meta.year)
    emit(
        {
            "session": directory.name,
            "corpus": str(papers),
            "records": len(corpus.records),
            "undated": sum(1 for r in corpus.records if r.year is None),
            "postdating": later,
        }
    )
    if later:
        signal(
            f"{later} corpus record(s) postdate the paper; they cannot serve as prior"
        )
    return 0


def linked_corpus(session: str) -> Path | None:
    _, meta = _session(session)
    return Path(meta.corpus) if meta.corpus else None


def cmd_note(args: argparse.Namespace) -> int:
    directory, meta = _session(args.session)
    log = EventLog(directory / LEDGER)
    events = log.read()
    ledger = replay(events)
    context = Context(_paper(directory), corpus_of(meta), meta.year)

    def expand(batch: dict[str, Any]) -> NoteResult:
        return expand_batch(ledger, batch, context, mint, pad_ids(directory))

    def commit(result: NoteResult) -> dict[str, JSON]:
        log.append(result.events, held=len(events))
        return {
            "session": directory.name,
            "admitted": dict(Counter(event["e"] for event in result.events)),
            "minted": result.minted,
            "claims": len(ledger.claim_order),
            "objections": len(ledger.objection_order),
            "walked": sorted(ledger.walks),
        }

    return gated(BATCH, args, "ledger", expand, commit)


class Review(TypedDict):
    """The check envelope. A TypedDict rather than the channel's JSON type
    because callers index it: cite-check reads `claims` and `objections`
    back out, so the shape has to survive the return."""

    session: str
    title: str
    date: str
    coverage: Coverage
    recommendation: dict[str, JSON]
    echo: dict[str, JSON]
    claims: list[ClaimView]
    objections: list[ObjectionView]
    scaffold: dict[str, JSON]


def _derive(directory: Path, meta: Meta) -> Review:
    ledger = replay(EventLog(directory / LEDGER).read())
    paper = _paper(directory)
    corpus = corpus_of(meta)
    objections = objection_views(ledger, paper, corpus, meta.year)
    claims = claim_views(ledger, paper, objections)
    return {
        "session": directory.name,
        "title": meta.title,
        "date": meta.date,
        "coverage": coverage(ledger, meta.level, corpus, paper),
        "recommendation": recommendation(objections),
        "echo": echo_ratio(objections, paper),
        "claims": claims,
        "objections": objections,
        "scaffold": scaffold(claims, objections),
    }


def cmd_check(args: argparse.Namespace) -> int:
    directory, meta = _session(args.session)
    document = _derive(directory, meta)
    cov = document["coverage"]
    if cov["unwalked"]:
        signal(
            f"banks not yet walked at level {cov['level']}: "
            f"{', '.join(cov['unwalked'])}"
        )
    if document["echo"].get("warn"):
        signal(
            f"echo ratio {document['echo']['ratio']}: most objections restate the "
            "authors' own Limitations; hunt outside it"
        )
    broken = [
        str(v["marker"])
        for v in document["objections"]
        if v["standing"] in (Standing.UNANCHORED, Standing.UNDATED)
    ]
    if broken:
        signal(f"{len(broken)} objection(s) lost their grounding: {', '.join(broken)}")
    emit(document)
    return 0


def next_step(meta: Meta, ledger: Ledger) -> str:
    """The cheapest legal next action, derived from live ledger state.

    Advisory only: the script owes the arithmetic over banks, claims, and
    standings that the agent would otherwise redo by hand."""
    if not meta.pages:
        return "ingest the paper text"
    if not ledger.claim_order:
        return "note the contribution claims verbatim"
    unwalked = sorted(set(LEVEL_BANKS[meta.level]) - set(ledger.walks))
    if unwalked:
        return f"walk the remaining banks: {' '.join(unwalked)}"
    if not ledger.objections:
        return "no objection stands; check, then draft the recommendation"
    return "check, then draft from the scaffold and cite-check it"


def cmd_status(args: argparse.Namespace) -> int:
    directory, meta = _session(args.session)
    ledger = replay(EventLog(directory / LEDGER).read())
    emit(
        {
            "session": directory.name,
            "title": meta.title,
            "project": meta.project,
            "links": [dump(link) for link in meta.links],
            "level": meta.level,
            "pages": meta.pages,
            "corpus": meta.corpus,
            "claims": len(ledger.claim_order),
            "objections": Counter(o.severity for o in ledger.objections.values()),
            "withdrawn": len(ledger.withdrawn),
            "walked": sorted(ledger.walks),
            "next": next_step(meta, ledger),
        }
    )
    return 0


def cmd_cite_check(args: argparse.Namespace) -> int:
    directory, meta = _session(args.session)
    draft = text(DRAFT, args)
    document = _derive(directory, meta)
    report = cite_check(draft, document["claims"], document["objections"])
    report["recommendation"] = document["recommendation"]
    emit(report)
    if report["problems"]:
        signal(f"{len(report['problems'])} marker problem(s); fix the draft")
        return 1
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    emit(
        {
            "note_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
            "order": "claims, objections, walks, withdraws; later entries may "
            "reference ids minted earlier in the same batch",
            "banks": {bank: list(kinds) for bank, kinds in BANKS.items()},
            "severities": list(Severity),
            "levels": list(Level),
            "refs": REFS_SCHEMA,
            "pad": PAD_SCHEMA,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_peer_review.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="mint a session for one paper")
    init.set_defaults(func=cmd_init)
    init.add_argument("session", help="two or three keywords, or a directory path")
    add_slot(init, PAPER, '{"title": "the paper under review"}')
    init.add_argument(
        "--date", required=True, help="YYYY[-MM[-DD]] of the version reviewed"
    )
    init.add_argument("--level", type=Level, choices=list(Level), default=Level.FULL)
    wire_project(init)
    ingest = commands.add_parser("ingest", help="store the paper's extracted text")
    ingest.set_defaults(func=cmd_ingest)
    ingest.add_argument("session")
    add_slot(ingest, EXTRACTION, "a read-pdf extraction with page markers")
    link = commands.add_parser("link", help="attach a lit-review corpus as prior work")
    link.set_defaults(func=cmd_link)
    link.add_argument("session")
    link.add_argument("--corpus", required=True, help="lit-review session id or path")
    note = commands.add_parser("note", help="admit one JSON batch")
    note.set_defaults(func=cmd_note)
    note.add_argument("session")
    add_slot(note, BATCH, "claims, objections, walks, withdraws")
    check = commands.add_parser(
        "check", help="derive standings and the report scaffold"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("session")
    status = commands.add_parser(
        "status", help="ledger counts, banks walked, and the next step"
    )
    status.set_defaults(func=cmd_status)
    status.add_argument("session")
    cite = commands.add_parser(
        "cite-check", help="markers in a draft against the ledger"
    )
    cite.set_defaults(func=cmd_cite_check)
    cite.add_argument("session")
    add_slot(cite, DRAFT, "the draft's Markdown")
    schema = commands.add_parser("schema", help="print the note batch shape")
    schema.set_defaults(func=cmd_schema)
    wire_pad(commands, STORE)
    wire_cite(commands, STORE.skill, linked_corpus)
    wire_clean(commands, STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run_cli(build_parser(), argv)
