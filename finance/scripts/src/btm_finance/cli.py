"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
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
from btm_finance.api import FACTORS, Market, ledger, on_dates
from btm_finance.batch import BATCH_KEYS, SCHEMA, Context, RecordResult, expand_batch
from btm_finance.brief import Bet, Open, brief, justifying
from btm_finance.data.assemble import UNIVERSE as UNIVERSE_FILE
from btm_finance.data.assemble import assemble, parse_universe
from btm_finance.data.panel import Events, Panel
from btm_finance.data.raw import (
    Entry,
    Manifest,
    data_snapshot,
    default_since,
    read_manifest,
    read_returns,
    returns_path,
    sha256_of,
    store,
    verify_all,
    write_returns,
)
from btm_finance.data.sources import csv, edgar, french, tiingo
from btm_finance.data.tables import (
    Days,
    Floats,
    Loaded,
    Source,
    Table,
    date_of,
    day_of,
)
from btm_finance.engine.metrics import PERIODS_PER_YEAR
from btm_finance.ledger import (
    ENVELOPE,
    Kind,
    Numbered,
    Row,
    current,
    cut_line,
    dangling,
    rows_of,
    undecodable,
)
from btm_finance.live import NEXT as LIVE_NEXT
from btm_finance.live import (
    Bounds,
    Case,
    Fill,
    LiveReport,
    LiveRow,
    RunFacts,
    Sleeve,
    breaches_of,
    fill_of,
    fresh,
    model_path,
    realized,
    reference_prices,
    report_of,
    row_of,
    seasoning,
    tier_of,
    trading_days_after,
)
from btm_finance.loader import load_strategy, strategy_reach
from btm_finance.measuring import (
    Peers,
    Prepared,
    Setting,
    Strategy,
    bounds,
    evaluate,
    rules_of,
    target_weights,
)
from btm_finance.models import (
    Action,
    Cadence,
    Exclusions,
    Limits,
    Preferences,
    Status,
    StrategyConfig,
    baseline_hypothesis,
)
from btm_finance.recommending import (
    AdvCut,
    Candidate,
    Inputs,
    Previous,
    Proposal,
    Quote,
    RuinCut,
    Skipped,
    Tier,
    account_of,
    approval_of,
    propose,
)
from btm_finance.regimes import (
    Dated,
    concentration,
    dated,
    falsified_warnings,
    regime_record,
    regime_stamp,
)
from btm_finance.repeat import (
    Presence,
    RepeatReport,
    canonical_config,
    canonical_source,
    code_drift,
    compare,
    data_drift,
    peer_drift,
)
from btm_finance.repeat import advisories as engine_advisories
from btm_finance.scaffold import INDEX, scaffold
from btm_finance.scorecard import RunLine, Span
from btm_finance.standing import Evidence, StandingView, standing_of
from btm_finance.store import (
    PAD,
    PAD_DIR,
    Book,
    append_ledger,
    held_out_list,
    load_limits,
    load_preferences,
    open_book,
    previous_proposal,
    proposal_dates,
    proposal_target,
    proposal_versions,
    read_bytes,
    read_json,
    run_files,
    strategies,
)
from btm_finance.streams import Series, effective_streams, pairs_of
from btm_finance.views import (
    CLOSING,
    by_status,
    families,
    next_step,
    open_hypotheses,
    open_proposals,
    overdue,
    unscored,
)

UNIVERSE = Optional("universe", inline=False)
CONFIG = Optional("config", inline=False)
LATER: dict[str, str] = {}
MONTH_DAYS, QUARTER_DAYS = 31, 92  # one cadence period, in calendar days
STALE_BARS = 5  # trading days an as-of bar may trail the proposal date
BASELINE = "baseline"
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


def start(
    root: Path, cap: int, universe: str | None, held_out: Path | None = None
) -> dict[str, Any]:
    """Make the book, then register the baseline hypothesis through the gate."""
    receipt = scaffold(root, cap, universe, held_out)
    book = open_book(str(root))
    limits = load_limits(book)
    context = Context(
        families=frozenset(limits.families),
        min_holding_days=limits.min_holding_days,
        ids={},
        strategies=["baseline"],
        proposals=[],
    )
    batch = {"hypotheses": [baseline_hypothesis(datetime.now(UTC).date())]}
    result = expand_batch(context, batch, make_id, now_iso())
    if result.problems:
        raise CommandError(f"baseline hypothesis refused: {result.problems}")
    append_ledger(book.path_of(Kind.HYPOTHESIS), result.staged[Kind.HYPOTHESIS])
    receipt["wrote"].append("ledger/hypotheses.jsonl")
    receipt["new"] = result.new["hypotheses"]
    return receipt


def cmd_start(args: argparse.Namespace) -> int:
    emit(
        start(
            Path(args.book).expanduser(), args.cap, text(UNIVERSE, args), args.held_out
        )
    )
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
    kinds = (
        Kind.HYPOTHESIS,
        Kind.CRITIQUE,
        Kind.DECISION,
        Kind.SCORED,
        Kind.REGIME,
        Kind.FILL,
    )
    ids = {kind: ids_of(book.path_of(kind)) for kind in kinds}
    context = Context(
        families=frozenset(limits.families),
        min_holding_days=limits.min_holding_days,
        ids={**ids, Kind.RUN: run_ids(book)},
        strategies=[strategy.name for strategy in strategies(book)],
        proposals=proposal_dates(book),
        live_regimes=frozenset(
            str(row.get("id")) for row in current(kind_rows(book, Kind.REGIME))
        ),
        live_hypotheses=frozenset(
            str(row.get("id")) for row in current(kind_rows(book, Kind.HYPOTHESIS))
        ),
    )

    def expand(batch: dict[str, Any]) -> RecordResult:
        return expand_batch(context, batch, make_id, now_iso())

    def commit(result: RecordResult) -> dict[str, Any]:
        accepted: dict[str, int] = {}
        for kind, rows in sorted(result.staged.items()):
            append_ledger(book.path_of(kind), rows)
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
    book = open_book(args.book)
    if args.live:
        today = args.today or datetime.now(UTC).date()
        emit(live_view(book, today).model_dump(mode="json"))
        return 0
    if args.brief:
        if args.target is not None:
            raise CommandError("--brief takes no target; run check <book> --brief")
        emit(brief_view(book))
        return 0
    if args.target is None:
        emit(continue_view(book))
        return 0
    try:
        when = date.fromisoformat(args.target)
    except ValueError:
        view = standing_view(book, args.target, advisory=True)
        emit(view.model_dump(mode="json"))
        return 0
    emit(proposal_view(book, when))
    return 0


def kind_rows(book: Book, kind: Kind) -> list[Numbered]:
    return rows_of(read_bytes(book.path_of(kind)))


def all_runs(book: Book) -> list[Row]:
    """Live run lines of every runs file, oldest first by `ts`."""
    return ledger(book, Kind.RUN)


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


def regime_rows(book: Book) -> list[Dated]:
    return dated(current(kind_rows(book, Kind.REGIME)))


def sleeve_series(book: Book, manifest: Manifest, skip: str) -> dict[str, Series]:
    """Each paper or live sleeve's newest research run series, but `skip`'s;
    a sleeve with no stored series is left out."""
    runs = all_runs(book)
    found: dict[str, Series] = {}
    for listed in strategies(book):
        if listed.name == skip or account_of(listed.status) is None:
            continue
        run = newest_run(runs, listed.name)
        series = (
            None if run is None else read_returns(book, manifest, str(run["run_id"]))
        )
        if series is not None:
            found[listed.name] = series
    return found


def advisory_of(
    book: Book, view: StandingView, run: Row, limits: Limits
) -> StandingView:
    """Regime concentration, correlation with each sleeve, effective streams;
    never a blocker. O(S^2 T log T)."""
    manifest = read_manifest(book)
    own = read_returns(book, manifest, str(run.get("run_id")))
    sleeves = sleeve_series(book, manifest, view.strategy)
    series = {**sleeves, **({view.strategy: own} if own is not None else {})}
    pairs = pairs_of(series)
    streams = effective_streams(sorted(series), pairs)
    if streams is not None and streams < limits.min_effective_streams:
        signal(
            f"effective_streams {streams:.3g} under limits.min_effective_streams "
            f"{limits.min_effective_streams}: {view.strategy} adds a trial, "
            "not a stream"
        )
    return view.with_(
        regime_concentration=concentration(run.get("regime_days")),
        correlation={
            name: None if own is None else pairs[frozenset((name, view.strategy))]
            for name in sorted(sleeves)
        },
        effective_streams=streams,
    )


def standing_view(book: Book, target: str, *, advisory: bool = False) -> StandingView:
    """`check <strategy>` or `check <run id>`: standing of the newest measured
    research run, or of the named run; `advisory` adds the stream fields."""
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
        status=found.status if found else Status.RESEARCH,
        raw_status=found.raw if found else "",
        today=datetime.now(UTC).date(),
    )
    limits = load_limits(book)
    view = standing_of(evidence, limits)
    return advisory_of(book, view, run, limits) if advisory and run else view


def ledger_warnings(book: Book) -> list[dict[str, Any]]:
    """Cut and undecodable lines and dangling `supersedes`, per file; derived
    on every call, never stored or repaired. Run files share one id set."""
    groups = [[book.path_of(kind)] for kind in Kind if kind is not Kind.RUN]
    found: list[dict[str, Any]] = []
    for paths in [*groups, run_files(book)]:
        read = [(book.relative(path), read_bytes(path)) for path in paths]
        rows = {name: rows_of(data) for name, data in read}
        ids = {row.get("id") for numbered in rows.values() for _, row in numbered}
        for name, data in read:
            found += (
                cut_line(name, data)
                + undecodable(name, data)
                + dangling(name, rows[name], ids)
            )
    return found


def index_warning(book: Book) -> list[dict[str, Any]]:
    """`INDEX.md` absent: the lead keeps one line per lib module, tool, and
    research topic there."""
    if (book.root / INDEX).is_file():
        return []
    signal(f"no {INDEX} in the book; write it with one line per lib, tool, topic")
    return [{"file": INDEX, "problem": "absent"}]


def continue_view(book: Book) -> dict[str, Any]:
    """Every ledger file replayed: O(ledger bytes)."""
    limits = load_limits(book)
    warnings = ledger_warnings(book)
    if warnings:
        signal(f"{len(warnings)} ledger warning(s) under warnings; tell the operator")

    def live(kind: Kind) -> list[dict[str, Any]]:
        return current(kind_rows(book, kind))

    runs = all_runs(book)
    hypothesis_lines = kind_rows(book, Kind.HYPOTHESIS)
    hypotheses, decisions = current(hypothesis_lines), live(Kind.DECISION)
    scored = live(Kind.SCORED)
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
    today = datetime.now(UTC).date()
    proposals = open_proposals(proposal_dates(book), decisions, today)
    pending = len(open_hypotheses(hypotheses, runs, decisions))
    records = regime_rows(book)
    regime = regime_record(records, today, limits.regime_stale_days)
    if regime is not None and regime.stale:
        signal(f"regime record {regime.id} as of {regime.as_of} is stale; draft one")
    closed = {d.get("subject") for d in decisions if d.get("action") in CLOSING}
    fired = falsified_warnings(records, hypotheses, closed)
    for entry in fired:
        signal(
            f"hypothesis {entry['hypothesis']} cites chain {entry['chain']}, "
            f"falsified in regime {entry['regime']}; write an objection pad entry"
        )
    retired = frozenset(name for name, s in known.items() if s is Status.RETIRED)
    late = [
        *overdue(hypotheses, decisions, scored, retired, today),
        *unscored(hypotheses, decisions, scored, today),
    ]
    if late:
        signal(f"{len(late)} overdue or unscored hypothesis(es) under warnings")
    return {
        "book": book.meta.id,
        "as_of": now_iso(),
        "regime": None if regime is None else regime.model_dump(mode="json"),
        "strategies": {**by_status(known), "unknown": unknown},
        "families": families(
            limits, hypotheses, runs, decisions, [row for _, row in hypothesis_lines]
        ),
        "proposals": proposals,
        "incidents": live(Kind.INCIDENT)[-INCIDENT_TAIL:],
        "pad": {"entries": count_lines(book.root / PAD_DIR / "scratch.jsonl")},
        "warnings": [*warnings, *fired, *late, *index_warning(book)],
        "next": next_step(hypotheses, pending, proposals, late),
    }


def brief_view(book: Book) -> dict[str, Any]:
    """`check --brief`: the continue view cut to at most twelve lines."""
    view = continue_view(book)
    runs = {str(row.get("run_id")): row for row in all_runs(book)}
    opened: list[Open] = []
    for entry in view["proposals"]:
        path = book.root / "proposals" / f"{entry['date']}.json"
        document = read_json(path) if path.is_file() else {}
        sleeves = document.get("sleeves") if isinstance(document, dict) else None
        bets: list[Bet] = []
        for name, sleeve in (sleeves if isinstance(sleeves, dict) else {}).items():
            run = runs.get(str(sleeve.get("run_id")))
            card = run.get("scorecard") if run else None
            odds = (hypothesis_for(book, run, name) or {}).get("odds")
            tier = str(sleeve.get("tier") or "-")
            bets.append(
                Bet(
                    strategy=name,
                    tier=tier,
                    weight=sleeve.get("weight"),
                    odds=odds if isinstance(odds, dict) else None,
                    number=justifying(
                        tier,
                        sleeve.get("sharpe_net"),
                        card.get("dsr") if isinstance(card, dict) else None,
                    ),
                )
            )
        opened.append(Open(entry["date"], entry["age_days"], tuple(bets)))
    late = Counter(w.get("problem") for w in view["warnings"])
    return brief(
        regime=view["regime"],
        proposals=opened,
        incidents=current(kind_rows(book, Kind.INCIDENT)),
        overdue=late["overdue"],
        unscored=late["unscored"],
        next_action=view["next"],
        today=datetime.now(UTC).date(),
    )


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
            "sequence": "hypotheses, critiques, decisions, scored, regimes, "
            "fills, holdings, preferences; a decision or scored line may name a "
            "hypothesis made earlier in the batch",
            "ledger_line": f"{', '.join(ENVELOPE)} (stamped by record), then the "
            "record",
            "corrections": '"supersedes": "<id>" on a new line; newest wins',
            "run_line": f"{', '.join(RunLine.model_fields)} (written by measure only)",
            "strategy_config": '{"params": {"<name>": 1.0}, "rebalance": '
            '"monthly|quarterly|annual", "holding_days": 21, "long_only": true, '
            '"family_id": "<key of limits.families>"}',
            "approval": '{"date": "YYYY-MM-DD", "proposal": "<proposal stem>", '
            '"orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, '
            '"price": 12.5, "adv_participation": 0.004, "strategy": "<name>", '
            '"limit": null}]} (check <date> prints it as approval_template; '
            "the operator writes it; bin/send checks it, prints the orders, "
            "records fills)",
            "fill_table": "CSV with header symbol,side,quantity,price,date "
            "(optional strategy), or a JSON list of objects with those keys; "
            "the operator pastes broker fills there for bin/send --fills",
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


@dataclass(frozen=True, slots=True)
class Code:
    """A strategy's code inputs: `signal.py`, `config.json`, and each
    book-local module it reaches, by path relative to the book root."""

    source: bytes
    config: bytes
    modules: Mapping[str, bytes]


def code_of(book: Book, name: str) -> Code:
    folder = book.root / "strategies" / name
    reach = strategy_reach(book.root, name)
    return Code(
        source=file_bytes(folder / "signal.py"),
        config=file_bytes(folder / "config.json"),
        modules={path: file_bytes(book.root / path) for path in reach.modules},
    )


def code_hash(code: Code) -> str:
    """sha256 over the AST dump of `signal.py`, canonical `config.json`, then
    each module's path and AST dump, each with its length, then the engine
    version: a reformat moves nothing."""
    digest = hashlib.sha256()
    parts = [canonical_source(code.source), canonical_config(code.config)]
    for path in sorted(code.modules):
        parts += [path.encode(), canonical_source(code.modules[path], path)]
    for part in (*parts, btm_finance.__version__.encode()):
        digest.update(len(part).to_bytes(8, "big") + part)
    return digest.hexdigest()


def code_files(code: Code) -> dict[str, str]:
    """Per file, sha256 of the same canonical forms `code_hash` folds."""
    return {
        "signal.py": sha256_of(canonical_source(code.source)),
        "config.json": sha256_of(canonical_config(code.config)),
        **{
            path: sha256_of(canonical_source(data, path))
            for path, data in sorted(code.modules.items())
        },
    }


def scoped(book: Book, names: Sequence[str], *, held_out: bool) -> frozenset[str]:
    """Research names, or with `held_out` their complement."""
    listed = held_out_list(book)
    chosen = frozenset(n for n in names if (n in listed) == held_out)
    if held_out and not chosen:
        raise CommandError(
            "the held-out list names no loaded symbol; nothing to measure"
        )
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
            "record its hypothesis first, then measure"
        )
    return named[-1]


def file_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as err:
        raise CommandError(f"cannot read {path}: {err}") from err


def cmd_measure(args: argparse.Namespace) -> int:
    """Refusals before running write nothing; bounds broken after running
    still append the run line, then exit 1."""
    if args.repeat is not None:
        return cmd_repeat(args)
    book = open_book(args.book)
    limits, preferences = load_limits(book), load_preferences(book)
    name = name_of(args.strategy, "strategy")
    agent = None if args.agent is None else name_of(args.agent, "agent")
    folder = book.root / "strategies" / name
    if not folder.is_dir():
        raise CommandError(f"no strategies/{name}/ in the book")
    hypothesis = registered(book, name)
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
    code = code_of(book, name)
    loaded = load_strategy(book.root, name)
    strategy = loaded.signal
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
    spanned, regime_days = regime_stamp(outcome.dates, regime_rows(book))
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
        code_hash=code_hash(code),
        code_files=code_files(code),
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
        regimes=spanned,
        regime_days=regime_days,
        imports=loaded.imports,
    )
    target = (
        book.ledger / "runs" / f"{agent}.jsonl" if agent else book.path_of(Kind.RUN)
    )
    append_ledger(
        target, [{"id": run_id, "ts": now_iso(), **line.model_dump(mode="json")}]
    )
    if outcome.unknown:
        signal(
            f"signal named {outcome.unknown} name(s) the market did not serve; dropped"
        )
    if loaded.imports:
        signal(
            f"signal.py reaches {', '.join(loaded.imports)} from outside the book; "
            "listed under imports on the run line for the critique"
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
            "regime_days": regime_days,
            "imports": list(loaded.imports),
            "next": f"fix {', '.join(r.split(':')[0] for r in refused)}; the run "
            "still counts as a trial"
            if refused
            else f"delegate a critique of {run_id}, then check {name}",
        }
    )
    for item in refused:
        print(f"error: refused {item}", file=sys.stderr)
    return 1 if refused else 0


def newest_run(runs: Sequence[Row], strategy: str) -> Row | None:
    own = [r for r in runs if r.get("strategy") == strategy and not r.get("held_out")]
    return own[-1] if own else None


def card_number(run: Row, key: str) -> float | None:
    card = run.get("scorecard")
    value = card.get(key) if isinstance(card, dict) else None
    return float(value) if isinstance(value, int | float) else None


def half_spread(run: Row) -> float:
    card = run.get("scorecard")
    model = card.get("spread_model") if isinstance(card, dict) else None
    value = model.get("half_spread_mean") if isinstance(model, dict) else None
    return float(value) if isinstance(value, int | float) else 0.0


@dataclass(frozen=True, slots=True)
class Day:
    """The scoped data and the as-of row `recommend` reads every sleeve on."""

    panel: Panel
    events: Events
    prep: Prepared
    row: int


def sleeve_tier(  # noqa: PLR0913 - one sleeve's ledger evidence
    setting: Setting,
    strategy: Strategy,
    params: Mapping[str, float],
    *,
    name: str,
    fills: Sequence[Row],
    limits: Limits,
    through: int,
) -> Tier:
    """Tier from the sleeve's dry-run and real fills through `through`
    against one model simulation, run only when the sleeve has fills."""
    paper = sleeve_fills(fills, name, Status.PAPER, {}, {})
    real = sleeve_fills(fills, name, Status.LIVE, {}, {})
    if not paper and not real:
        return Tier.BACKTEST
    model = model_path(setting, strategy, params)
    rf = setting.prep.rf
    return tier_of(
        seasoning(paper, setting.panel, rf, model, through),
        seasoning(real, setting.panel, rf, model, through),
        days=limits.thresholds.paper_min_days,
        bound=limits.thresholds.tracking_error,
    )


def candidate(  # noqa: PLR0913 - one sleeve's inputs, read once each
    book: Book,
    limits: Limits,
    preferences: Preferences,
    day: Day,
    *,
    run: Row,
    status: Status,
    fills: Sequence[Row],
) -> Candidate:
    """The sleeve's weights on the as-of row through `Market.at` and
    `target_weights`, as `measure` sets them; vol from the run's net series;
    tier `probe` by status, else from its fills."""
    account = account_of(status)
    if account is None:
        raise CommandError(f"status {status} names no sleeve")
    name = str(run.get("strategy"))
    folder = book.root / "strategies" / name
    config = parse_model(
        StrategyConfig,
        read_json(folder / "config.json"),
        f"strategies/{name}/config.json",
    )
    strategy = load_strategy(book.root, name).signal
    rules = rules_of(limits, preferences, config)
    setting = Setting(day.panel, day.events, day.prep, rules)
    market = Market.at(day.panel, day.events, int(day.panel.dates[day.row]))
    try:
        raw = strategy(market, dict(config.params))
    except Exception as err:  # the strategy's failure, named for its author
        raise CommandError(f"{name} signal raised: {err!r}") from err
    index = {symbol: column for column, symbol in enumerate(day.panel.names)}
    chosen = target_weights(raw, market, setting, index, day.row)
    weights, unknown = chosen.weights, chosen.unknown
    tier = (
        Tier.PROBE
        if status is Status.PROBE
        else sleeve_tier(
            setting,
            strategy,
            dict(config.params),
            name=name,
            fills=fills,
            limits=limits,
            through=int(day.panel.dates[day.row]),
        )
    )
    series = read_returns(book, read_manifest(book), str(run.get("run_id")))
    vol = None
    if series is not None and len(series[1]) > 1:
        vol = float(np.std(series[1], ddof=1)) * math.sqrt(PERIODS_PER_YEAR)
    changed = code_hash(code_of(book, name)) != run.get("code_hash")
    if changed:
        signal(f"{name}: strategy code changed since run {run['run_id']}")
    return Candidate(
        strategy=name,
        account=account,
        run_id=str(run.get("run_id")),
        sharpe_net=card_number(run, "sharpe_net"),
        vol_net=vol,
        max_drawdown=card_number(run, "max_drawdown"),
        half_spread=half_spread(run),
        code_changed=changed,
        unknown=unknown,
        signal={
            str(k): float(v)
            for k, v in (raw.items() if isinstance(raw, dict) else [])
            if isinstance(v, int | float)
        },
        weights={
            symbol: float(w)
            for symbol, w in zip(day.panel.names, weights.tolist(), strict=True)
            if w
        },
        series=series,
        dsr=card_number(run, "dsr"),
        tier=tier,
    )


def quotes_of(day: Day) -> dict[str, Quote]:
    """Per name its last close on or before the row and its ADV. O(T N)."""
    panel, adv = day.panel, day.prep.adv[day.row]
    seen = np.isfinite(panel.close[: day.row + 1])
    rows = np.arange(day.row + 1)[:, None]
    last = np.where(seen, rows, -1).max(axis=0, initial=-1)
    return {
        name: Quote(
            price=float(panel.close[int(at), column]),
            adv=float(adv[column]),
            sector=panel.sector[column],
        )
        for column, (name, at) in enumerate(
            zip(panel.names, last.tolist(), strict=True)
        )
        if at >= 0
    }


def previous_of(book: Book, day: str) -> Previous | None:
    path = previous_proposal(book, day)
    if path is None:
        return None
    stem = path.stem
    rejected = any(
        row.get("subject") == stem and row.get("action") == Action.REJECT.value
        for row in current(kind_rows(book, Kind.DECISION))
    )
    proposal = parse_model(Proposal, read_json(path), book.relative(path))
    return Previous(stem=stem, proposal=proposal, rejected=rejected)


def sleeves_of(book: Book) -> tuple[list[tuple[Row, Status]], list[Skipped]]:
    """Probe, paper, and live strategies with their newest research run line."""
    runs = all_runs(book)
    chosen: list[tuple[Row, Status]] = []
    skipped: list[Skipped] = []
    for found in strategies(book):
        if found.status is None or account_of(found.status) is None:
            continue
        run = newest_run(runs, found.name)
        if run is None:
            reason = f"{found.status} with no run line: measure {found.name} first"
            signal(f"sleeve {found.name} skipped: {reason}")
            skipped.append(Skipped(strategy=found.name, reason=reason))
            continue
        chosen.append((run, found.status))
    return chosen, skipped


def cmd_recommend(args: argparse.Namespace) -> int:
    """Writes `proposals/<date>.json` and nothing else."""
    book = open_book(args.book)
    when: date = args.date
    chosen, skipped = sleeves_of(book)
    if not chosen:
        named = ", ".join(s.strategy for s in skipped)
        raise CommandError(
            "no sleeve: no strategies/*/status reads probe, paper, or live with a "
            "run line"
            + (f" (skipped {named})" if named else "")
            + "; the operator sets status, the agent measures"
        )
    target = proposal_target(book, when.isoformat(), force=args.force)
    limits, preferences = load_limits(book), load_preferences(book)
    panel, events = assemble(book)
    names = scoped(book, panel.names, held_out=False)
    panel, events = panel.only(names), events.only(names)
    row = panel.through(day_of(when)) - 1
    if row < 0:
        raise CommandError(f"no bar on or before {when}; load prices first")
    day = Day(panel, events, Prepared.of(panel, events, limits.delisting), row)
    fills = current(kind_rows(book, Kind.FILL))
    candidates = tuple(
        candidate(book, limits, preferences, day, run=run, status=status, fills=fills)
        for run, status in chosen
    )
    proposal = propose(
        Inputs(
            date=when.isoformat(),
            as_of=date_of(int(panel.dates[row])).isoformat(),
            cap=limits.asset_cap,
            sizing=limits.sizing,
            bound=limits.max_adv_participation,
            commission_bps=limits.commission_bps,
            candidates=candidates,
            skipped=tuple(skipped),
            quotes=quotes_of(day),
            fills=fills,
            previous=previous_of(book, when.isoformat()),
            risk_share=limits.max_strategy_risk_share,
            regime=regime_record(regime_rows(book), when, limits.regime_stale_days),
        )
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(target, json.dumps(proposal.model_dump(mode="json"), indent=2) + "\n")
    for cut in proposal.cuts:
        match cut:
            case AdvCut():
                signal(
                    f"{cut.symbol} ({cut.strategy}) cut from {cut.wanted} to "
                    f"{cut.kept}: ADV participation {cut.adv_participation:.4g} "
                    f"over {cut.bound}"
                )
            case RuinCut():
                signal(
                    f"every sleeve scaled by {cut.scale:.4g}: 1st-percentile "
                    f"252-day loss {cut.loss:.4g} over ruin_bound {cut.bound}"
                )
    for name in proposal.advisory.over:
        signal(
            f"advisory: sleeve {name} risk share "
            f"{proposal.advisory.risk_share[name]:.3g} over {proposal.advisory.bound}"
        )
    emit(
        {
            "book": book.meta.id,
            "proposal": book.relative(target),
            "as_of": proposal.as_of,
            "sleeves": {
                s: {
                    "weight": v.weight,
                    "tier": v.tier.value,
                    "edge_scale": v.edge_scale,
                }
                for s, v in proposal.sleeves.items()
            },
            "skipped": [s.model_dump(mode="json") for s in proposal.skipped],
            "orders": len(proposal.orders),
            "cuts": len(proposal.cuts),
            "carried": len(proposal.carried),
            "unmanaged": len(proposal.unmanaged),
            "summary": proposal.summary.model_dump(mode="json"),
            "regime": None
            if proposal.regime is None
            else proposal.regime.model_dump(mode="json"),
            "effective_streams": proposal.effective_streams,
            "ruin": None if proposal.ruin is None else proposal.ruin.loss,
            "reasons": proposal.reasons,
            "next": f"check {target.stem}; read it to the operator, blockers first",
        }
    )
    return 0


def stale_flags(proposal: Proposal, cadence: Cadence, today: date) -> list[str]:
    """Proposal older than one cadence period; as-of bar over 5 trading days
    before the proposal date."""
    match cadence:
        case Cadence.MONTHLY:
            period = MONTH_DAYS
        case Cadence.QUARTERLY:
            period = QUARTER_DAYS
    flags: list[str] = []
    age = (today - date.fromisoformat(proposal.date)).days
    if age > period:
        flags.append(f"proposal is {age} days old, over the {cadence} period")
    behind = int(np.busday_count(proposal.as_of, proposal.date))
    if behind > STALE_BARS:
        flags.append(
            f"as-of bar {proposal.as_of} is {behind} trading days before "
            f"{proposal.date}; load prices, then recommend again with --force"
        )
    return flags


def comparison(book: Book, proposal: Proposal) -> list[dict[str, Any]]:
    """The baseline's row first, then each other sleeve's."""
    rows: list[dict[str, Any]] = []
    for name, sleeve in proposal.sleeves.items():
        rows.append(
            {
                "strategy": name,
                "run_id": sleeve.run_id,
                "tier": sleeve.tier.value,
                "edge_scale": sleeve.edge_scale,
                "sharpe_net": sleeve.sharpe_net,
                "max_drawdown": sleeve.max_drawdown,
                "weight": sleeve.weight,
            }
        )
    if BASELINE not in proposal.sleeves:
        run = newest_run(all_runs(book), BASELINE)
        rows.append(
            {
                "strategy": BASELINE,
                "run_id": None if run is None else run.get("run_id"),
                "tier": None,
                "edge_scale": None,
                "sharpe_net": None if run is None else card_number(run, "sharpe_net"),
                "max_drawdown": None
                if run is None
                else card_number(run, "max_drawdown"),
                "weight": 0.0,
                "note": "baseline is no sleeve here: its status is not probe, "
                "paper, or live",
            }
        )
    return sorted(rows, key=lambda row: row["strategy"] != BASELINE)


def proposal_view(book: Book, when: date) -> dict[str, Any]:
    """`check <date>`: blockers, baseline, stale flags, then the diff."""
    versions = proposal_versions(book, when.isoformat())
    if not versions:
        raise CommandError(f"no proposal for {when}: run recommend {when} first")
    path = versions[-1]
    proposal = parse_model(Proposal, read_json(path), book.relative(path))
    known = {str(row.get("run_id")) for row in all_runs(book)}
    blockers = {
        name: standing_view(book, s.run_id if s.run_id in known else name).model_dump(
            mode="json"
        )["blockers"]
        for name, s in proposal.sleeves.items()
    }
    today = datetime.now(UTC).date()
    template = approval_of(proposal, path.stem)
    return {
        "book": book.meta.id,
        "proposal": book.relative(path),
        "blockers": blockers,
        "baseline": comparison(book, proposal),
        "stale": stale_flags(proposal, load_preferences(book).cadence, today),
        "regime": None
        if proposal.regime is None
        else proposal.regime.model_dump(mode="json"),
        "effective_streams": proposal.effective_streams,
        "advisory": proposal.advisory.model_dump(mode="json"),
        "ruin": None
        if proposal.ruin is None
        else proposal.ruin.model_dump(mode="json"),
        "reasons": proposal.reasons,
        "diff": [
            {
                "symbol": o.symbol,
                "side": o.side.value,
                "quantity": o.quantity,
                "price": o.price,
                "held": o.held,
                "target": o.target,
                "strategy": o.strategy,
                "account": o.account.value,
                "carried_from": o.carried_from,
            }
            for o in proposal.orders
        ],
        "cuts": [cut.model_dump(mode="json") for cut in proposal.cuts],
        "unmanaged": [h.model_dump(mode="json") for h in proposal.unmanaged],
        "skipped": [s.model_dump(mode="json") for s in proposal.skipped],
        "summary": proposal.summary.model_dump(mode="json"),
        "approval_template": template.model_dump(mode="json"),
        "approval_path": f"approvals/{proposal.date}.json",
        "next": "read blockers to the operator first, baseline beside each "
        "sleeve; the operator alone copies approval_template to approval_path, "
        "edits it, sets date and file name to the send day, runs bin/send on "
        "it, places each order by hand, then records fills with bin/send "
        f"--fills; record a reject or override of {path.stem} as a decision with "
        "the operator's reason",
    }


def run_line_of(book: Book, run_id: str) -> tuple[Row, RunLine]:
    """The run line any runs file holds for `run_id`, decoded."""
    found = [row for row in all_runs(book) if row.get("run_id") == run_id]
    if not found:
        raise CommandError(f"no run line {run_id} in any runs file")
    row = found[-1]
    body = {key: value for key, value in row.items() if key not in ENVELOPE}
    return row, parse_model(RunLine, body, f"run line {run_id}")


def presence_of(book: Book, entry: Entry) -> Presence:
    """A listed file against its digest; unlike a read, logs no incident."""
    try:
        data = (book.root / entry.path).read_bytes()
    except FileNotFoundError:
        return Presence.VANISHED
    return Presence.INTACT if sha256_of(data) == entry.sha256 else Presence.CHANGED


def drift_of(
    book: Book,
    row: Row,
    line: RunLine,
    *,
    code: Code,
    manifest: Manifest,
) -> list[str]:
    """Every reason the rerun would not be the recorded run. Re-hashes every
    listed source file and peer series once: O(store bytes)."""
    problems: list[str] = []
    if code_hash(code) != line.code_hash:
        moved = code_drift(
            line.code_files,
            code_files(code),
            (line.engine.get("btm_finance", ""), btm_finance.__version__),
        )
        problems.append(f"code moved: {', '.join(moved) or 'code_hash differs'}")
    sources = [e for e in manifest.files if e.table != Table.RETURNS]
    stamp = str(row.get("ts", ""))
    problems += data_drift(
        line.data_snapshot,
        data_snapshot(manifest),
        [(e.path, presence_of(book, e)) for e in sources],
        [e.path for e in sources if e.loaded_at > stamp],
    )
    listed = {e.path: e for e in manifest.files}
    problems += peer_drift(
        {
            peer: presence_of(book, listed[returns_path(peer)])
            if returns_path(peer) in listed
            else None
            for peer in line.peers
        }
    )
    return problems


def recorded_peers(book: Book, manifest: Manifest, line: RunLine) -> Peers:
    """Exactly the line's peers, in its order, with the trial count it saw."""
    rows = {str(row.get("run_id")): row for row in all_runs(book)}
    sharpes: list[float] = []
    series = []
    for peer in line.peers:
        card = rows.get(peer, {}).get("scorecard")
        value = card.get("sharpe_net") if isinstance(card, dict) else None
        if isinstance(value, int | float):
            sharpes.append(float(value) / math.sqrt(PERIODS_PER_YEAR))
        found = read_returns(book, manifest, peer)
        if found is None:  # drift_of refused this already
            raise CommandError(f"peer {peer}: returns file not listed")
        series.append(found)
    return Peers(
        trials=line.scorecard.trials - 1,
        sharpes=tuple(sharpes),
        series=tuple(series),
        ids=line.peers,
    )


def cmd_repeat(args: argparse.Namespace) -> int:
    """Rerun one line from its own inputs: one `measure` run, nothing written."""
    book = open_book(args.book)
    name = name_of(args.strategy, "strategy")
    row, line = run_line_of(book, args.repeat)
    if line.strategy != name:
        raise CommandError(f"run {line.run_id} measured {line.strategy}, not {name}")
    manifest = read_manifest(book)
    problems = drift_of(book, row, line, code=code_of(book, name), manifest=manifest)
    if problems:
        raise CommandError(f"refused to repeat {line.run_id}: " + "; ".join(problems))
    config = parse_model(StrategyConfig, line.config, f"run {line.run_id} config")
    limits, preferences = load_limits(book), load_preferences(book)
    preferences = preferences.with_(exclusions=line.exclusions.model_dump())
    strategy = load_strategy(book.root, name).signal
    panel, events = assemble(book)
    names = scoped(book, panel.names, held_out=line.held_out)
    panel, events = panel.only(names), events.only(names)
    setting = Setting.of(panel, events, rules_of(limits, preferences, config))
    peers = recorded_peers(book, manifest, line)
    outcome = evaluate(setting, strategy, line.params, peers)
    compared, diffs = compare(
        line.scorecard.model_dump(mode="json"),
        outcome.scorecard.model_dump(mode="json"),
        line.tolerance,
    )
    current_engine = {
        "btm_finance": btm_finance.__version__,
        "numpy": np.__version__,
        "pyarrow": pa.__version__,
    }
    report = RepeatReport(
        run_id=line.run_id,
        strategy=name,
        reproduced=not diffs,
        tolerance=line.tolerance,
        compared=compared,
        diffs=tuple(diffs),
        advisories=tuple(engine_advisories(line.engine, current_engine)),
    )
    for note in report.advisories:
        signal(f"engine moved: {note}")
    emit(
        {
            "book": book.meta.id,
            **report.model_dump(mode="json"),
            "rule": "absolute when both values are at or below 1, relative above",
            "next": f"run {line.run_id} reproduces; cite it"
            if report.reproduced
            else "read each diff; a moved number is a method change to explain, "
            "never a run to measure again",
        }
    )
    return 0 if report.reproduced else 1


def run_facts(book: Book, strategy: str) -> RunFacts | None:
    """The strategy's newest research run line, as `check --live` reads it."""
    run = newest_run(all_runs(book), strategy)
    drawdown = None if run is None else card_number(run, "max_drawdown")
    if run is None or drawdown is None:
        return None
    card = run.get("scorecard")
    spread = card.get("spread_model") if isinstance(card, dict) else None
    half = spread.get("half_spread_mean") if isinstance(spread, dict) else None
    return RunFacts(
        run_id=str(run.get("run_id")),
        max_drawdown=drawdown,
        half_spread=float(half) if isinstance(half, int | float) else None,
    )


def approved_proposals(book: Book) -> dict[str, str]:
    """Approval file name to the proposal stem it names, from `approvals/`
    and `sent/`; a file naming none maps to its own stem."""
    found: dict[str, str] = {}
    for folder in ("approvals", "sent"):
        for path in sorted((book.root / folder).glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            stem = document.get("proposal") if isinstance(document, dict) else None
            found[path.name] = stem if isinstance(stem, str) else path.stem
    return found


def sleeve_fills(
    rows: Sequence[Row],
    name: str,
    status: Status,
    prices: Mapping[tuple[str, str, str], float],
    proposals: Mapping[str, str],
) -> tuple[Fill, ...]:
    """Paper sleeves count dry-run fills, probe and live ones real fills; a fill's
    reference is its proposal order's `price`, by approval, symbol, side."""
    paper = status is Status.PAPER
    chosen = [
        row
        for row in rows
        if row.get("strategy") == name and bool(row.get("dry_run")) is paper
    ]

    def reference(row: Row) -> float | None:
        approval = str(row.get("approval", ""))
        stem = proposals.get(approval, Path(approval).stem)
        return prices.get((stem, str(row.get("symbol")), str(row.get("side"))))

    return tuple(fill_of(row, reference(row)) for row in chosen)


def modeled(
    book: Book, name: str, setting_of: Callable[[StrategyConfig], Setting]
) -> tuple[tuple[Days, Floats] | None, str | None]:
    """`measure`'s base path with current code and params, or why not."""
    folder = book.root / "strategies" / name
    try:
        config = parse_model(
            StrategyConfig, read_json(folder / "config.json"), f"strategies/{name}"
        )
        strategy = load_strategy(book.root, name).signal
        path = model_path(setting_of(config), strategy, dict(config.params))
    except CommandError as err:
        return None, f"no model path: {err}"
    return path, None if path is not None else "no model path: signal held nothing"


def live_view(book: Book, today: date) -> LiveReport:
    """Every paper, probe, or live sleeve: one model simulation each, O(S (T N + R N
    L)), plus O(D S + F) per realized path; appends incidents only."""
    limits, preferences = load_limits(book), load_preferences(book)
    tracked = [
        (s.name, s.status)
        for s in strategies(book)
        if s.status in {Status.PAPER, Status.PROBE, Status.LIVE}
    ]
    rows: list[LiveRow] = []
    last_bar: str | None = None
    if tracked:
        panel, events = assemble(book)
        rf = np.nan_to_num(on_dates(events, FACTORS, "rf", panel.dates), nan=0.0)
        last = int(panel.dates[-1])
        last_bar = date_of(last).isoformat()
        research = scoped(book, panel.names, held_out=False)
        model_panel, model_events = panel.only(research), events.only(research)

        def setting_of(config: StrategyConfig) -> Setting:
            rules = rules_of(limits, preferences, config)
            return Setting.of(model_panel, model_events, rules)

        prices = reference_prices(
            {
                day: read_json(book.root / "proposals" / f"{day}.json")
                for day in proposal_dates(book)
            }
        )
        fills = [
            row
            for row in current(kind_rows(book, Kind.FILL))
            if row.get("strategy") != "opening"
        ]
        approved = approved_proposals(book)
        own = {
            name: sleeve_fills(fills, name, status, prices, approved)
            for name, status in tracked
        }
        sleeves: dict[str, Sleeve | None] = {
            name: realized(own[name], panel, rf) for name, _ in tracked
        }
        stale = trading_days_after(last, today)
        bounds = Bounds(
            drawdown_multiple=limits.thresholds.drawdown_review_multiple,
            underperform_months=limits.thresholds.underperform_months,
            tracking=limits.thresholds.tracking_error,
            commission=limits.commission_bps / 1e4,
        )
        for name, status in tracked:
            path, why = modeled(book, name, setting_of)
            run = run_facts(book, name)
            notes = [note for note in (why,) if note]
            if run is None:
                notes.append("no research run line: drawdown and slippage unbounded")
            if not own[name]:
                notes.append(
                    f"no {'dry-run' if status is Status.PAPER else 'real'} fills"
                )
            case = Case(
                strategy=name,
                status=status,
                fills=own[name],
                sleeve=sleeves[name],
                model=path,
                baseline=None if name == "baseline" else sleeves.get("baseline"),
                run=run,
                stale_days=stale,
                notes=tuple(notes),
            )
            rows.append(row_of(case, bounds))
    found = breaches_of(rows)
    new, repeated = fresh(found, current(kind_rows(book, Kind.INCIDENT)), today)
    stamp = now_iso()
    records = [
        {
            "id": make_id(["live", breach.kind.value, *ascii_words(breach.strategy)]),
            "ts": stamp,
            "kind": breach.kind.value,
            "strategy": breach.strategy,
            "value": breach.value,
            "limit": breach.limit,
            "as_of": today.isoformat(),
            "by": "check --live",
        }
        for breach in new
    ]
    if records:
        append_ledger(book.path_of(Kind.INCIDENT), records)
    return LiveReport(
        book=book.meta.id,
        as_of=today.isoformat(),
        last_bar=last_bar,
        strategies=tuple(rows),
        breaches=tuple(found),
        new=tuple(str(record["id"]) for record in records),
        repeated=len(repeated),
        report=report_of(rows, today, last_bar),
        next=LIVE_NEXT,
    )


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
    start.add_argument(
        "--held-out",
        type=Path,
        help="held-out list path outside the book; default under XDG_STATE_HOME",
    )

    schema = commands.add_parser("schema", help="print every record shape")
    schema.set_defaults(func=cmd_schema)

    record = commands.add_parser("record", help="accept one batch through the gate")
    record.set_defaults(func=cmd_record)
    record.add_argument("book", help="book directory")
    add_slot(record, BATCH, ", ".join(BATCH_KEYS))

    check = commands.add_parser(
        "check", help="continue view, a strategy's standing, or a proposal"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("book", help="book directory")
    check.add_argument(
        "target",
        nargs="?",
        help="strategy, run id, or proposal date",
    )
    check.add_argument(
        "--live", action="store_true", help="weekly tracking of paper and live sleeves"
    )
    check.add_argument(
        "--brief", action="store_true", help="daily brief: at most twelve lines"
    )
    check.add_argument(
        "--today", type=iso_day, help="tests only: the day --live measures from"
    )

    measure = commands.add_parser("measure", help="measure a registered strategy")
    measure.set_defaults(func=cmd_measure)
    measure.add_argument("book", help="book directory")
    measure.add_argument("strategy", help="directory under strategies/")
    measure.add_argument(
        "--held-out", action="store_true", help="the human's one run on held-out names"
    )
    measure.add_argument("--agent", help="append to ledger/runs/<agent>.jsonl")
    measure.add_argument(
        "--repeat", metavar="RUN_ID", help="rerun a recorded run; writes nothing"
    )

    recommend = commands.add_parser("recommend", help="write the rebalance proposal")
    recommend.set_defaults(func=cmd_recommend)
    recommend.add_argument("book", help="book directory")
    recommend.add_argument("date", type=iso_day, help="rebalance date, YYYY-MM-DD")
    recommend.add_argument(
        "--force", action="store_true", help="write <date>.<n>.json beside the first"
    )

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
