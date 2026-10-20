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
from btm_finance.advising import (
    Account,
    Candidate,
    Inputs,
    Previous,
    Proposal,
    Quote,
    Skipped,
    account_of,
    approval_of,
    propose,
)
from btm_finance.api import Market
from btm_finance.batch import BATCH_KEYS, SCHEMA, Context, RecordResult, expand_batch
from btm_finance.data.assemble import UNIVERSE as UNIVERSE_FILE
from btm_finance.data.assemble import assemble, parse_universe
from btm_finance.data.panel import Events, Panel
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
    Action,
    Cadence,
    Exclusions,
    Limits,
    Preferences,
    Status,
    StrategyConfig,
)
from btm_finance.scaffold import member, scaffold
from btm_finance.scorecard import RunLine, Span
from btm_finance.scoring import (
    Peers,
    Prepared,
    Setting,
    bounds,
    evaluate,
    rules_of,
    target_weights,
)
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
    previous_proposal,
    proposal_dates,
    proposal_target,
    proposal_versions,
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
        when = date.fromisoformat(args.target)
    except ValueError:
        emit(standing_view(book, args.target).model_dump(mode="json"))
        return 0
    emit(proposal_view(book, when))
    return 0


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
            "approval": '{"date": "YYYY-MM-DD", "proposal": "<proposal stem>", '
            '"orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, '
            '"price": 12.5, "adv_participation": 0.004, "strategy": "<name>", '
            '"limit": null}]} (check <date> prints it as approval_template; '
            "the operator writes it; bin/send reads it)",
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
    """The scoped data and the as-of row `advise` reads every sleeve on."""

    panel: Panel
    events: Events
    prep: Prepared
    row: int


def candidate(  # noqa: PLR0913 - one sleeve's inputs, read once each
    book: Book,
    limits: Limits,
    preferences: Preferences,
    day: Day,
    *,
    run: Row,
    account: Account,
) -> Candidate:
    """The sleeve's weights on the as-of row through `Market.at` and
    `target_weights`, as `score` sets them; vol from the run's net series."""
    name = str(run.get("strategy"))
    folder = book.root / "strategies" / name
    config_bytes = file_bytes(folder / "config.json")
    config = parse_model(
        StrategyConfig,
        read_json(folder / "config.json"),
        f"strategies/{name}/config.json",
    )
    source = file_bytes(folder / "signal.py")
    module = f"btm_strategy_{name.replace('-', '_')}_{secrets.token_hex(4)}"
    strategy = load_signal(
        source.decode("utf-8", errors="replace"), f"strategies/{name}/signal.py", module
    )
    rules = rules_of(limits, preferences, config)
    setting = Setting(day.panel, day.events, day.prep, rules)
    market = Market.at(day.panel, day.events, int(day.panel.dates[day.row]))
    try:
        raw = strategy(market, dict(config.params))
    except Exception as err:  # the strategy's failure, named for its author
        raise CommandError(f"{name} signal raised: {err!r}") from err
    index = {symbol: column for column, symbol in enumerate(day.panel.names)}
    weights, unknown = target_weights(raw, market, setting, index, day.row)
    series = read_returns(book, read_manifest(book), str(run.get("run_id")))
    vol = None
    if series is not None and len(series[1]) > 1:
        vol = float(np.std(series[1], ddof=1)) * math.sqrt(PERIODS_PER_YEAR)
    changed = code_hash(source, config_bytes) != run.get("code_hash")
    if changed:
        signal(f"{name}: signal.py or config.json changed since run {run['run_id']}")
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


def sleeves_of(book: Book) -> tuple[list[tuple[Row, Account]], list[Skipped]]:
    """Paper and live strategies with their newest research run line."""
    runs = all_runs(book)
    chosen: list[tuple[Row, Account]] = []
    skipped: list[Skipped] = []
    for found in strategies(book):
        account = account_of(found.status)
        if account is None:
            continue
        run = newest_run(runs, found.name)
        if run is None:
            reason = f"{found.status} with no run line: score {found.name} first"
            signal(f"sleeve {found.name} skipped: {reason}")
            skipped.append(Skipped(strategy=found.name, reason=reason))
            continue
        chosen.append((run, account))
    return chosen, skipped


def cmd_advise(args: argparse.Namespace) -> int:
    """Writes `proposals/<date>.json` and nothing else."""
    book = open_book(args.book)
    when: date = args.date
    chosen, skipped = sleeves_of(book)
    if not chosen:
        named = ", ".join(s.strategy for s in skipped)
        raise CommandError(
            "no sleeve: no strategies/*/status reads paper or live with a run line"
            + (f" (skipped {named})" if named else "")
            + "; the operator sets status, the agent scores"
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
    candidates = tuple(
        candidate(book, limits, preferences, day, run=run, account=account)
        for run, account in chosen
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
            fills=current(kind_rows(book, Kind.FILL)),
            previous=previous_of(book, when.isoformat()),
        )
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(target, json.dumps(proposal.model_dump(mode="json"), indent=2) + "\n")
    for cut in proposal.cuts:
        signal(
            f"{cut.symbol} ({cut.strategy}) cut from {cut.wanted} to {cut.kept}: "
            f"ADV participation {cut.adv_participation:.4g} over {cut.bound}"
        )
    emit(
        {
            "book": book.meta.id,
            "proposal": book.relative(target),
            "as_of": proposal.as_of,
            "sleeves": {s: v.weight for s, v in proposal.sleeves.items()},
            "skipped": [s.model_dump(mode="json") for s in proposal.skipped],
            "orders": len(proposal.orders),
            "cuts": len(proposal.cuts),
            "carried": len(proposal.carried),
            "unmanaged": len(proposal.unmanaged),
            "summary": proposal.summary.model_dump(mode="json"),
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
            f"{proposal.date}; load prices, then advise again with --force"
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
                "sharpe_net": None if run is None else card_number(run, "sharpe_net"),
                "max_drawdown": None
                if run is None
                else card_number(run, "max_drawdown"),
                "weight": 0.0,
                "note": "baseline is no sleeve here: its status is not paper or live",
            }
        )
    return sorted(rows, key=lambda row: row["strategy"] != BASELINE)


def proposal_view(book: Book, when: date) -> dict[str, Any]:
    """`check <date>`: blockers, baseline, stale flags, then the diff."""
    versions = proposal_versions(book, when.isoformat())
    if not versions:
        raise CommandError(f"no proposal for {when}: run advise {when} first")
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
        f"it; record a reject or override of {path.stem} as a decision with "
        "the operator's reason",
    }


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
        "check", help="continue view, a strategy's standing, or a proposal"
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("book", help="book directory")
    check.add_argument(
        "target",
        nargs="?",
        help="strategy, run id, or proposal date",
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

    advise = commands.add_parser("advise", help="write the rebalance proposal")
    advise.set_defaults(func=cmd_advise)
    advise.add_argument("book", help="book directory")
    advise.add_argument("date", type=iso_day, help="rebalance date, YYYY-MM-DD")
    advise.add_argument(
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
