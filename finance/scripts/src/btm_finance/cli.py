"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
import inspect
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
from pydantic import BaseModel

import btm_finance
from btm_corekit import (
    BATCH,
    REFS_SCHEMA,
    CommandError,
    Diagnostic,
    Optional,
    Parser,
    Required,
    add_slot,
    ascii_words,
    count_lines,
    dispatch,
    emit,
    gated,
    make_id,
    now_iso,
    parse_model,
    rejection,
    run_cli,
    signal,
    text,
    write_atomic,
)
from btm_corekit.cli import PAD_TYPES
from btm_finance import fills as pasted_fills
from btm_finance import loader
from btm_finance.api import FACTORS, Market, ledger, on_dates
from btm_finance.batch import BATCH_KEYS, SCHEMA, Context, RecordResult, expand_batch
from btm_finance.brief import (
    ANSWER,
    WEEK,
    Bet,
    Open,
    Owed,
    asked_today,
    brief,
    justifying,
)
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
    IGNORED,
    SCORED,
    Kind,
    Numbered,
    Row,
    closed_of,
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
    commission_of,
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
    commission_ceiling,
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
    propose,
    real,
)
from btm_finance.repeat import (
    Presence,
    RepeatReport,
    code_drift,
    code_files,
    code_hash,
    compare,
    data_drift,
    peer_drift,
)
from btm_finance.repeat import advisories as engine_advisories
from btm_finance.scaffold import DEFAULT_CAP, scaffold
from btm_finance.scorecard import RunLine, Span, UniverseKind
from btm_finance.standing import Evidence, StandingView, standing_of
from btm_finance.store import (
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
from btm_finance.views import (
    by_status,
    families,
    next_step,
    open_hypotheses,
    open_proposals,
    overdue,
    trials_today,
    unscored,
)

UNIVERSE = Optional("universe", inline=False)
CONFIG = Optional("config", inline=False)
FILLS = Optional("fills", inline=False)
FILLS_SLOT = Required("fills", inline=False)  # names the flag in a rejection
SCHEMA_KINDS = ("record", "run", "pad", "strategy")
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
    root: Path, cap: int | None, universe: str | None, held_out: Path | None = None
) -> dict[str, Any]:
    """Make the book, then register the baseline hypothesis."""
    receipt = scaffold(root, cap, universe, held_out)
    book = open_book(str(root))
    hypotheses = {"hypotheses": [baseline_hypothesis(datetime.now(UTC).date())]}
    result = recorded(book, hypotheses)
    receipt["wrote"] += ["ledger/hypotheses.jsonl"]
    receipt["new"] = result.new["hypotheses"]
    return receipt


def cmd_start(args: argparse.Namespace) -> int:
    emit(
        start(
            Path(args.book).expanduser(), args.cap, text(UNIVERSE, args), args.held_out
        )
    )
    return 0


def utc_today() -> date:
    """Today, UTC."""
    return datetime.now(UTC).date()


def ids_of(path: Path, key: str = "id") -> list[str]:
    return [
        row[key]
        for _, row in rows_of(read_bytes(path))
        if isinstance(row.get(key), str)
    ]


def run_ids(book: Book) -> list[str]:
    return [run_id for path in run_files(book) for run_id in ids_of(path, "run_id")]


def context_of(book: Book) -> Context:
    """Live book state the gate resolves a batch against."""
    limits = load_limits(book)
    kinds = (Kind.HYPOTHESIS, Kind.CRITIQUE, Kind.DECISION, Kind.FILL)
    ids = {kind: ids_of(book.path_of(kind)) for kind in kinds}
    return Context(
        families=frozenset(limits.families),
        min_holding_days=limits.min_holding_days,
        ids={**ids, Kind.RUN: run_ids(book)},
        strategies=[strategy.name for strategy in strategies(book)],
        proposals=proposal_dates(book),
        book=book.meta.id,
    )


def committed(book: Book, result: RecordResult) -> dict[str, int]:
    """Staged rows appended per kind; accepted counts per kind."""
    accepted: dict[str, int] = {}
    for kind, rows in sorted(result.staged.items()):
        append_ledger(book.path_of(kind), rows)
        accepted[kind.value] = len(rows)
    return accepted


def recorded(book: Book, batch: dict[str, Any]) -> RecordResult:
    """A batch the program builds itself, through the same gate; any problem
    is a defect, so it raises."""
    result = expand_batch(context_of(book), batch, make_id, now_iso())
    if result.problems:
        raise CommandError(f"record refused {batch}: {result.problems}")
    committed(book, result)
    return result


def cmd_record(args: argparse.Namespace) -> int:
    book = open_book(args.book)

    def expand(batch: dict[str, Any]) -> RecordResult:
        return expand_batch(context_of(book), batch, make_id, now_iso())

    def commit(result: RecordResult) -> dict[str, Any]:
        return {
            "book": book.meta.id,
            "accepted": committed(book, result),
            "new": result.new,
            "next": "run check for the continue view",
        }

    sugar = fills_batch(book, args)
    if sugar is None:
        return gated(BATCH, args, "book", expand, commit)
    batch, problems = sugar
    if problems:
        emit(rejection(problems, "book", FILLS_SLOT))
        return 1
    result = expand(batch)
    for advisory in result.advisories:
        signal(advisory)
    if result.problems:
        emit(rejection(result.problems, "book", FILLS_SLOT))
        return 1
    emit(commit(result))
    return 0


def fills_batch(
    book: Book, args: argparse.Namespace
) -> tuple[dict[str, Any], list[Diagnostic]] | None:
    """`--fills:file` against `--proposal` as a `fills` batch and the problems
    refusing it; None when the batch slot carries the batch."""
    raw = text(FILLS, args)
    if args.proposal is None:
        if raw is not None:
            raise CommandError("--fills:file needs --proposal <stem>")
        return None
    if args.batch_file is not None or getattr(args, "stdin", None) == "batch":
        raise CommandError("--proposal builds the batch; drop --batch")
    if raw is None:
        raise CommandError("--proposal needs --fills:file <table>")
    orders = proposal_orders(book, args.proposal)
    rows = pasted_fills.table_rows(raw, "the fills")
    made, problems = pasted_fills.pasted(rows, orders, utc_today().isoformat())
    return {"fills": [fill | {"proposal": args.proposal} for fill in made]}, problems


def proposal_orders(book: Book, stem: str) -> list[Any]:
    """The `orders` of `proposals/<stem>.json`; refuses a stem naming no file."""
    folder = (book.root / "proposals").resolve()
    target = (folder / f"{stem}.json").resolve()
    if target.parent != folder or not target.is_file():
        raise CommandError(f"--proposal {stem} names no file under proposals/")
    found = read_json(target)
    orders = found.get("orders") if isinstance(found, dict) else None
    return orders if isinstance(orders, list) else []


def cmd_check(args: argparse.Namespace) -> int:
    if args.schema is not None:
        emit(schema_view(args.schema))
        return 0
    if args.book is None:
        raise CommandError("check needs a book path; only --schema runs without one")
    return book_check(open_book(args.book), args)


def today_of(args: argparse.Namespace) -> date:
    """`--today` when a test sets it, else today (UTC)."""
    found: date | None = args.today
    return found or datetime.now(UTC).date()


def book_check(book: Book, args: argparse.Namespace) -> int:
    """Continue view, `--live`, `--brief`, a standing, or a proposal."""
    if args.live:
        emit(live_view(book, today_of(args)).model_dump(mode="json"))
        return 0
    if args.brief:
        if args.target is not None:
            raise CommandError("--brief takes no target; run check <book> --brief")
        emit(brief_view(book, today_of(args)))
        return 0
    if args.target is None:
        emit(continue_view(book, today_of(args)))
        return 0
    try:
        when = date.fromisoformat(args.target)
    except ValueError:
        standing = standing_view(book, args.target)
        emit(standing.model_dump(mode="json"))
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


def decisions_of(book: Book) -> list[Row]:
    """Live decisions, an older book's `scored` lines read as `close`
    decisions among them, oldest first by `ts`."""
    scored = rows_of(read_bytes(book.ledger / SCORED))
    rows = kind_rows(book, Kind.DECISION) + [
        (number, closed_of(row)) for number, row in scored
    ]
    return sorted(current(rows), key=lambda row: str(row.get("ts", "")))


def fill_proposal(row: Row) -> str | None:
    """The proposal stem a fill names; an older fill's `approval` stem reads
    as one."""
    named = row.get("proposal")
    if isinstance(named, str):
        return named
    approval = row.get("approval")
    if not isinstance(approval, str):
        return None
    return approval.rpartition("/")[2].removesuffix(".json")


def standing_view(book: Book, target: str) -> StandingView:
    """`check <strategy>` or `check <run id>`: standing of the newest measured
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
        status=found.status if found else Status.RESEARCH,
        raw_status=found.raw if found else "",
    )
    return standing_of(evidence, load_limits(book))


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


def ignored_files(book: Book) -> None:
    """One signal per older ledger file no view reads."""
    for name in IGNORED:
        if (book.ledger / name).is_file():
            signal(f"ledger/{name} holds an older kind no view reads; ignored")


def continue_view(book: Book, today: date) -> dict[str, Any]:
    """Every ledger file replayed: O(ledger bytes)."""
    limits = load_limits(book)
    warnings = ledger_warnings(book)
    if warnings:
        signal(f"{len(warnings)} ledger warning(s) under warnings; tell the operator")
    ignored_files(book)
    runs = all_runs(book)
    hypothesis_lines = kind_rows(book, Kind.HYPOTHESIS)
    hypotheses, decisions = current(hypothesis_lines), decisions_of(book)
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
    proposals = open_proposals(proposal_dates(book), decisions, today)
    pending = len(open_hypotheses(hypotheses, runs, decisions))
    retired = frozenset(name for name, s in known.items() if s is Status.RETIRED)
    late = [
        *overdue(hypotheses, decisions, retired, today),
        *unscored(hypotheses, decisions, today),
    ]
    if late:
        signal(f"{len(late)} overdue or unscored hypothesis(es) under warnings")
    budgets = families(
        limits, hypotheses, runs, decisions, [row for _, row in hypothesis_lines]
    )
    return {
        "book": book.meta.id,
        "as_of": now_iso(),
        "strategies": {**by_status(known), "unknown": unknown},
        "families": budgets,
        "proposals": proposals,
        "incidents": current(kind_rows(book, Kind.INCIDENT))[-INCIDENT_TAIL:],
        "pad": {"entries": count_lines(book.root / PAD_DIR / "scratch.jsonl")},
        "trials_today": {
            "used": trials_today(runs, today),
            "cap": limits.trials_per_day,
        },
        "warnings": [*warnings, *late],
        "next": next_step(hypotheses, pending, proposals, late, budgets),
    }


def unfilled(book: Book, decisions: Sequence[Row], today: date) -> str | None:
    """The newest proposal stem an `approve` decision of the last 7 days
    names and no real fill names. O(D + F)."""
    named = {
        stem
        for row in current(kind_rows(book, Kind.FILL))
        if real(row) and (stem := fill_proposal(row)) is not None
    }
    found: list[str] = []
    for row in decisions:
        stamp = str(row.get("ts", ""))[:10]
        try:
            age = (today - date.fromisoformat(stamp)).days
        except ValueError:
            continue
        subject = str(row.get("subject"))
        if (
            row.get("action") == Action.APPROVE.value
            and subject not in named
            and 0 <= age < WEEK
        ):
            found.append(subject)
    return max(found, default=None)


def owed_of(book: Book, view: Mapping[str, Any], today: date) -> Owed:
    """What the operator owes, in `Reply` order: fills, an answer to the
    oldest open proposal, a yes to a change asked today (`question` pad entry
    of today no `answer` names), a word on the first overdue or unscored bet."""
    pad = rows_of(read_bytes(book.root / PAD_DIR / "scratch.jsonl"))
    asked = asked_today((row for _, row in pad), today)
    late = [w for w in view["warnings"] if w.get("problem") in {"overdue", "unscored"}]
    first = late[0] if late else None
    return Owed(
        unfilled=unfilled(book, decisions_of(book), today),
        unanswered=view["proposals"][0]["date"] if view["proposals"] else None,
        pending=asked,
        late=None
        if first is None
        else (
            str(first.get("strategy")),
            str(first.get("falsifier_by") or first.get("due")),
        ),
    )


def brief_view(book: Book, today: date) -> dict[str, Any]:
    """`check --brief`: the continue view cut to at most twelve lines."""
    view = continue_view(book, today)
    runs = {str(row.get("run_id")): row for row in all_runs(book)}
    opened: list[Open] = []
    for entry in view["proposals"]:
        path = book.root / "proposals" / f"{entry['date']}.json"
        document = read_json(path) if path.is_file() else {}
        sleeves = document.get("sleeves") if isinstance(document, dict) else None
        bets: list[Bet] = []
        for name, sleeve in (sleeves if isinstance(sleeves, dict) else {}).items():
            run = runs.get(str(sleeve.get("run_id")))
            odds = (hypothesis_for(book, run, name) or {}).get("odds")
            bets.append(
                Bet(
                    strategy=name,
                    tier=str(sleeve.get("tier") or "-"),
                    weight=sleeve.get("weight"),
                    odds=odds if isinstance(odds, dict) else None,
                    number=justifying(sleeve.get("sharpe_net")),
                )
            )
        opened.append(Open(entry["date"], entry["age_days"], tuple(bets)))
    late = Counter(w.get("problem") for w in view["warnings"])
    return brief(
        proposals=opened,
        incidents=current(kind_rows(book, Kind.INCIDENT)),
        overdue=late["overdue"],
        unscored=late["unscored"],
        owed=owed_of(book, view, today),
        next_action=view["next"],
        today=today,
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


def market_accessors() -> dict[str, str]:
    """Each public `Market` member but its constructor, as signature or type
    then docstring; a field's meaning lives in the class docstring."""
    found: dict[str, str] = {}
    for name in dir(Market):
        member = inspect.getattr_static(Market, name)
        if name.startswith("_") or isinstance(member, classmethod):
            continue
        if isinstance(member, property):
            found[name] = f"{name}: {inspect.getdoc(member)}"
        elif callable(member):
            shown = str(inspect.signature(member)).replace("(self, ", "(")
            found[name] = f"{name}{shown}: {inspect.getdoc(member)}"
        else:
            found[name] = f"{name}: {Market.__annotations__[name]}"
    return found


def strategy_schema() -> dict[str, Any]:
    """`check --schema strategy`: the `signal.py` contract, derived from the
    loader's module docstring, `Market`'s docstrings, and `StrategyConfig`."""
    return {
        "signal": inspect.getdoc(loader),
        "market": {"Market": inspect.getdoc(Market), **market_accessors()},
        "config": StrategyConfig.model_json_schema(),
    }


SCHEMA_VIEW: dict[str, dict[str, Any]] = {
    "record": {
        "record_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
        "sequence": "hypotheses, critiques, decisions, fills; a decision may "
        "name a hypothesis made earlier in the batch",
        "ledger_line": f"{', '.join(ENVELOPE)} (stamped by record), then the record",
        "corrections": '"supersedes": "<id>" on a new line; newest wins',
        "refs": REFS_SCHEMA + "; receipts echo every new id under new",
        "fill_table": "CSV with header symbol,side,quantity,price,date "
        "(optional strategy), or a JSON list of objects with those keys; "
        "record --fills:file <table> --proposal <stem> turns it into fills, "
        "strategy taken from the proposal's one order of that symbol and side "
        "when absent",
    },
    "run": {
        "run_line": f"{', '.join(RunLine.model_fields)} (written by measure only)",
        "strategy_config": "check --schema strategy",
    },
    "pad": {
        "path": f"{PAD_DIR.as_posix()}/scratch.jsonl; agent appends and greps "
        "it with its own file tools; never gated, never read by record",
        "line": '{"ts": "<ISO 8601>", "type": "<type>", ...any fields}',
        "types": {
            **{name: meaning for name, meaning in PAD_TYPES.items() if name != "known"},
            "heartbeat": "one wake of the always-on loop: item, outcome (one "
            "line), next_wake (ISO)",
            ANSWER: "operator's reply to a question: question (the answered "
            "question line's ts), text (operator's words); closes its yes line",
        },
    },
    "strategy": strategy_schema(),
}


def schema_kind(raw: str) -> str:
    if raw not in (*SCHEMA_KINDS, "all"):  # argparse types the const too
        raise argparse.ArgumentTypeError(
            f"{raw!r} is no shape; name one of {'|'.join(SCHEMA_KINDS)}"
        )
    return raw


def schema_view(kind: str) -> dict[str, Any]:
    """`check --schema [kind]`: one kind's shapes, or every kind's."""
    return SCHEMA_VIEW if kind == "all" else {kind: SCHEMA_VIEW[kind]}


def name_of(raw: str, what: str) -> str:
    if not NAME.fullmatch(raw):
        raise CommandError(
            f"{what} {raw!r}: use lowercase letters, digits, '-', '_'; never a path"
        )
    return raw


def code_of(book: Book, name: str) -> dict[str, bytes]:
    """`signal.py`, `config.json`, and each book-local module `signal.py`
    reaches, by book-relative path, to its bytes."""
    folder = f"strategies/{name}"
    reach = strategy_reach(book.root, name)
    paths = {f"{folder}/signal.py", f"{folder}/config.json", *reach.modules}
    return {path: file_bytes(book.root / path) for path in sorted(paths)}


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


def policy_gates(
    book: Book, limits: Limits, config: StrategyConfig, *, held_out: bool
) -> list[str]:
    """Each policy refusal `--reason` runs past; `--held-out` passes the
    daily cap."""
    gates: list[str] = []
    if config.holding_days < limits.min_holding_days:
        gates.append(
            f"holding_days {config.holding_days} is under "
            f"limits.min_holding_days {limits.min_holding_days}"
        )
    if held_out:
        return gates
    spent = trials_today(all_runs(book), utc_today())
    if spent >= limits.trials_per_day:
        gates.append(
            f"{spent} run line(s) dated today reach limits.trials_per_day "
            f"{limits.trials_per_day}"
        )
    return gates


def reason_text(raw: str) -> str:
    if not raw.strip():
        raise argparse.ArgumentTypeError("--reason needs text naming the gate")
    return raw.strip()


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
    if config.family_id != hypothesis.get("family_id"):
        raise CommandError(
            f"config family_id {config.family_id} differs from hypothesis "
            f"{hypothesis.get('id')} family {hypothesis.get('family_id')}"
        )
    code = code_of(book, name)
    gates = policy_gates(book, limits, config, held_out=args.held_out)
    if gates and args.reason is None:
        raise CommandError(
            f"refused before running: {'; '.join(gates)}; next: fix it, or "
            'measure again with --reason "<why this run answers the gate>"'
        )
    for gate in gates:
        signal(f"--reason runs past {gate}; stamped as override_reason")
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
        engine=btm_finance.__version__,
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
        imports=loaded.imports,
        universe=UniverseKind.MEMBERSHIP if any(panel.members) else UniverseKind.STATIC,
        override_reason=args.reason if gates else None,
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
    real_fills: Sequence[Fill],
    limits: Limits,
    through: int,
) -> Tier:
    """Tier from the sleeve's real fills through `through` against one model
    simulation."""
    model = model_path(setting, strategy, params)
    return tier_of(
        seasoning(real_fills, setting.panel, setting.prep.rf, model, through),
        days=limits.thresholds.tracked_days,
        bound=limits.thresholds.tracking_error,
    )


def candidate(  # noqa: PLR0913 - one sleeve's inputs, read once each
    book: Book,
    limits: Limits,
    preferences: Preferences,
    day: Day,
    *,
    run: Row,
    fills: Sequence[Row],
) -> Candidate:
    """The sleeve's weights on the as-of row through `Market.at` and
    `target_weights`, as `measure` sets them; vol from the run's net series;
    tier from its real fills, `entry` before any."""
    name = str(run.get("strategy"))
    folder = book.root / "strategies" / name
    config = parse_model(
        StrategyConfig,
        read_json(folder / "config.json"),
        f"strategies/{name}/config.json",
    )
    strategy = load_strategy(book.root, name).signal
    rules = rules_of(limits, preferences, config)
    setting = Setting(
        day.panel,
        day.events,
        day.prep,
        rules,
        commission_of(rules.commission_bps, day.panel),
    )
    market = Market.at(day.panel, day.events, int(day.panel.dates[day.row]))
    try:
        raw = strategy(market, dict(config.params))
    except Exception as err:  # the strategy's failure, named for its author
        raise CommandError(f"{name} signal raised: {err!r}") from err
    index = {symbol: column for column, symbol in enumerate(day.panel.names)}
    chosen = target_weights(raw, market, setting, index, day.row)
    weights, unknown = chosen.weights, chosen.unknown
    own = sleeve_fills(fills, name, {})
    tier = (
        sleeve_tier(
            setting,
            strategy,
            dict(config.params),
            real_fills=own,
            limits=limits,
            through=int(day.panel.dates[day.row]),
        )
        if own
        else Tier.BACKTEST
    )
    series = read_returns(book, read_manifest(book), str(run.get("run_id")))
    vol = None
    if series is not None and len(series[1]) > 1:
        vol = float(np.std(series[1], ddof=1)) * math.sqrt(PERIODS_PER_YEAR)
    changed = code_changed(book, name, run)
    if changed:
        signal(f"{name}: strategy code changed since run {run['run_id']}")
    return Candidate(
        strategy=name,
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
        entry=not own,
    )


def code_changed(book: Book, name: str, run: Row) -> bool:
    """The strategy's code moved since the run: `code_hash` differs; a line
    without one reads moved."""
    return code_hash(code_of(book, name)) != run.get("code_hash")


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
            exchange=panel.exchange[column].value,
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


def sleeves_of(book: Book) -> tuple[list[Row], list[Skipped]]:
    """Live strategies with their newest research run line."""
    runs = all_runs(book)
    chosen: list[Row] = []
    skipped: list[Skipped] = []
    for found in strategies(book):
        if found.status is not Status.LIVE:
            continue
        run = newest_run(runs, found.name)
        if run is None:
            reason = f"{found.status} with no run line: measure {found.name} first"
            signal(f"sleeve {found.name} skipped: {reason}")
            skipped.append(Skipped(strategy=found.name, reason=reason))
            continue
        chosen.append(run)
    return chosen, skipped


def cmd_recommend(args: argparse.Namespace) -> int:
    """Writes `proposals/<date>.json` and nothing else."""
    book = open_book(args.book)
    when: date = args.date
    chosen, skipped = sleeves_of(book)
    if not chosen:
        named = ", ".join(s.strategy for s in skipped)
        raise CommandError(
            "no sleeve: no strategies/*/status reads live with a run line"
            + (f" (skipped {named})" if named else "")
            + "; status changes on the operator's word, the agent measures"
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
        candidate(book, limits, preferences, day, run=run, fills=fills)
        for run in chosen
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
                "note": "baseline is no sleeve here: its status is not live",
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
    return {
        "book": book.meta.id,
        "proposal": book.relative(path),
        "blockers": blockers,
        "baseline": comparison(book, proposal),
        "stale": stale_flags(proposal, load_preferences(book).cadence, today),
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
                "carried_from": o.carried_from,
            }
            for o in proposal.orders
        ],
        "cuts": [cut.model_dump(mode="json") for cut in proposal.cuts],
        "unmanaged": [h.model_dump(mode="json") for h in proposal.unmanaged],
        "skipped": [s.model_dump(mode="json") for s in proposal.skipped],
        "summary": proposal.summary.model_dump(mode="json"),
        "next": "read blockers to the operator first, baseline beside each "
        "sleeve, then wait for a reply; record the approve, reject, or "
        f"override decision on {path.stem} with the reply verbatim as reason",
    }


def run_line_of(book: Book, run_id: str) -> tuple[Row, RunLine]:
    """The run line any runs file holds for `run_id`, decoded."""
    found = [row for row in all_runs(book) if row.get("run_id") == run_id]
    if not found:
        raise CommandError(f"no run line {run_id} in any runs file")
    row = found[-1]
    body = {key: value for key, value in row.items() if key not in ENVELOPE}
    engine = body.get("engine")
    if isinstance(engine, dict):  # an older line: skill commit and libraries
        body["engine"] = str(engine.get("btm_finance", ""))
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
    manifest: Manifest,
) -> list[str]:
    """Every reason the rerun would not be the recorded run. Re-hashes the
    code, every listed source file, and every peer series once: O(store
    bytes)."""
    problems: list[str] = []
    code = code_of(book, line.strategy)
    if line.code_hash is None:
        problems.append("run line predates code hashes")
    elif code_hash(code) != line.code_hash:
        moved = code_drift(line.code_files, code_files(code))
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
    problems = drift_of(book, row, line, manifest=manifest)
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
    report = RepeatReport(
        run_id=line.run_id,
        strategy=name,
        reproduced=not diffs,
        tolerance=line.tolerance,
        compared=compared,
        diffs=tuple(diffs),
        advisories=tuple(engine_advisories(line.engine, btm_finance.__version__)),
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


def sleeve_fills(
    rows: Sequence[Row], name: str, prices: Mapping[tuple[str, str, str], float]
) -> tuple[Fill, ...]:
    """The sleeve's real fills; a fill's reference is its proposal order's
    `price`, by proposal, symbol, side."""
    chosen = [row for row in rows if row.get("strategy") == name and real(row)]

    def reference(row: Row) -> float | None:
        stem = fill_proposal(row) or ""
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
    """Every live sleeve: one model simulation each, O(S (T N + R N L)), plus
    O(D S + F) per realized path; appends incidents only."""
    limits, preferences = load_limits(book), load_preferences(book)
    tracked = [s.name for s in strategies(book) if s.status is Status.LIVE]
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
        own = {name: sleeve_fills(fills, name, prices) for name in tracked}
        stale = trading_days_after(last, today)
        bounds = Bounds(
            drawdown_multiple=limits.thresholds.drawdown_review_multiple,
            tracking=limits.thresholds.tracking_error,
            commission=commission_ceiling(limits.commission_bps) / 1e4,
        )
        for name in tracked:
            path, why = modeled(book, name, setting_of)
            run = run_facts(book, name)
            notes = [note for note in (why,) if note]
            if run is None:
                notes.append("no research run line: drawdown and slippage unbounded")
            if not own[name]:
                notes.append("no real fills")
            case = Case(
                strategy=name,
                status=Status.LIVE,
                fills=own[name],
                sleeve=realized(own[name], panel, rf),
                model=path,
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
    start.add_argument("--cap", type=positive, help=f"asset cap; default {DEFAULT_CAP}")
    add_slot(start, UNIVERSE, "CSV with a symbol column and an optional sector column")
    start.add_argument(
        "--held-out",
        type=Path,
        help="held-out list path outside the book; default under XDG_STATE_HOME",
    )

    record = commands.add_parser("record", help="accept one batch through the gate")
    record.set_defaults(func=cmd_record)
    record.add_argument("book", help="book directory")
    add_slot(record, BATCH, ", ".join(BATCH_KEYS))
    add_slot(
        record,
        FILLS,
        "pasted broker fills, CSV header symbol,side,quantity,price,date "
        "(optional strategy) or a JSON list; needs --proposal",
    )
    record.add_argument("--proposal", help="proposal stem the fills trade")

    check = commands.add_parser(
        "check",
        help="continue view, a standing, a proposal, or --schema",
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("book", nargs="?", help="book directory; --schema needs none")
    check.add_argument(
        "target",
        nargs="?",
        help="strategy, run id, or proposal date",
    )
    check.add_argument(
        "--schema",
        nargs="?",
        const="all",
        type=schema_kind,
        metavar="|".join(SCHEMA_KINDS),
        help="print record shapes, one kind or all; needs no book",
    )
    check.add_argument(
        "--live", action="store_true", help="weekly tracking of live sleeves"
    )
    check.add_argument(
        "--brief", action="store_true", help="daily brief: at most twelve lines"
    )
    check.add_argument(
        "--today",
        type=iso_day,
        help="tests only: the day the view, --live, or --brief reads as today",
    )

    measure = commands.add_parser("measure", help="measure a registered strategy")
    measure.set_defaults(func=cmd_measure)
    measure.add_argument("book", help="book directory")
    measure.add_argument("strategy", help="directory under strategies/")
    measure.add_argument(
        "--held-out",
        action="store_true",
        help="one run on held-out names at a promotion gate; read its scorecard only",
    )
    measure.add_argument("--agent", help="append to ledger/runs/<agent>.jsonl")
    measure.add_argument(
        "--repeat", metavar="RUN_ID", help="rerun a recorded run; writes nothing"
    )
    measure.add_argument(
        "--reason",
        type=reason_text,
        help="run past trials_per_day or min_holding_days; stamped as override_reason",
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    given = list(sys.argv[1:] if argv is None else argv)
    if given and given[0] in LATER:
        return later(given[0])
    return run_cli(build_parser(), given)
