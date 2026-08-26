#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Ledger engine for open-question research sessions.

The script owns the exact half of a research run: the append-only event
ledger, its transition invariants, total replay, derived sections, source
numbering, per-round yield, and the draft-time outline. The invoking agent
owns every judgment call: decomposition, search, source classing, closure,
and prose. Subcommands print one JSON document to stdout; advisory
`signal:` lines go to stderr and never block; invariant violations print
`error:` to stderr and exit 1 without appending the offending event.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_CLASSES = ("constitutive", "attested", "measured", "reported")
ORIGINS = ("frame", "spawned")
CLOSE_STATES = ("retrieved", "refuted", "unresolved", "retired")
UNRESOLVED_REASONS = ("searched", "not_pursued")
RETIRED_REASONS = ("folded", "immaterial")
CHAIN_MIN_LINKS = 2  # a Chain section renders past this many retrieved leaves
MAX_EVENTS = 1000  # runaway backstop; a real run stays under ~100 events


class CommandError(Exception):
    """Failure that ends the command with a clean message and exit code 1."""


# --- pure core: leaf states as a closed sum ---


@dataclass(frozen=True, slots=True)
class Open:
    pass


@dataclass(frozen=True, slots=True)
class Retrieved:
    sources: tuple[str, ...]  # non-empty by construction


@dataclass(frozen=True, slots=True)
class Refuted:
    sources: tuple[str, ...]  # non-empty by construction
    premise: str  # what the leaf assumed that evidence contradicts


@dataclass(frozen=True, slots=True)
class Unresolved:
    reason: str  # one of UNRESOLVED_REASONS
    detail: str


@dataclass(frozen=True, slots=True)
class Retired:
    reason: str  # one of RETIRED_REASONS
    detail: str  # folded: the target leaf id; immaterial: why


LeafState = Open | Retrieved | Refuted | Unresolved | Retired


@dataclass(frozen=True, slots=True)
class Leaf:
    question: str
    origin: str
    state: LeafState


@dataclass(frozen=True, slots=True)
class Source:
    leaf: str
    cls: str
    title: str
    url: str


@dataclass(slots=True)
class Ledger:
    """Left fold of the event log; mutated only inside apply()."""

    leaves: dict[str, Leaf] = field(default_factory=dict)
    sources: dict[str, Source] = field(default_factory=dict)
    source_order: list[str] = field(default_factory=list)
    swept: bool = False
    events: int = 0


def _require(condition: bool, invariant: str) -> None:
    if not condition:
        raise CommandError(invariant)


def _close_state(raw: dict[str, Any], ledger: Ledger) -> LeafState:
    """Parse a close payload into a LeafState, or raise the violated invariant."""
    state = raw.get("state")
    _require(state in CLOSE_STATES, f"close state must be one of {CLOSE_STATES}")
    if state in ("retrieved", "refuted"):
        sources = tuple(raw.get("sources") or ())
        _require(bool(sources), f"{state} requires at least one source id")
        for sid in sources:
            _require(sid in ledger.sources, f"unknown source id: {sid}")
        if state == "retrieved":
            return Retrieved(sources)
        premise = str(raw.get("premise") or "").strip()
        _require(bool(premise), "refuted requires the contradicted premise")
        return Refuted(sources, premise)
    reason = raw.get("reason")
    detail = str(raw.get("detail") or "").strip()
    if state == "unresolved":
        _require(
            reason in UNRESOLVED_REASONS,
            f"unresolved reason must be one of {UNRESOLVED_REASONS}",
        )
        _require(bool(detail), "unresolved requires detail")
        return Unresolved(reason, detail)
    _require(
        reason in RETIRED_REASONS, f"retired reason must be one of {RETIRED_REASONS}"
    )
    if reason == "folded":
        target = ledger.leaves.get(detail)
        _require(target is not None, f"fold target does not exist: {detail}")
        _require(
            isinstance(target.state, Retrieved),
            f"fold target must be retrieved: {detail}",
        )
        return Retired(reason, detail)
    _require(
        bool(detail), "immaterial detail must name the conclusion it fails to change"
    )
    return Retired(reason, detail)


def _apply_close(ledger: Ledger, raw: dict[str, Any]) -> None:
    leaf_id = raw.get("leaf")
    leaf = ledger.leaves.get(leaf_id)
    _require(leaf is not None, f"unknown leaf id: {leaf_id}")
    new_state = _close_state(raw, ledger)
    legal = isinstance(leaf.state, Open) or (
        isinstance(leaf.state, Retrieved) and isinstance(new_state, Refuted)
    )
    _require(
        legal,
        f"illegal transition on {leaf_id}: {type(leaf.state).__name__} -> "
        f"{type(new_state).__name__} (only Open -> any, Retrieved -> Refuted)",
    )
    ledger.leaves[leaf_id] = Leaf(leaf.question, leaf.origin, new_state)


def apply(ledger: Ledger, raw: dict[str, Any]) -> Ledger:
    """Admit one raw event into the ledger, or raise the violated invariant.

    This is the smart constructor: an event this function rejects is never
    appended, so the log on disk holds only admitted events.
    """
    _require(ledger.events < MAX_EVENTS, f"event cap reached ({MAX_EVENTS})")
    kind = raw.get("e")
    match kind:
        case "add_leaf":
            leaf_id = str(raw.get("id") or "").strip()
            _require(bool(leaf_id), "add_leaf requires an id")
            _require(leaf_id not in ledger.leaves, f"duplicate leaf id: {leaf_id}")
            question = str(raw.get("q") or "").strip()
            _require(bool(question), "add_leaf requires a question")
            origin = raw.get("origin", "frame")
            _require(origin in ORIGINS, f"origin must be one of {ORIGINS}")
            ledger.leaves[leaf_id] = Leaf(question, origin, Open())
        case "add_source":
            source_id = str(raw.get("id") or "").strip()
            _require(bool(source_id), "add_source requires an id")
            _require(
                source_id not in ledger.sources, f"duplicate source id: {source_id}"
            )
            leaf_id = raw.get("leaf")
            _require(leaf_id in ledger.leaves, f"unknown leaf id: {leaf_id}")
            cls = raw.get("cls")
            _require(cls in SOURCE_CLASSES, f"cls must be one of {SOURCE_CLASSES}")
            title = str(raw.get("title") or "").strip()
            _require(bool(title), "add_source requires a title")
            ledger.sources[source_id] = Source(
                leaf_id, cls, title, str(raw.get("url") or "")
            )
            ledger.source_order.append(source_id)
        case "close":
            _apply_close(ledger, raw)
        case "sweep":
            checked = str(raw.get("checked") or "").strip()
            _require(bool(checked), "sweep requires what was checked")
            candidates = list(raw.get("candidates") or [])
            survivors = list(raw.get("survivors") or [])
            _require(
                set(survivors) <= set(candidates),
                "sweep survivors must be a subset of candidates",
            )
            ledger.swept = True
        case "checkpoint":
            searches = raw.get("searches")
            _require(
                isinstance(searches, int) and searches >= 0,
                "checkpoint requires a non-negative integer search count",
            )
        case _:
            raise CommandError(f"unknown event kind: {kind}")
    ledger.events += 1
    return ledger


def replay(events: list[dict[str, Any]]) -> Ledger:
    """Total over any log the script wrote; a rejection here means tampering."""
    ledger = Ledger()
    for index, raw in enumerate(events, start=1):
        try:
            apply(ledger, raw)
        except CommandError as exc:
            raise CommandError(f"ledger line {index} does not replay: {exc}") from exc
    return ledger


# --- pure core: derived views ---


def stated(classes: list[str]) -> str:
    """How the renderer may voice a claim: advisory, never a close gate."""
    if any(cls in ("constitutive", "attested") for cls in classes):
        return "plain"
    measured = sum(1 for cls in classes if cls == "measured")
    return "plain" if measured >= 2 else "hedged"  # noqa: PLR2004


def sections(ledger: Ledger) -> list[str]:
    """The five derivable sections; Boundary stays an agent judgment."""
    derived = ["answer"]
    states = [leaf.state for leaf in ledger.leaves.values()]
    if sum(isinstance(s, Retrieved) for s in states) > CHAIN_MIN_LINKS:
        derived.append("chain")
    if any(isinstance(s, Refuted) for s in states) or ledger.swept:
        derived.append("rival")
    if any(isinstance(s, Unresolved) for s in states):
        derived.append("open")
    derived.append("sources")
    return derived


def violations(ledger: Ledger) -> list[str]:
    found = [
        f"open leaf blocks draft: {leaf_id} ({leaf.question})"
        for leaf_id, leaf in ledger.leaves.items()
        if isinstance(leaf.state, Open)
    ]
    if not ledger.swept:
        found.append("no sweep recorded: run the rival sweep before drafting")
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.state, Retired) and leaf.state.reason == "folded":
            target = ledger.leaves.get(leaf.state.detail)
            if target is None or not isinstance(target.state, Retrieved):
                found.append(
                    f"fold broken: {leaf_id} folded into {leaf.state.detail}, "
                    "which is no longer retrieved; reopen or re-close the fold"
                )
    return found


def hedges(ledger: Ledger) -> list[str]:
    """Advisory: leaves whose evidence class earns hedged wording."""
    lines = []
    for leaf_id, leaf in ledger.leaves.items():
        if isinstance(leaf.state, (Retrieved, Refuted)):
            classes = [ledger.sources[sid].cls for sid in leaf.state.sources]
            if stated(classes) == "hedged":
                lines.append(
                    f"{leaf_id} rests on {'/'.join(sorted(set(classes)))} "
                    "sources: hedge the wording and name the class"
                )
    return lines


def yield_table(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """New sources per declared search, segmented by checkpoint events."""
    rows = []
    new_sources = 0
    for raw in events:
        if raw.get("e") == "add_source":
            new_sources += 1
        elif raw.get("e") == "checkpoint":
            searches = raw.get("searches", 0)
            rows.append(
                {
                    "label": raw.get("label") or f"round-{len(rows) + 1}",
                    "searches": searches,
                    "new_sources": new_sources,
                    "yield": round(new_sources / searches, 2) if searches else None,
                }
            )
            new_sources = 0
    return rows


def leaf_view(state: LeafState) -> dict[str, Any]:
    match state:
        case Open():
            return {"state": "open"}
        case Retrieved(sources):
            return {"state": "retrieved", "sources": list(sources)}
        case Refuted(sources, premise):
            return {"state": "refuted", "sources": list(sources), "premise": premise}
        case Unresolved(reason, detail):
            return {"state": "unresolved", "reason": reason, "detail": detail}
        case Retired(reason, detail):
            return {"state": "retired", "reason": reason, "detail": detail}


# --- imperative shell ---


def state_root() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / "btm-skills" / "btm-research"
    base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    return Path(base) / "btm-skills" / "btm-research"


def session_dir(name: str) -> Path:
    if os.sep in name or name.startswith("."):
        return Path(name)
    return state_root() / "sessions" / name


def ledger_path(directory: Path) -> Path:
    return directory / "ledger.jsonl"


def read_events(directory: Path) -> list[dict[str, Any]]:
    path = ledger_path(directory)
    if not path.exists():
        raise CommandError(f"no session at {directory}; run init first")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_events(directory: Path, admitted: list[dict[str, Any]]) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = "".join(
        json.dumps({"t": stamp, **raw}, ensure_ascii=False) + "\n" for raw in admitted
    )
    with ledger_path(directory).open("a", encoding="utf-8") as handle:
        handle.write(payload)


def admit(directory: Path, batch: list[dict[str, Any]]) -> Ledger:
    """Validate the whole batch against the replayed ledger, then append it."""
    events = read_events(directory)
    ledger = replay(events)
    for raw in batch:
        apply(ledger, raw)
    append_events(directory, batch)
    return ledger


def emit(document: dict[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)


def load_batch(path: str, kind: str) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(raw, list), f"--file must hold a JSON array of {kind} payloads")
    return [{"e": kind, **entry} for entry in raw]


def cmd_init(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    _require(
        not ledger_path(directory).exists(), f"session already exists at {directory}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    meta = {
        "question": args.question,
        "focus": args.focus,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with tempfile.NamedTemporaryFile(
        "w", dir=directory, delete=False, encoding="utf-8"
    ) as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)
    Path(handle.name).replace(directory / "session.json")
    ledger_path(directory).touch()
    emit({"session": str(directory), **meta})
    return 0


def read_meta(directory: Path) -> dict[str, Any]:
    path = directory / "session.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def cmd_leaf(args: argparse.Namespace) -> int:
    if args.file:
        batch = load_batch(args.file, "add_leaf")
    else:
        _require(bool(args.id and args.question), "leaf requires --id and --question")
        batch = [
            {"e": "add_leaf", "id": args.id, "q": args.question, "origin": args.origin}
        ]
    ledger = admit(session_dir(args.session), batch)
    emit({"added": len(batch), "leaves": len(ledger.leaves)})
    return 0


def cmd_source(args: argparse.Namespace) -> int:
    if args.file:
        batch = load_batch(args.file, "add_source")
    else:
        _require(
            bool(args.id and args.leaf and args.cls and args.title),
            "source requires --id, --leaf, --cls, and --title",
        )
        batch = [
            {
                "e": "add_source",
                "id": args.id,
                "leaf": args.leaf,
                "cls": args.cls,
                "title": args.title,
                "url": args.url or "",
            }
        ]
    ledger = admit(session_dir(args.session), batch)
    emit({"added": len(batch), "sources": len(ledger.sources)})
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    if args.file:
        batch = load_batch(args.file, "close")
    else:
        _require(bool(args.leaf and args.state), "close requires --leaf and --state")
        raw: dict[str, Any] = {"e": "close", "leaf": args.leaf, "state": args.state}
        if args.sources:
            raw["sources"] = [s for s in args.sources.split(",") if s]
        if args.premise:
            raw["premise"] = args.premise
        if args.reason:
            raw["reason"] = args.reason
        if args.into:
            raw["detail"] = args.into
        elif args.detail:
            raw["detail"] = args.detail
        batch = [raw]
    ledger = admit(session_dir(args.session), batch)
    open_left = sum(isinstance(lf.state, Open) for lf in ledger.leaves.values())
    emit({"closed": len(batch), "open_left": open_left})
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    candidates = [c for c in (args.candidates or "").split(",") if c]
    survivors = [s for s in (args.survivors or "").split(",") if s]
    batch = [
        {
            "e": "sweep",
            "checked": args.checked,
            "candidates": candidates,
            "survivors": survivors,
        }
    ]
    admit(session_dir(args.session), batch)
    if survivors:
        signal(f"surviving rivals: {', '.join(survivors)}; the Rival section renders")
    emit({"swept": True, "candidates": candidates, "survivors": survivors})
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    if args.checkpoint:
        _require(args.searches is not None, "--checkpoint requires --searches <count>")
        admit(
            directory,
            [{"e": "checkpoint", "label": args.label, "searches": args.searches}],
        )
    events = read_events(directory)
    ledger = replay(events)
    counts: dict[str, int] = {}
    for leaf in ledger.leaves.values():
        key = leaf_view(leaf.state)["state"]
        counts[key] = counts.get(key, 0) + 1
    rows = yield_table(events)
    last, prior = (rows[-1], rows[-2]) if len(rows) > 1 else (None, None)
    if (
        last is not None
        and last["yield"] is not None
        and prior["yield"]
        and last["yield"] < prior["yield"]
    ):
        signal(
            "yield fell against the previous round: weigh leaving this patch "
            "(re-decompose, or stop)"
        )
    emit(
        {
            "question": read_meta(directory).get("question"),
            "counts": counts,
            "open": [
                leaf_id
                for leaf_id, leaf in ledger.leaves.items()
                if isinstance(leaf.state, Open)
            ],
            "rounds": len(rows),
            "yield": rows,
        }
    )
    return 0


def cmd_outline(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    events = read_events(directory)
    ledger = replay(events)
    markers = {
        source_id: f"S{index}"
        for index, source_id in enumerate(ledger.source_order, start=1)
    }
    found = violations(ledger)
    for line in found:
        signal(line)
    signal(
        "boundary section is yours to judge: render it when the answer flips "
        "somewhere inside the question's scope"
    )
    emit(
        {
            "question": read_meta(directory).get("question"),
            "sections": sections(ledger),
            "violations": found,
            "hedges": hedges(ledger),
            "sources": [
                {
                    "marker": markers[source_id],
                    "id": source_id,
                    "cls": ledger.sources[source_id].cls,
                    "title": ledger.sources[source_id].title,
                    "url": ledger.sources[source_id].url,
                    "leaf": ledger.sources[source_id].leaf,
                }
                for source_id in ledger.source_order
            ],
            "leaves": {
                leaf_id: {"question": leaf.question, **leaf_view(leaf.state)}
                for leaf_id, leaf in ledger.leaves.items()
            },
        }
    )
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    root = state_root() / "sessions"
    if not args.session and not args.all:
        listing = (
            [
                {
                    "session": entry.name,
                    "bytes": sum(
                        f.stat().st_size for f in entry.rglob("*") if f.is_file()
                    ),
                }
                for entry in sorted(root.iterdir())
                if entry.is_dir()
            ]
            if root.exists()
            else []
        )
        emit({"sessions": listing})
        return 0
    targets = (
        (
            [d for d in root.iterdir() if d.is_dir()]
            if args.all
            else [session_dir(args.session)]
        )
        if root.exists() or args.session
        else []
    )
    freed = 0
    removed = []
    for target in targets:
        if target.exists():
            freed += sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            shutil.rmtree(target)
            removed.append(str(target))
    emit({"removed": removed, "bytes_freed": freed})
    return 0


def cmd_selftest(_args: argparse.Namespace) -> int:
    """Law checks: admitted events replay totally; every rejection path rejects."""
    checks = 0

    def rejects(raws: list[dict[str, Any]], why: str) -> None:
        nonlocal checks
        try:
            replay(raws)
        except CommandError:
            checks += 1
            return
        raise AssertionError(f"expected rejection: {why}")

    base = [
        {"e": "add_leaf", "id": "L1", "q": "q1", "origin": "frame"},
        {"e": "add_leaf", "id": "L2", "q": "q2", "origin": "spawned"},
        {"e": "add_leaf", "id": "L3", "q": "q3", "origin": "frame"},
        {
            "e": "add_source",
            "id": "S1",
            "leaf": "L1",
            "cls": "constitutive",
            "title": "spec",
        },
        {
            "e": "add_source",
            "id": "S2",
            "leaf": "L2",
            "cls": "reported",
            "title": "blog",
        },
        {"e": "close", "leaf": "L1", "state": "retrieved", "sources": ["S1"]},
        {
            "e": "close",
            "leaf": "L2",
            "state": "refuted",
            "sources": ["S2"],
            "premise": "assumed exact-length",
        },
        {"e": "checkpoint", "label": "round-1", "searches": 4},
        {
            "e": "sweep",
            "checked": "rival accounts of q1",
            "candidates": ["folk"],
            "survivors": [],
        },
        {
            "e": "close",
            "leaf": "L3",
            "state": "retired",
            "reason": "folded",
            "into": "L1",
            "detail": "L1",
        },
    ]
    ledger = replay(base)
    assert sections(ledger) == ["answer", "rival", "sources"], sections(ledger)
    assert violations(ledger) == [], violations(ledger)
    assert yield_table(base) == [
        {"label": "round-1", "searches": 4, "new_sources": 2, "yield": 0.5}
    ]
    assert stated(["reported"]) == "hedged" and stated(["attested"]) == "plain"
    assert stated(["measured"]) == "hedged"
    assert stated(["measured", "measured"]) == "plain"
    checks += 5

    contrary = {
        "e": "close",
        "leaf": "L1",
        "state": "refuted",
        "sources": ["S1"],
        "premise": "late contrary evidence",
    }
    broken = replay([*base, contrary])  # Retrieved -> Refuted is the one legal bend
    assert any("fold broken" in line for line in violations(broken))
    checks += 1

    rejects([{"e": "add_leaf", "id": "L1", "q": "a"}] * 2, "duplicate leaf")
    rejects(
        [
            {
                "e": "add_source",
                "id": "S1",
                "leaf": "L9",
                "cls": "measured",
                "title": "t",
            }
        ],
        "unknown leaf",
    )
    rejects(
        [*base, {"e": "close", "leaf": "L2", "state": "retrieved", "sources": ["S2"]}],
        "Refuted is terminal",
    )
    rejects(
        [
            *base,
            {
                "e": "close",
                "leaf": "L1",
                "state": "retired",
                "reason": "immaterial",
                "detail": "",
            },
        ],
        "empty immaterial why",
    )
    rejects(
        [
            {"e": "add_leaf", "id": "L1", "q": "a"},
            {
                "e": "close",
                "leaf": "L1",
                "state": "retired",
                "reason": "folded",
                "detail": "L1",
            },
        ],
        "fold target not retrieved",
    )
    rejects(
        [{"e": "sweep", "checked": "x", "candidates": [], "survivors": ["a"]}],
        "survivors outside candidates",
    )
    emit({"selftest": "ok", "checks": checks})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    def sub(name: str, func: Any) -> argparse.ArgumentParser:
        command = commands.add_parser(name)
        command.set_defaults(func=func)
        if name not in ("clean", "selftest"):
            command.add_argument("session")
        return command

    init = sub("init", cmd_init)
    init.add_argument("--question", required=True)
    init.add_argument("--focus", default=None)
    leaf = sub("leaf", cmd_leaf)
    leaf.add_argument("--id")
    leaf.add_argument("--question")
    leaf.add_argument("--origin", choices=ORIGINS, default="frame")
    leaf.add_argument("--file")
    source = sub("source", cmd_source)
    source.add_argument("--id")
    source.add_argument("--leaf")
    source.add_argument("--cls", choices=SOURCE_CLASSES)
    source.add_argument("--title")
    source.add_argument("--url")
    source.add_argument("--file")
    close = sub("close", cmd_close)
    close.add_argument("--leaf")
    close.add_argument("--state", choices=CLOSE_STATES)
    close.add_argument("--sources")
    close.add_argument("--premise")
    close.add_argument("--reason", choices=UNRESOLVED_REASONS + RETIRED_REASONS)
    close.add_argument("--into")
    close.add_argument("--detail")
    close.add_argument("--file")
    sweep = sub("sweep", cmd_sweep)
    sweep.add_argument("--checked", required=True)
    sweep.add_argument("--candidates")
    sweep.add_argument("--survivors")
    status = sub("status", cmd_status)
    status.add_argument("--checkpoint", action="store_true")
    status.add_argument("--searches", type=int)
    status.add_argument("--label")
    sub("outline", cmd_outline)
    clean = sub("clean", cmd_clean)
    clean.add_argument("session", nargs="?")
    clean.add_argument("--all", action="store_true")
    sub("selftest", cmd_selftest)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
