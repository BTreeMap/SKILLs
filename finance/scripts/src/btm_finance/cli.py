"""Argument surface and the process boundary that turns violations into exit 1."""

from __future__ import annotations

import argparse
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
    dump,
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
from btm_finance import approvals, delegates, git, governed, heartbeat, onboarding
from btm_finance.api import FACTORS, Market, ledger, on_dates
from btm_finance.batch import BATCH_KEYS, SCHEMA, Context, RecordResult, expand_batch
from btm_finance.brief import WEEK, Bet, Open, Owed, brief, justifying
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
from btm_finance.evolution import evolution
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
    ANSWERS_SHAPE,
    RECEIPT_SHAPE,
    SUMMARY_WORDS,
    Action,
    Answers,
    Cadence,
    Exclusions,
    Limits,
    Preferences,
    Status,
    StrategyConfig,
    baseline_hypothesis,
    book_relative,
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
    code_drift,
    compare,
    data_drift,
    peer_drift,
)
from btm_finance.repeat import advisories as engine_advisories
from btm_finance.scaffold import INDEX, onboard_files, scaffold, template
from btm_finance.scorecard import RunLine, Span
from btm_finance.standing import Evidence, StandingView, standing_of
from btm_finance.store import (
    MARKER,
    PAD_DIR,
    Book,
    append_ledger,
    governed_paths,
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
ANSWERS = Optional("answers", inline=False)
FILLS = Optional("fills", inline=False)
FILLS_SLOT = Required("fills", inline=False)  # names the flag in a rejection
ANSWERS_HELP = "JSON object of onboarding answers; check --schema answers prints it"
SCHEMA_KINDS = ("record", "run", "answers", "pad", "receipt", "approval")
RECEIPT = "receipt"
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
    root: Path,
    cap: int | None,
    universe: str | None,
    held_out: Path | None = None,
    answers: Answers | None = None,
) -> dict[str, Any]:
    """Make the book, register the baseline hypothesis, commit it all as
    `start: <id>`, then record the `onboard` decision naming the blob of
    every governed file the scaffold wrote, and commit its ledger line."""
    receipt = scaffold(root, cap, universe, held_out, answers)
    book = open_book(str(root))
    hypotheses = {"hypotheses": [baseline_hypothesis(datetime.now(UTC).date())]}
    result = recorded(book, hypotheses)
    receipt["commit"] = git.commit(book.root, ["."], f"start: {book.meta.id}")
    recorded(book, {"decisions": [onboarded(book, governed_paths(book.root))]})
    git.commit(book.root, [DECISIONS], f"start: {book.meta.id} onboard decision")
    receipt["wrote"] += ["ledger/hypotheses.jsonl", DECISIONS]
    receipt["new"] = result.new["hypotheses"]
    return receipt


DECISIONS = "ledger/decisions.jsonl"


def onboarded(book: Book, applied: list[str]) -> dict[str, Any]:
    """The decision `start` records for the governed files it wrote."""
    return {
        "kw": ["book", "start"],
        "subject": book.meta.id,
        "action": Action.ONBOARD.value,
        "reason": "start",
        "applied": applied,
    }


def cmd_start(args: argparse.Namespace) -> int:
    """A new book; on an existing one, with answers, its instruction files."""
    raw = text(ANSWERS, args)
    answers = None if raw is None else onboarding.answers_of(raw)
    root = Path(args.book).expanduser()
    universe = text(UNIVERSE, args)
    if answers is not None and (root / MARKER).is_file():
        if args.cap is not None or universe is not None or args.held_out is not None:
            raise CommandError(
                f"{root} is a book: start takes only --answers:file and --force there"
            )
        emit(onboard(open_book(str(root)), answers, force=args.force))
        return 0
    emit(start(root, args.cap, universe, args.held_out, answers))
    return 0


def onboard(book: Book, answers: Answers, *, force: bool) -> dict[str, Any]:
    """Instruction files for an existing book, and each answered limit that
    differs written into `limits.json`, committed as `onboard: <id>`, under
    an `onboard` decision naming that commit; `preferences.json` changes
    only through the returned batch."""
    git.repository_at(book.root)
    onboarding.refuse_existing(book.root, force=force)
    limits = load_limits(book)
    claude = onboard_files(
        book.root,
        book.meta,
        answers,
        answers.capital.now or limits.asset_cap,
        utc_today().isoformat(),
    )
    changes = onboarding.limit_changes(answers, limits)
    wrote = list(onboarding.FILES)
    if changes:
        path = book.root / governed.LIMITS
        write_atomic(
            path,
            json.dumps(onboarding.patched(read_json(path), changes), indent=2) + "\n",
        )
        wrote.append(governed.LIMITS)
    commit = git.commit(book.root, wrote, f"onboard: {book.meta.id}")
    if changes:
        recorded(book, {"decisions": [onboarded(book, [governed.LIMITS])]})
        git.commit(book.root, [DECISIONS], f"onboard: {book.meta.id} decision")
        wrote.append(DECISIONS)
    return {
        "book": book.meta.id,
        "wrote": wrote,
        "commit": commit,
        "claude_md": claude,
        "limits": changes,
        "preferences": onboarding.preference_batch(answers, load_preferences(book)),
        "next": "tell the operator each limits value written; confirm "
        "preferences with the operator, then record them as a batch",
    }


def utc_today() -> date:
    """Today, UTC: the one day an approval holds."""
    return datetime.now(UTC).date()


def ids_of(path: Path, key: str = "id") -> list[str]:
    return [
        row[key]
        for _, row in rows_of(read_bytes(path))
        if isinstance(row.get(key), str)
    ]


def run_ids(book: Book) -> list[str]:
    return [run_id for path in run_files(book) for run_id in ids_of(path, "run_id")]


def pointers(book: Book) -> tuple[dict[str, str], frozenset[str]]:
    """Each clean, committed governed file to its blob id at HEAD, and the
    governed files that differ from HEAD or are untracked. Three git calls."""
    dirty = frozenset(
        path
        for path in git.dirty(book.root, governed.PATHSPECS)
        if governed.governed(path)
    )
    blobs = git.tree_blobs(book.root, [governed.LIMITS, "strategies", "approvals"])
    present = governed_paths(book.root)
    return {p: blobs[p] for p in present if p in blobs and p not in dirty}, dirty


def needs_pointers(batch: Mapping[str, Any]) -> bool:
    """A decision in the batch names a governed file."""
    rows = batch.get("decisions")
    return isinstance(rows, list) and any(
        isinstance(row, dict) and row.get("applied") for row in rows
    )


def context_of(book: Book, *, resolve: bool = False) -> Context:
    """Live book state the gate resolves a batch against; with `resolve`,
    governed files' blob ids too, which needs git."""
    limits = load_limits(book)
    resolved, dirty = pointers(book) if resolve else ({}, frozenset[str]())
    kinds = (
        Kind.HYPOTHESIS,
        Kind.CRITIQUE,
        Kind.DECISION,
        Kind.SCORED,
        Kind.REGIME,
        Kind.FILL,
    )
    ids = {kind: ids_of(book.path_of(kind)) for kind in kinds}
    return Context(
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
        book=book.meta.id,
        governed=resolved,
        dirty=dirty,
    )


def committed(book: Book, result: RecordResult) -> dict[str, int]:
    """Staged rows appended per kind, `preferences.json` rewritten when given;
    accepted counts per kind."""
    accepted: dict[str, int] = {}
    for kind, rows in sorted(result.staged.items()):
        append_ledger(book.path_of(kind), rows)
        accepted[kind.value] = len(rows)
    if result.preferences is not None:
        write_atomic(
            book.root / "preferences.json",
            json.dumps(dump(result.preferences), indent=2) + "\n",
        )
    return accepted


def recorded(book: Book, batch: dict[str, Any]) -> RecordResult:
    """A batch the program builds itself, through the same gate; any problem
    is a defect, so it raises."""
    context = context_of(book, resolve=needs_pointers(batch))
    result = expand_batch(context, batch, make_id, now_iso())
    if result.problems:
        raise CommandError(f"record refused {batch}: {result.problems}")
    committed(book, result)
    return result


def cmd_record(args: argparse.Namespace) -> int:
    book = open_book(args.book)

    def expand(batch: dict[str, Any]) -> RecordResult:
        context = context_of(book, resolve=needs_pointers(batch))
        return expand_batch(context, batch, make_id, now_iso())

    def commit(result: RecordResult) -> dict[str, Any]:
        document: dict[str, Any] = {
            "book": book.meta.id,
            "accepted": committed(book, result),
        }
        if result.preferences is not None:
            document["preferences"] = "rewritten"
        document["new"] = result.new
        document["next"] = "run check for the continue view"
        return document

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
    """`--fills:file` or `--dry-run` against `--approval` as a `fills` batch
    and the problems refusing it; None when the batch slot carries the batch."""
    raw = text(FILLS, args)
    if args.approval is None:
        if raw is not None or args.dry_run:
            raise CommandError("--fills:file and --dry-run need --approval <file>")
        return None
    if args.batch_file is not None or getattr(args, "stdin", None) == "batch":
        raise CommandError("--approval builds the batch; drop --batch")
    if (raw is None) is not args.dry_run:
        raise CommandError("--approval takes one of --fills:file or --dry-run")
    today = utc_today().isoformat()
    path = approval_file(book, args.approval)
    approval = approval_checked(book, path, today)
    if raw is None:
        fills, problems = approvals.dry_run(approval, today)
    else:
        rows = approvals.table_rows(raw, "the fills")
        fills, problems = approvals.pasted(
            rows, approval.orders, statuses_of(book), today
        )
    return {"fills": [fill | {"approval": path.stem} for fill in fills]}, problems


def statuses_of(book: Book) -> dict[str, str]:
    """Each strategy directory's raw `status` word, empty when absent."""
    return {found.name: found.raw for found in strategies(book)}


def approval_file(book: Book, raw: str) -> Path:
    """`raw`, absolute or book-relative, resolving to a file under `approvals/`."""
    folder = (book.root / "approvals").resolve()
    given = Path(raw).expanduser()
    path = (given if given.is_absolute() else book.root / given).resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        raise CommandError(f"{raw} is no file under the book's approvals/")
    return path


def approval_checked(book: Book, path: Path, today: str) -> approvals.Checked:
    """The approval against its proposal, `limits.json`, each status, and the
    `approve` decisions naming its committed blob."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise CommandError(f"unreadable approvals/{path.name}: {err}") from err
    shown = book.relative(path)
    clean = not git.dirty(book.root, [shown])
    witness = (shown, git.blob(book.root, "HEAD", shown) if clean else "")
    approvals_seen = governed.witnesses(
        (row for _, row in kind_rows(book, Kind.DECISION)), Action.APPROVE
    )
    folder = (book.root / "proposals").resolve()

    def orders_of(stem: str) -> list[Any] | None:
        target = (folder / f"{stem}.json").resolve()
        if target.parent != folder or not target.is_file():
            return None
        try:
            found = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        orders = found.get("orders") if isinstance(found, dict) else None
        return orders if isinstance(orders, list) else None

    return approvals.checked(
        document,
        path.stem,
        today=today,
        cap=load_limits(book).max_adv_participation,
        statuses=statuses_of(book),
        proposal_orders=orders_of,
        witnessed=clean and witness in approvals_seen,
    )


def approval_view(book: Book, target: str, today: date) -> tuple[dict[str, Any], int]:
    """`check <book> approvals/<date>.json`: the order table and every problem."""
    path = approval_file(book, target)
    found = approval_checked(book, path, today.isoformat())
    for problem in found.problems:
        signal(f"approval: {problem}")
    shown = f"approvals/{path.name}"
    return {
        "book": book.meta.id,
        "approval": shown,
        "orders": list(found.orders),
        "problems": list(found.problems),
        "next": "fix each problem: rewrite the file from the operator's reply "
        "and record its approve decision again, then check it"
        if found.problems
        else "operator places each probe and live order by hand at the broker "
        "and pastes fills in chat; show the parsed table back, on yes run "
        f"record --fills:file <table> --approval {shown}; paper orders now: "
        f"record --approval {shown} --dry-run",
    }, 1 if found.problems else 0


def cmd_check(args: argparse.Namespace) -> int:
    if args.schema is not None:
        emit(schema_view(args.schema))
        return 0
    if args.book is None:
        raise CommandError("check needs a book path; only --schema runs without one")
    book = open_book(args.book)
    if args.target is not None and args.target.endswith(".json"):
        view, code = approval_view(book, args.target, args.today or utc_today())
        emit(view)
        return code
    return book_check(book, args)


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
        standing = standing_view(book, args.target, advisory=True)
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
    """`INDEX.md` absent: the lead keeps one line per lib module, tool,
    research topic, and delegate brief there."""
    if (book.root / INDEX).is_file():
        return []
    signal(
        f"no {INDEX} in the book; write it with one line per lib, tool, topic, brief"
    )
    return [{"file": INDEX, "problem": "absent"}]


def absent_writes(root: Path, pad: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One tagged warning per `wrote` path of a `receipt` pad line that is
    outside the book or absent from it. O(pad lines + paths)."""
    found: list[dict[str, Any]] = []
    for row in pad:
        wrote = row.get("wrote") if row.get("type") == RECEIPT else None
        for path in wrote if isinstance(wrote, list) else []:
            try:
                present = (root / book_relative(str(path))).exists()
            except ValueError:
                present = False
            if not present:
                found.append(
                    {
                        "problem": "receipt path absent",
                        "unit": row.get("unit"),
                        "ts": row.get("ts"),
                        "path": path,
                    }
                )
    return found


def continue_view(book: Book, today: date) -> dict[str, Any]:
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
    proposals = open_proposals(proposal_dates(book), decisions, today)
    every_decision = [row for _, row in kind_rows(book, Kind.DECISION)]
    log = git.log_commits(book.root, governed.PATHSPECS)
    resolved, dirty = pointers(book)
    pending = len(open_hypotheses(hypotheses, runs, decisions))
    preferences = load_preferences(book)
    pad = [row for _, row in rows_of(read_bytes(book.root / PAD_DIR / "scratch.jsonl"))]
    pulse = heartbeat.pulse(
        pad, preferences, datetime.now(UTC), datetime.now().astimezone().time()
    )
    stale_pulse = heartbeat.stale_warning(pulse, preferences.heartbeat_minutes)
    if stale_pulse:
        signal(
            f"newest heartbeat is {pulse['minutes_since']} minutes old; "
            "run the queue and schedule the next wake"
        )
    used_today = heartbeat.trials_today(runs, today)
    absent = absent_writes(book.root, pad)
    if absent:
        signal(
            f"{len(absent)} receipt path(s) absent under warnings; examine "
            "those receipts again"
        )
    briefless = delegates.absent_briefs(book.root, pad)
    if briefless:
        signal(
            f"{len(briefless)} delegate brief(s) absent under warnings; write "
            "delegates/<unit>.md before next dispatch"
        )
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
    budgets = families(
        limits, hypotheses, runs, decisions, [row for _, row in hypothesis_lines]
    )
    unwitnessed = [
        *governed.unnamed(log, every_decision),
        *governed.uncommitted(dirty),
    ]
    if unwitnessed:
        signal(
            f"{len(unwitnessed)} governed change(s) no decision names, under "
            "warnings: tell the operator; record their word as a decision with "
            "applied after committing"
        )
    return {
        "book": book.meta.id,
        "as_of": now_iso(),
        "regime": None if regime is None else regime.model_dump(mode="json"),
        "strategies": {**by_status(known), "unknown": unknown},
        "families": budgets,
        "proposals": proposals,
        "approvals": approval_rows(book, resolved, every_decision, live(Kind.FILL)),
        "incidents": live(Kind.INCIDENT)[-INCIDENT_TAIL:],
        "pad": {"entries": count_lines(book.root / PAD_DIR / "scratch.jsonl")},
        "heartbeat": pulse,
        "trials_today": {"used": used_today, "cap": limits.trials_per_day},
        "warnings": [
            *warnings,
            *stale_pulse,
            *absent,
            *briefless,
            *fired,
            *late,
            *unwitnessed,
            *index_warning(book),
            *onboarding.warnings(book.root, template("AGENTS.tmpl")),
        ],
        "evolution": evolution_of(book, pad, runs, today, limits.idle_days),
        "next": started(
            pulse, next_step(hypotheses, pending, proposals, late, budgets)
        ),
    }


def started(pulse: Mapping[str, Any], step: str) -> str:
    """`next` prefixed with starting the heartbeat while no line exists."""
    return step if pulse["last"] is not None else f"{heartbeat.START}; then {step}"


def evolution_of(
    book: Book, pad: Sequence[Row], runs: Sequence[Row], today: date, idle_days: int
) -> dict[str, Any]:
    """Bare `check` `evolution`: one directory walk and one `git log` over
    `lib/` and `tools/`."""
    root = book.root

    def code(folder: str) -> list[str]:
        return [
            path.relative_to(root).as_posix()
            for path in (root / folder).rglob("*.py")
            if path.name != "__init__.py" and "__pycache__" not in path.parts
        ]

    dates: dict[str, str] = {}
    for found in git.log_commits(root, ["lib", "tools"]):
        for path in found.files:
            dates.setdefault(path, found.date)
    return evolution(
        briefs=[path.stem for path in (root / delegates.DELEGATES).glob("*.md")],
        pad=pad,
        runs=runs,
        lib=code("lib"),
        tools=code("tools"),
        commits=dates,
        today=today,
        idle_days=idle_days,
    )


def approval_rows(
    book: Book,
    resolved: Mapping[str, str],
    decisions: Sequence[Row],
    fills: Sequence[Row],
) -> list[dict[str, Any]]:
    """Each approval file: `proposal` and `date` it names, `approved` while
    clean and an `approve` decision names its blob, `filled` once a
    fill carries its stem. O(A + D + F)."""
    approves = governed.witnesses(decisions, Action.APPROVE)
    filled = {str(row.get("approval", "")).removesuffix(".json") for row in fills}
    rows: list[dict[str, Any]] = []
    for path in governed_paths(book.root):
        if not path.startswith("approvals/"):
            continue
        try:
            document = json.loads((book.root / path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            document = None
        named = document if isinstance(document, dict) else {}
        rows.append(
            {
                "file": path,
                "proposal": named.get("proposal"),
                "date": named.get("date"),
                "approved": (path, resolved.get(path)) in approves,
                "filled": Path(path).stem in filled,
            }
        )
    return rows


def unfilled_approval(rows: Sequence[Mapping[str, Any]], today: date) -> str | None:
    """The newest send date of an approved, unfilled approval of the last 7
    days."""
    found: list[str] = []
    for row in rows:
        try:
            age = (today - date.fromisoformat(str(row["date"]))).days
        except ValueError:
            continue
        if row["approved"] and not row["filled"] and 0 <= age < WEEK:
            found.append(str(row["date"]))
    return max(found, default=None)


def owed_of(book: Book, view: Mapping[str, Any], today: date) -> Owed:
    """What the operator owes, in `Reply` order: fills, an answer to the
    oldest open proposal, a yes to a change asked today (`question` pad entry
    of today), a word on the first overdue or unscored bet."""
    pad = rows_of(read_bytes(book.root / PAD_DIR / "scratch.jsonl"))
    asked = any(
        row.get("type") == "question"
        and str(row.get("ts", ""))[:10] == today.isoformat()
        for _, row in pad
    )
    late = [w for w in view["warnings"] if w.get("problem") in {"overdue", "unscored"}]
    first = late[0] if late else None
    return Owed(
        unfilled=unfilled_approval(view["approvals"], today),
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


SCHEMA_VIEW: dict[str, dict[str, Any]] = {
    "record": {
        "record_batch": {key: SCHEMA[key] for key in BATCH_KEYS},
        "sequence": "hypotheses, critiques, decisions, scored, regimes, "
        "fills, holdings, preferences; a decision or scored line may name a "
        "hypothesis made earlier in the batch",
        "ledger_line": f"{', '.join(ENVELOPE)} (stamped by record), then the record",
        "corrections": '"supersedes": "<id>" on a new line; newest wins',
        "refs": REFS_SCHEMA + "; receipts echo every new id under new",
        "fill_table": "CSV with header symbol,side,quantity,price,date "
        "(optional strategy), or a JSON list of objects with those keys; "
        "record --fills:file <table> --approval <file> turns it into fills, "
        "strategy taken from the approval's one order of that symbol and side "
        "when absent; record --approval <file> --dry-run fills its paper "
        "orders at price",
    },
    "run": {
        "run_line": f"{', '.join(RunLine.model_fields)} (written by measure only)",
        "strategy_config": '{"params": {"<name>": 1.0}, "rebalance": '
        '"monthly|quarterly|annual", "holding_days": 21, "long_only": true, '
        '"family_id": "<key of limits.families>"}',
    },
    "answers": {
        "answers": ANSWERS_SHAPE,
        "answers_rules": "start --answers:file, new book or existing; every "
        "key optional, a missing one takes its default (risk 0.35 and 0.25, "
        "cadence monthly, brief_hour 7, schedule weekdays, sources csv edgar "
        "french, collaborators none); brief_hour 0 to 23; schedule "
        "daily|weekdays; "
        "accounts kind taxable|sheltered; sleeve_account names one account; "
        "cadence monthly|quarterly; sources csv|edgar|french|tiingo; "
        "collaborators kind agent|person; unknown keys refused, so no key or "
        "secret fits: keys live in the environment only",
    },
    "pad": {
        "path": f"{PAD_DIR.as_posix()}/scratch.jsonl; agent appends and greps "
        "it with its own file tools; never gated, never read by record",
        "line": '{"ts": "<ISO 8601>", "type": "<type>", ...any fields}',
        "types": {
            **{name: meaning for name, meaning in PAD_TYPES.items() if name != "known"},
            heartbeat.HEARTBEAT: "one wake of the always-on loop: item (tier "
            "and unit in words), outcome (one line), next_wake (ISO)",
            RECEIPT: "a delegate receipt the lead accepted, verbatim, plus ts "
            "and type; bare check warns on each wrote path absent",
        },
    },
    "receipt": {
        "receipt": RECEIPT_SHAPE,
        "rules": "a delegate's final message is this one JSON object and "
        "nothing else; every key required, no other key; wrote paths "
        f"book-relative; summary at most {SUMMARY_WORDS} words; next and "
        "friction one line each, empty allowed; commit the 40-hex head of "
        "the delegate's branch after its last commit, null when it wrote "
        "nothing; check it with btm_finance.api.receipt(text)",
    },
    "approval": {
        "approval": '{"date": "YYYY-MM-DD", "proposal": "<proposal stem>", '
        '"reply": "<operator\'s reply, verbatim>", '
        '"orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, '
        '"price": 12.5, "adv_participation": 0.004, "strategy": "<name>", '
        '"limit": null}]}',
        "rules": "check <book> approvals/<date>.json: date is today (UTC); "
        "reply is non-empty; the file is committed, clean, and an approve "
        "decision names its committed blob; proposal names a file under "
        "proposals/; every order is one of that proposal by symbol, side, "
        "strategy; adv_participation at most "
        "limits.max_adv_participation; strategy status paper, probe, or live",
    },
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


def code_paths(book: Book, name: str) -> tuple[str, ...]:
    """`signal.py`, `config.json`, and each book-local module `signal.py`
    reaches, book-relative, sorted."""
    folder = f"strategies/{name}"
    reach = strategy_reach(book.root, name)
    return tuple(
        sorted({f"{folder}/signal.py", f"{folder}/config.json", *reach.modules})
    )


def committed_code(book: Book, name: str) -> dict[str, str]:
    """`code_objects`: each code path to its blob id at HEAD; refuses when the
    strategy folder or a module it reaches differs from HEAD or is
    untracked."""
    paths = code_paths(book, name)
    dirty = git.dirty(book.root, [f"strategies/{name}/", *paths])
    if dirty:
        raise CommandError(
            f"commit before measure: {', '.join(sorted(dirty))} differs from HEAD "
            "or is untracked"
        )
    return {path: git.blob(book.root, "HEAD", path) for path in paths}


def moved_code(book: Book, name: str, objects: Mapping[str, str]) -> list[str]:
    """Each code path whose AST (or parsed `config.json`) differs between its
    recorded blob and the working tree, then each path reached today but not
    then. Blob ids survive rebase."""
    then = {path: git.show_blob(book.root, blob) for path, blob in objects.items()}
    now = {
        path: (book.root / path).read_bytes() if (book.root / path).is_file() else None
        for path in objects
    }
    return code_drift(then, now, code_paths(book, name))


def engine_now() -> dict[str, str]:
    """What `engine` on a run line holds: the skill commit, then libraries."""
    return {
        "btm_finance": git.skill_commit(),
        "numpy": np.__version__,
        "pyarrow": pa.__version__,
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
    objects = committed_code(book, name)
    spent = heartbeat.trials_today(all_runs(book), utc_today())
    if not args.held_out and spent >= limits.trials_per_day:
        raise CommandError(
            f"refused before running: {spent} run line(s) dated today reach "
            f"limits.trials_per_day {limits.trials_per_day}; sharpen the "
            "backlog and measure tomorrow"
        )
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
        code_paths=tuple(objects),
        code_objects=objects,
        config=config.model_dump(mode="json"),
        params={key: float(value) for key, value in params.items()},
        scorecard=outcome.scorecard,
        reasons=outcome.reasons,
        engine=engine_now(),
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
    changed = code_changed(book, name, run)
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


def code_changed(book: Book, name: str, run: Row) -> bool:
    """The strategy's code moved since the run, by `moved_code`; a line
    without `code_objects` reads moved."""
    objects = run.get("code_objects")
    if not isinstance(objects, dict) or not objects:
        return True
    return bool(moved_code(book, name, {str(p): str(b) for p, b in objects.items()}))


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
        "sleeve, then wait for a reply. On approve: write approval_template to "
        "approvals/<send day>.json with date the send day and reply the "
        f"operator's words, record an approve decision on {path.stem} quoting "
        "them with applied naming the file, then check it. On reject or "
        f"override: record that decision on {path.stem} quoting the reply",
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
    manifest: Manifest,
) -> list[str]:
    """Every reason the rerun would not be the recorded run. Reads each code
    path's recorded blob; re-hashes every listed source file and peer series
    once: O(store bytes)."""
    problems: list[str] = []
    moved = moved_code(book, line.strategy, line.code_objects)
    if moved:
        problems.append(f"code moved: {', '.join(moved)}")
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
        advisories=tuple(engine_advisories(line.engine, engine_now())),
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
    """Approval file stem to the proposal stem it names, from `approvals/`; a
    file naming none maps to its own stem."""
    found: dict[str, str] = {}
    for path in sorted((book.root / "approvals").glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stem = document.get("proposal") if isinstance(document, dict) else None
        found[path.stem] = stem if isinstance(stem, str) else path.stem
    return found


def sleeve_fills(
    rows: Sequence[Row],
    name: str,
    status: Status,
    prices: Mapping[tuple[str, str, str], float],
    proposals: Mapping[str, str],
) -> tuple[Fill, ...]:
    """Paper sleeves count dry-run fills, probe and live ones real fills; a fill's
    reference is its proposal order's `price`, by approval, symbol, side. A
    fill names its approval by stem, or by file name as older fills do."""
    paper = status is Status.PAPER
    chosen = [
        row
        for row in rows
        if row.get("strategy") == name and bool(row.get("dry_run")) is paper
    ]

    def reference(row: Row) -> float | None:
        approval = str(row.get("approval", "")).removesuffix(".json")
        stem = proposals.get(approval, approval)
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
        "--cap",
        type=positive,
        help="asset cap; default answers capital.now, else 10000000",
    )
    add_slot(start, UNIVERSE, "CSV with a symbol column and an optional sector column")
    start.add_argument(
        "--held-out",
        type=Path,
        help="held-out list path outside the book; default answers held_out, "
        "else under XDG_STATE_HOME",
    )
    add_slot(start, ANSWERS, ANSWERS_HELP)
    start.add_argument(
        "--force",
        action="store_true",
        help="existing book: rewrite README.md, AGENTS.md, CLAUDE.md when present",
    )

    record = commands.add_parser("record", help="accept one batch through the gate")
    record.set_defaults(func=cmd_record)
    record.add_argument("book", help="book directory")
    add_slot(record, BATCH, ", ".join(BATCH_KEYS))
    add_slot(
        record,
        FILLS,
        "pasted broker fills, CSV header symbol,side,quantity,price,date "
        "(optional strategy) or a JSON list; needs --approval",
    )
    record.add_argument(
        "--approval", help="approvals/<date>.json the fills or dry run belong to"
    )
    record.add_argument(
        "--dry-run",
        action="store_true",
        help="record the approval's paper orders as dry-run fills at price",
    )

    check = commands.add_parser(
        "check",
        help="continue view, a standing, a proposal, an approval, or --schema",
    )
    check.set_defaults(func=cmd_check)
    check.add_argument("book", nargs="?", help="book directory; --schema needs none")
    check.add_argument(
        "target",
        nargs="?",
        help="strategy, run id, proposal date, or approvals/<date>.json",
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
        "--live", action="store_true", help="weekly tracking of paper and live sleeves"
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
