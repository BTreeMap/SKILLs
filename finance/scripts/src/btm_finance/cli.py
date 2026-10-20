"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import secrets
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TypeVar

import numpy as np
import pyarrow as pa
from pydantic import BaseModel

import btm_finance
from btm_corekit import (
    BATCH,
    PAD_SCHEMA,
    REFS_SCHEMA,
    CommandError,
    Optional,
    Parser,
    add_slot,
    ascii_words,
    count_lines,
    dispatch,
    dump,
    emit,
    gated,
    make_id,
    now_iso,
    parse_model,
    run_cli,
    signal,
    text,
    wire_pad,
    write_atomic,
)
from btm_finance.batch import BATCH_KEYS, SCHEMA, Context, RecordResult, expand_batch
from btm_finance.data.assemble import UNIVERSE as UNIVERSE_FILE
from btm_finance.data.assemble import assemble, parse_universe
from btm_finance.data.raw import (
    Manifest,
    data_snapshot,
    default_since,
    read_manifest,
    read_returns,
    returns_path,
    store,
    verify_all,
    write_returns,
)
from btm_finance.data.sources import csv, edgar, french, tiingo
from btm_finance.data.tables import Loaded, Source, Table, date_of, day_of
from btm_finance.engine.metrics import PERIODS_PER_YEAR
from btm_finance.ledger import (
    ENVELOPE,
    Break,
    Kind,
    Numbered,
    Row,
    audit,
    current,
    dangling,
    rows_of,
)
from btm_finance.models import (
    BASELINE_HYPOTHESIS,
    Exclusions,
    Status,
    StrategyConfig,
)
from btm_finance.scaffold import member, scaffold
from btm_finance.scorecard import RunLine, Span
from btm_finance.scoring import Peers, Setting, bounds, evaluate, rules_of
from btm_finance.standing import Evidence, standing_of
from btm_finance.store import (
    PAD,
    PAD_DIR,
    Book,
    append_chained,
    held_out_list,
    ledger_files,
    load_limits,
    load_preferences,
    open_book,
    proposal_dates,
    read_bytes,
    read_json,
    run_files,
    strategies,
)
from btm_finance.views import (
    by_status,
    families,
    next_step,
    open_hypotheses,
    open_proposals,
)
from btm_finance.whitelist import load_signal

UNIVERSE = Optional("universe", inline=False)
CONFIG = Optional("config", inline=False)
LATER: dict[str, str] = {
    "advise": "stage 4",
}
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
INCIDENT_TAIL = 10
M = TypeVar("M", bound=BaseModel)


def positive(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a whole number") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"{value} is no asset cap; pass 1 or more")
    return value


def start(root: Path, cap: int, universe: str | None) -> dict[str, Any]:
    """Make the book, then register the baseline hypothesis through the gate."""
    receipt = scaffold(root, cap, universe)
    book = open_book(str(root))
    limits = load_limits(book)
    context = Context(
        families=frozenset(limits.families),
        min_holding_days=limits.min_holding_days,
        ids={},
        strategies=["baseline"],
        proposals=[],
    )
    batch = {"hypotheses": [BASELINE_HYPOTHESIS]}
    result = expand_batch(context, batch, make_id, now_iso())
    if result.problems:
        raise CommandError(f"baseline hypothesis refused: {result.problems}")
    append_chained(book.path_of(Kind.HYPOTHESIS), result.staged[Kind.HYPOTHESIS])
    receipt["wrote"].append("ledger/hypotheses.jsonl")
    receipt["new"] = result.new["hypotheses"]
    return receipt


def cmd_start(args: argparse.Namespace) -> int:
    emit(start(Path(args.book).expanduser(), args.cap, text(UNIVERSE, args)))
    return 0


def ids_of(path: Path, key: str = "id") -> list[str]:
    return [
        row[key]
        for _, row in rows_of(read_bytes(path))
        if isinstance(row.get(key), str)
    ]


def run_ids(book: Book) -> list[str]:
    return [run_id for path in run_files(book) for run_id in ids_of(path, "run_id")]


def cmd_record(args: argparse.Namespace) -> int:
    book = open_book(args.book)
    limits = load_limits(book)
    kinds = (Kind.HYPOTHESIS, Kind.CRITIQUE, Kind.DECISION, Kind.FILL)
    ids = {kind: ids_of(book.path_of(kind)) for kind in kinds}
    context = Context(
        families=frozenset(limits.families),
        min_holding_days=limits.min_holding_days,
        ids={**ids, Kind.RUN: run_ids(book)},
        strategies=[strategy.name for strategy in strategies(book)],
        proposals=proposal_dates(book),
    )

    def expand(batch: dict[str, Any]) -> RecordResult:
        return expand_batch(context, batch, make_id, now_iso())

    def commit(result: RecordResult) -> dict[str, Any]:
        accepted: dict[str, int] = {}
        for kind, rows in sorted(result.staged.items()):
            append_chained(book.path_of(kind), rows)
            accepted[kind.value] = len(rows)
        document: dict[str, Any] = {"book": book.meta.id, "accepted": accepted}
        if result.preferences is not None:
            write_atomic(
                book.root / "preferences.json",
                json.dumps(dump(result.preferences), indent=2) + "\n",
            )
            document["preferences"] = "rewritten"
        document["new"] = result.new
        document["next"] = "run check for the continue view"
        return document

    return gated(BATCH, args, "book", expand, commit)


def cmd_check(args: argparse.Namespace) -> int:
    if args.live:
        raise CommandError("check --live arrives in stage 5; not available yet")
    book = open_book(args.book)
    if args.target is None:
        emit(continue_view(book))
        return 0
    try:
        date.fromisoformat(args.target)
    except ValueError:
        emit(standing_view(book, args.target).model_dump(mode="json"))
        return 0
    raise CommandError(
        f"check {args.target}: a proposal arrives in stage 4; check a strategy "
        "or run id today"
    )


def kind_rows(book: Book, kind: Kind) -> list[Numbered]:
    return rows_of(read_bytes(book.path_of(kind)))


def all_runs(book: Book) -> list[Row]:
    """Live run lines of every runs file, oldest first by `ts`."""
    rows = [
        row for path in run_files(book) for row in current(rows_of(read_bytes(path)))
    ]
    return sorted(rows, key=lambda row: str(row.get("ts", "")))


def hypothesis_for(book: Book, run: Row | None, strategy: str) -> Row | None:
    """The run's hypothesis, its newest correction winning; with no run, the
    newest live hypothesis naming the strategy."""
    rows = kind_rows(book, Kind.HYPOTHESIS)
    live = current(rows)
    if run is None:
        named = [row for row in live if row.get("strategy") == strategy]
        return named[-1] if named else None
    wanted = run.get("hypothesis_id")
    corrected = [row for row in live if row.get("supersedes") == wanted]
    if corrected:
        return corrected[-1]
    return next((row for _, row in rows if row.get("id") == wanted), None)


def standing_view(book: Book, target: str) -> BaseModel:
    """`check <strategy>` or `check <run id>`: standing of the newest scored
    research run, or of the named run."""
    runs = all_runs(book)
    named = {str(row.get("run_id")): row for row in runs}
    listed = {s.name: s for s in strategies(book)}
    if target in named:
        run: Row | None = named[target]
        strategy = str(named[target].get("strategy"))
    elif target in listed:
        strategy = target
        own = [r for r in runs if r.get("strategy") == target and not r.get("held_out")]
        run = own[-1] if own else None
    else:
        raise CommandError(f"no strategy or run named {target!r} in the book")
    critiques = [
        row
        for row in current(kind_rows(book, Kind.CRITIQUE))
        if run is not None and row.get("run_id") == run.get("run_id")
    ]
    found = listed.get(strategy)
    evidence = Evidence(
        strategy=strategy,
        run=run,
        hypothesis=hypothesis_for(book, run, strategy),
        critique=critiques[-1] if critiques else None,
        decisions=current(kind_rows(book, Kind.DECISION)),
        status=found.status if found else None,
        raw_status=found.raw if found else "",
        today=datetime.now(UTC).date(),
    )
    return standing_of(evidence, load_limits(book))


def continue_view(book: Book) -> dict[str, Any]:
    """Every ledger file audited and replayed once: O(ledger bytes)."""
    limits = load_limits(book)
    breaks: list[Break] = []
    lines = 0
    rows: dict[str, list[Numbered]] = {}
    for path in ledger_files(book):
        name = book.relative(path)
        data = read_bytes(path)
        breaks += audit(name, data)
        rows[name] = rows_of(data)
        breaks += dangling(name, rows[name])
        lines += len(rows[name])

    def live(kind: Kind) -> list[dict[str, Any]]:
        return current(rows.get(f"ledger/{kind.file}", []))

    runs = [
        row
        for path in run_files(book)
        for row in current(rows.get(book.relative(path), []))
    ]
    hypotheses, decisions = live(Kind.HYPOTHESIS), live(Kind.DECISION)
    listed = strategies(book)
    known = {s.name: s.status for s in listed if s.status is not None}
    unknown = [
        {"strategy": s.name, "status": s.raw} for s in listed if s.status is None
    ]
    for entry in unknown:
        signal(
            f"strategies/{entry['strategy']}/status reads {entry['status']!r}, "
            f"not one of {'|'.join(Status)}"
        )
    if breaks:
        signal(f"{len(breaks)} ledger break(s); details under incidents.ledger")
    today = datetime.now(UTC).date()
    proposals = open_proposals(proposal_dates(book), decisions, today)
    pending = len(open_hypotheses(hypotheses, runs, decisions))
    return {
        "book": book.meta.id,
        "as_of": now_iso(),
        "strategies": {**by_status(known), "unknown": unknown},
        "families": families(limits, hypotheses, runs, decisions),
        "proposals": proposals,
        "incidents": {
            "ledger": [found.view() for found in breaks],
            "logged": live(Kind.INCIDENT)[-INCIDENT_TAIL:],
        },
        "chain": {"files": len(rows), "lines": lines, "breaks": len(breaks)},
        "pad": {"entries": count_lines(book.root / PAD_DIR / "scratch.jsonl")},
        "next": next_step(breaks, hypotheses, pending, proposals),
    }


def iso_day(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is no YYYY-MM-DD date") from None


def config_of(model: type[M], raw: str | None) -> M:
    """The `--config` slot as the source's settings; absent is all defaults."""
    if raw is None:
        return model()
    try:
        data = json.loads(raw)
    except ValueError as err:
        raise CommandError(f"make the config valid JSON: {err}") from err
    return parse_model(model, data, "the config")


def universe_symbols(book: Book, given: Sequence[str] | None) -> list[str]:
    if given is not None:
        return list(given)
    path = book.root / UNIVERSE_FILE
    if not path.is_file():
        raise CommandError(
            f"no {UNIVERSE_FILE} in the book: name symbols in the config, or copy "
            "the universe CSV there"
        )
    return sorted(parse_universe(path.read_text(encoding="utf-8")))


def fetched(book: Book, source: Source, raw: str | None, since: date) -> Loaded:
    match source:
        case Source.CSV:
            if raw is None:
                raise CommandError("load csv needs --config:file naming bars or events")
            return csv.fetch(config_of(csv.CsvConfig, raw))
        case Source.FRENCH:
            return french.fetch(config_of(french.FrenchConfig, raw))
        case Source.EDGAR:
            edgar_config = config_of(edgar.EdgarConfig, raw)
            symbols = universe_symbols(book, edgar_config.symbols)
            return edgar.fetch(edgar_config, symbols)
        case Source.TIINGO:
            tiingo_config = config_of(tiingo.TiingoConfig, raw)
            symbols = universe_symbols(book, tiingo_config.symbols)
            return tiingo.fetch(symbols, since, datetime.now(UTC).date())


def cmd_load(args: argparse.Namespace) -> int:
    book = open_book(args.book)
    source = Source(args.source)
    manifest = read_manifest(book)
    verified = verify_all(book, manifest)
    today = datetime.now(UTC).date()
    since: date = args.since or default_since(manifest, source, today)
    if since > today:
        raise CommandError(f"--since {since} is after today; nothing to load")
    raw = text(CONFIG, args)
    loaded, dropped = fetched(book, source, raw, since).since(day_of(since))
    if dropped:
        signal(f"{dropped} row(s) before {since} dropped; pass an earlier --since")
    manifest, added = store(book, source, loaded, since=since, today=today)
    if not added:
        signal(f"{source.value} yielded no rows from {since}; nothing written")
    emit(
        {
            "book": book.meta.id,
            "source": source.value,
            "since": since.isoformat(),
            "files": [
                {"path": e.path, "rows": e.rows, "sha256": e.sha256} for e in added
            ],
            "rows": {
                table.value: sum(e.rows for e in added if e.table == table)
                for table in (Table.BARS, Table.EVENTS)
            },
            "verified": verified,
            "data_snapshot": data_snapshot(manifest),
        }
    )
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    del args
    emit(
        {
            "record_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
            "sequence": "hypotheses, critiques, decisions, fills, holdings, "
            "preferences; a decision may name a hypothesis made earlier in the batch",
            "ledger_line": f"{', '.join(ENVELOPE)} (stamped by record), then the "
            "record; prev is the sha256 hex of the previous line's bytes",
            "corrections": '"supersedes": "<id>" on a new line; newest wins',
            "run_line": f"{', '.join(RunLine.model_fields)} (written by score only)",
            "strategy_config": '{"params": {"<name>": 1.0}, "rebalance": '
            '"monthly|quarterly|annual", "holding_days": 21, "long_only": true, '
            '"family_id": "<key of limits.families>"}',
            "approval": '{"date": "YYYY-MM-DD", "orders": [{"symbol": "...", '
            '"side": "buy|sell", "quantity": 10, "price": 12.5, '
            '"strategy": "<name>", "adv_participation": 0.004}]} '
            "(the operator writes it; bin/send reads it)",
            "refs": REFS_SCHEMA + "; receipts echo every new id under new",
            "pad": PAD_SCHEMA,
        }
    )
    return 0


def name_of(raw: str, what: str) -> str:
    if not NAME.fullmatch(raw):
        raise CommandError(
            f"{what} {raw!r}: use lowercase letters, digits, '-', '_'; never a path"
        )
    return raw


def code_hash(*parts: bytes) -> str:
    """sha256 over each part's length and bytes, then the engine version."""
    digest = hashlib.sha256()
    for part in (*parts, btm_finance.__version__.encode()):
        digest.update(len(part).to_bytes(8, "big") + part)
    return digest.hexdigest()


def scoped(book: Book, names: Sequence[str], *, held_out: bool) -> frozenset[str]:
    """Research names, or with `held_out` their complement."""
    salt, members = held_out_list(book)
    chosen = frozenset(n for n in names if (member(salt, n) in members) == held_out)
    if held_out and not chosen:
        raise CommandError("the held-out list names no loaded symbol; nothing to score")
    return chosen


def peers_of(book: Book, manifest: Manifest, family: str) -> Peers:
    """The family's run lines so far. A research run with a stored series is
    a peer: its series feeds PBO and its net Sharpe `sr_var`, in file order."""
    rows = [row for row in all_runs(book) if row.get("family_id") == family]
    ids: list[str] = []
    sharpes: list[float] = []
    series = []
    for row in rows:
        if row.get("held_out"):
            continue
        run_id = str(row.get("run_id"))
        found = read_returns(book, manifest, run_id)
        if found is None:
            signal(f"run {run_id} lists no returns file; left out of PBO and sr_var")
            continue
        card = row.get("scorecard")
        value = card.get("sharpe_net") if isinstance(card, dict) else None
        if isinstance(value, int | float):
            sharpes.append(float(value) / math.sqrt(PERIODS_PER_YEAR))
        ids.append(run_id)
        series.append(found)
    return Peers(
        trials=len(rows), sharpes=tuple(sharpes), series=tuple(series), ids=tuple(ids)
    )


def registered(book: Book, strategy: str) -> Row:
    named = [
        row
        for row in current(kind_rows(book, Kind.HYPOTHESIS))
        if row.get("strategy") == strategy
    ]
    if not named:
        raise CommandError(
            f"strategy {strategy} is unregistered: no hypothesis names it; "
            "record its hypothesis first, then score"
        )
    return named[-1]


def file_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as err:
        raise CommandError(f"cannot read {path}: {err}") from err


def cmd_score(args: argparse.Namespace) -> int:
    """Refusals before running write nothing; bounds broken after running
    still append the run line, then exit 1."""
    if args.repeat is not None:
        raise CommandError("score --repeat arrives in stage 5; not available yet")
    book = open_book(args.book)
    limits, preferences = load_limits(book), load_preferences(book)
    name = name_of(args.strategy, "strategy")
    agent = None if args.agent is None else name_of(args.agent, "agent")
    folder = book.root / "strategies" / name
    if not folder.is_dir():
        raise CommandError(f"no strategies/{name}/ in the book")
    hypothesis = registered(book, name)
    config_bytes = file_bytes(folder / "config.json")
    config = parse_model(
        StrategyConfig,
        read_json(folder / "config.json"),
        f"strategies/{name}/config.json",
    )
    if config.holding_days < limits.min_holding_days:
        raise CommandError(
            f"refused before running: holding_days {config.holding_days} is under "
            f"limits.min_holding_days {limits.min_holding_days}"
        )
    if config.family_id != hypothesis.get("family_id"):
        raise CommandError(
            f"config family_id {config.family_id} differs from hypothesis "
            f"{hypothesis.get('id')} family {hypothesis.get('family_id')}"
        )
    source = file_bytes(folder / "signal.py")
    module = f"btm_strategy_{name.replace('-', '_')}_{secrets.token_hex(4)}"
    strategy = load_signal(
        source.decode("utf-8", errors="replace"), f"strategies/{name}/signal.py", module
    )
    panel, events = assemble(book)
    names = scoped(book, panel.names, held_out=args.held_out)
    panel, events = panel.only(names), events.only(names)
    manifest = read_manifest(book)
    peers = peers_of(book, manifest, config.family_id)
    params = dict(config.params)
    setting = Setting.of(panel, events, rules_of(limits, preferences, config))
    outcome = evaluate(setting, strategy, params, peers)
    refused = bounds(outcome.scorecard, limits)
    snapshot = data_snapshot(manifest)
    run_id = make_id([*ascii_words(name), "run"])
    write_returns(
        book,
        run_id,
        dates=outcome.dates,
        gross=outcome.gross,
        net=outcome.net,
    )
    line = RunLine(
        run_id=run_id,
        hypothesis_id=str(hypothesis.get("id")),
        family_id=config.family_id,
        strategy=name,
        data_snapshot=snapshot,
        code_hash=code_hash(source, config_bytes),
        config=config.model_dump(mode="json"),
        params={key: float(value) for key, value in params.items()},
        scorecard=outcome.scorecard,
        reasons=outcome.reasons,
        engine={
            "btm_finance": btm_finance.__version__,
            "numpy": np.__version__,
            "pyarrow": pa.__version__,
        },
        tolerance=limits.repeat_tolerance,
        held_out=args.held_out,
        exclusions=Exclusions.model_validate(preferences.exclusions.model_dump()),
        refused=tuple(refused),
        peers=peers.ids,
        span=Span(
            start=date_of(int(outcome.dates[0])).isoformat(),
            end=date_of(int(outcome.dates[-1])).isoformat(),
            periods=len(outcome.dates),
        ),
        returns=returns_path(run_id),
        agent=agent,
    )
    target = (
        book.ledger / "runs" / f"{agent}.jsonl" if agent else book.path_of(Kind.RUN)
    )
    append_chained(
        target, [{"id": run_id, "ts": now_iso(), **line.model_dump(mode="json")}]
    )
    if outcome.unknown:
        signal(
            f"signal named {outcome.unknown} name(s) the market did not serve; dropped"
        )
    emit(
        {
            "book": book.meta.id,
            "run_id": run_id,
            "strategy": name,
            "held_out": args.held_out,
            "scorecard": outcome.scorecard.model_dump(mode="json"),
            "reasons": outcome.reasons,
            "refused": refused,
            "next": f"fix {', '.join(r.split(':')[0] for r in refused)}; the run "
            "still counts as a trial"
            if refused
            else f"delegate a critique of {run_id}, then check {name}",
        }
    )
    for item in refused:
        print(f"error: refused {item}", file=sys.stderr)
    return 1 if refused else 0


def later(verb: str) -> int:
    def refuse() -> int:
        raise CommandError(f"{verb} arrives in {LATER[verb]}; not available yet")

    return dispatch(refuse)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(description=btm_finance.__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="make a book at a new path")
    start.set_defaults(func=cmd_start)
    start.add_argument("book", help="directory to make the book in")
    start.add_argument(
        "--cap", type=positive, default=10_000_000, help="asset cap, default 10000000"
    )
    add_slot(start, UNIVERSE, "CSV with a symbol column and an optional sector column")

    schema = commands.add_parser("schema", help="print every record shape")
    schema.set_defaults(func=cmd_schema)

    record = commands.add_parser("record", help="accept one batch through the gate")
    record.set_defaults(func=cmd_record)
    record.add_argument("book", help="book directory")
    add_slot(record, BATCH, ", ".join(BATCH_KEYS))

    check = commands.add_parser(
        "check", help="continue view, or a strategy's promotion standing"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("book", help="book directory")
    check.add_argument(
        "target",
        nargs="?",
        help="strategy or run id; a proposal date arrives in stage 4",
    )
    check.add_argument("--live", action="store_true", help="refused until stage 5")

    score = commands.add_parser("score", help="score a registered strategy")
    score.set_defaults(func=cmd_score)
    score.add_argument("book", help="book directory")
    score.add_argument("strategy", help="directory under strategies/")
    score.add_argument(
        "--held-out", action="store_true", help="the human's one run on held-out names"
    )
    score.add_argument("--agent", help="append to ledger/runs/<agent>.jsonl")
    score.add_argument("--repeat", metavar="RUN_ID", help="refused until stage 5")

    for verb, stage in LATER.items():
        stub = commands.add_parser(verb, help=f"arrives in {stage}; refused today")
        stub.add_argument("rest", nargs=argparse.REMAINDER)
    load = commands.add_parser("load", help="pull one source into the raw store")
    load.set_defaults(func=cmd_load)
    load.add_argument("book", help="book directory")
    load.add_argument("source", choices=[source.value for source in Source])
    load.add_argument(
        "--since",
        type=iso_day,
        help="first date to keep; default the day after the source's last",
    )
    add_slot(load, CONFIG, "JSON object; required for csv: bars, events, columns")

    wire_pad(commands, PAD)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    given = list(sys.argv[1:] if argv is None else argv)
    if given and given[0] in LATER:
        return later(given[0])
    return run_cli(build_parser(), given)
