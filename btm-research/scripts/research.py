#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["btm-corekit"]
#
# [tool.uv.sources]
# btm-corekit = { path = "../.corekit", editable = true }
# ///

"""Scratchpad and verifier for open-question research sessions.

The script serves two purposes and few others. As the scratchpad, `note`
admits one JSON batch of findings per round: leaves, sources, closes, the
rival sweep, a checkpoint. As the verifier, `check` replays the ledger
into a drafting scaffold: derived sections, numbered sources, violations,
hedges. The invoking agent owns every judgment call; the script owns
identity, memory, counting, and verification.

Identifiers are minted here, by the repository's shared btm-corekit
kernel: the agent supplies two or three keywords,
the script returns the full identifier (keyword slug plus a 128-bit
entropy suffix) for the agent to use in later calls, and every output
echoes the canonical identifier. A uniquely-resolving keyword subset
recovers an identifier lost to context compression, signaled and
re-echoed on use.

Configuration travels as command-line parameters; JSON content travels
on stdin. Every call names its session: several agents may share one
state root, so the script holds no ambient subject. Subcommands print
one JSON document to stdout; advisory `signal:` lines go to stderr and
never block; invariant violations print `error:` to stderr and exit 1
without appending anything.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterable
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from btm_corekit import (
    Ambiguous,
    CommandError,
    Exact,
    NoMatch,
    Recovered,
    band_signal,
    eliminate,
    is_pathlike,
    mint,
    resolve,
    slugify,
    state_root,
    tree_bytes,
)

SOURCE_CLASSES = ("constitutive", "attested", "measured", "reported")
ORIGINS = ("frame", "spawned")
CLOSE_STATES = ("retrieved", "refuted", "unresolved", "retired")
UNRESOLVED_REASONS = ("searched", "not_pursued")
RETIRED_REASONS = ("folded", "immaterial")
CHAIN_MIN_LINKS = 2  # a Chain section renders past this many retrieved leaves
MAX_EVENTS = 1000  # runaway backstop; a real run stays under ~100 events


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


# --- pure core: batch expansion (the note smart constructor, stage one) ---


def _detail_of(raw: dict[str, Any]) -> str:
    """`into` carries a fold target ref; `detail` carries every other reason."""
    key = "into" if raw.get("reason") == "folded" else "detail"
    return str(raw.get(key) or "")


def _resolve_ref(
    ref: str,
    ids: AbstractSet[str],
    kind: str,
    fresh: AbstractSet[str],
    advisories: list[str],
) -> str:
    """Resolve one reference, recording recovery for ids outside `fresh`.

    A keyword match inside `fresh` is the designed path (the full id is
    born in this very batch), so only a match outside it records recovery.
    """
    full, note = eliminate(resolve(ref, ids), ref, kind)
    if note and full not in fresh:
        advisories.append(note)
    return full


def expand_batch(
    ledger: Ledger, batch: dict[str, Any], minter: Callable[[Iterable[str]], str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]], list[str]]:
    """Resolve keyword references and mint ids for one note batch.

    Admission order inside a batch: leaves, sources, closes, sweep,
    checkpoint, so later entries may reference ids minted earlier in the
    same batch. Returns the expanded events, the minted-id maps, and the
    advisory signals for the shell to render.
    """
    known = {"leaves", "sources", "closes", "sweeps", "checkpoints"}
    unknown = set(batch) - known
    _require(not unknown, f"unknown note keys: {', '.join(sorted(unknown))}")
    minted: dict[str, dict[str, str]] = {"leaves": {}, "sources": {}}
    advisories: list[str] = []
    fresh: set[str] = set()
    leaf_ids = set(ledger.leaves)
    source_ids = set(ledger.sources)
    events: list[dict[str, Any]] = []

    def admit(kind: str, entry: dict[str, Any], into: set[str]) -> str:
        full = minter(entry.get("kw") or [])
        stem = full.rsplit("-", 1)[0]
        _require(
            stem not in minted[kind],
            f"duplicate keywords in one batch: {stem}; vary one keyword",
        )
        minted[kind][stem] = full
        if advice := band_signal(stem):
            advisories.append(advice)
        fresh.add(full)
        into.add(full)
        return full

    for entry in batch.get("leaves") or []:
        full = admit("leaves", entry, leaf_ids)
        events.append(
            {
                "e": "add_leaf",
                "id": full,
                "q": entry.get("q"),
                "origin": entry.get("origin", "frame"),
            }
        )
    for entry in batch.get("sources") or []:
        full = admit("sources", entry, source_ids)
        events.append(
            {
                "e": "add_source",
                "id": full,
                "leaf": _resolve_ref(
                    str(entry.get("leaf") or ""), leaf_ids, "leaf", fresh, advisories
                ),
                "cls": entry.get("cls"),
                "title": entry.get("title"),
                "url": entry.get("url", ""),
            }
        )
    for entry in batch.get("closes") or []:
        event: dict[str, Any] = {
            "e": "close",
            "leaf": _resolve_ref(
                str(entry.get("leaf") or ""), leaf_ids, "leaf", fresh, advisories
            ),
            "state": entry.get("state"),
        }
        if entry.get("sources"):
            event["sources"] = [
                _resolve_ref(str(ref), source_ids, "source", fresh, advisories)
                for ref in entry["sources"]
            ]
        if entry.get("premise"):
            event["premise"] = entry["premise"]
        if entry.get("reason"):
            event["reason"] = entry["reason"]
            detail = _detail_of(entry)
            if entry["reason"] == "folded":
                detail = _resolve_ref(detail, leaf_ids, "leaf", fresh, advisories)
            event["detail"] = detail
        events.append(event)
    for entry in batch.get("sweeps") or []:
        events.append({"e": "sweep", **entry})
    for entry in batch.get("checkpoints") or []:
        events.append({"e": "checkpoint", **entry})
    _require(bool(events), "empty note: nothing to record")
    return events, minted, advisories


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


def counts_of(ledger: Ledger) -> dict[str, int]:
    tally: dict[str, int] = {}
    for leaf in ledger.leaves.values():
        key = leaf_view(leaf.state)["state"]
        tally[key] = tally.get(key, 0) + 1
    return tally


# --- imperative shell ---


def sessions_root() -> Path:
    return state_root("btm-research") / "sessions"


def session_ids() -> list[str]:
    root = sessions_root()
    if not root.exists():
        return []
    return sorted(entry.name for entry in root.iterdir() if entry.is_dir())


def resolved_session(ref: str) -> Path:
    """Eliminate a session Resolution at the shell, rendering its signal."""
    full, note = eliminate(
        resolve(ref, session_ids()),
        ref,
        "session",
        hint="open with --question creates one",
    )
    if note:
        signal(note)
    return sessions_root() / full


def session_dir(ref: str) -> Path:
    if is_pathlike(ref):
        return Path(ref).expanduser()
    return resolved_session(ref)


def ledger_path(directory: Path) -> Path:
    return directory / "ledger.jsonl"


def read_events(directory: Path) -> list[dict[str, Any]]:
    path = ledger_path(directory)
    if not path.exists():
        raise CommandError(f"no session at {directory}; open with --question creates")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_events(directory: Path, admitted: list[dict[str, Any]]) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = "".join(
        json.dumps({"t": stamp, **raw}, ensure_ascii=False) + "\n" for raw in admitted
    )
    with ledger_path(directory).open("a", encoding="utf-8") as handle:
        handle.write(payload)


def read_meta(directory: Path) -> dict[str, Any]:
    path = directory / "session.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def emit(document: dict[str, Any]) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))


def signal(message: str) -> None:
    print(f"signal: {message}", file=sys.stderr)


def orient(directory: Path) -> dict[str, Any]:
    """The re-orientation payload: everything a resumed agent needs first."""
    events = read_events(directory)
    ledger = replay(events)
    return {
        "session": directory.name,
        "question": read_meta(directory).get("question"),
        "focus": read_meta(directory).get("focus"),
        "counts": counts_of(ledger),
        "open": [
            {"id": leaf_id, "q": leaf.question}
            for leaf_id, leaf in ledger.leaves.items()
            if isinstance(leaf.state, Open)
        ],
        "swept": ledger.swept,
        "yield": yield_table(events),
    }


def create_session(directory: Path, name: str, args: argparse.Namespace) -> int:
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
    emit({"session": name, **meta})
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    ref = args.ref
    if is_pathlike(ref):
        directory = Path(ref).expanduser()
        if not args.question:
            _require(
                ledger_path(directory).exists(),
                f"no session at {directory}; pass --question to create one",
            )
            emit(orient(directory))
            return 0
        _require(
            not ledger_path(directory).exists(),
            f"session already exists at {directory}",
        )
        return create_session(directory, str(directory), args)
    match resolve(ref, session_ids()):
        case Exact(sid):
            emit(orient(sessions_root() / sid))
        case Recovered(sid):
            signal(f"recovered session '{ref}' -> {sid}; use the full identifier")
            emit(orient(sessions_root() / sid))
        case Ambiguous(candidates):
            raise CommandError(
                f"'{ref}' is ambiguous across sessions: {', '.join(candidates)}"
            )
        case NoMatch():
            _require(
                bool(args.question),
                f"no session matches '{ref}'; pass --question to create one",
            )
            full = mint(ref.split())
            if advice := band_signal(full.rsplit("-", 1)[0]):
                signal(advice)
            return create_session(sessions_root() / full, full, args)
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    directory = session_dir(args.session)
    raw = sys.stdin.read()
    _require(bool(raw.strip()), "note reads the JSON batch from stdin")
    batch = json.loads(raw)
    _require(isinstance(batch, dict), "note takes one JSON object")
    events = read_events(directory)
    ledger = replay(events)
    expanded, minted, advisories = expand_batch(ledger, batch, mint)
    for event in expanded:
        apply(ledger, event)
    append_events(directory, expanded)
    for line in advisories:
        signal(line)
    emit(
        {
            "session": directory.name,
            "minted": minted,
            "counts": counts_of(ledger),
            "open": [
                leaf_id
                for leaf_id, leaf in ledger.leaves.items()
                if isinstance(leaf.state, Open)
            ],
            "yield": yield_table(events + expanded),
        }
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
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
    signal("Boundary section is yours: render it where the answer flips inside scope")
    emit(
        {
            "session": directory.name,
            "question": read_meta(directory).get("question"),
            "sections": sections(ledger),
            "violations": found,
            "hedges": hedges(ledger),
            "yield": yield_table(events),
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
    root = sessions_root()
    if args.all and args.session:
        raise CommandError("pass a session or --all, one of the two")
    if args.all:
        if not root.is_dir():
            emit({"removed": None, "bytes_freed": 0})
            return 0
        freed = tree_bytes(root)
        shutil.rmtree(root)
        emit({"removed": str(root), "bytes_freed": freed})
        return 0
    if args.session is None:
        listing = (
            [
                {"session": entry.name, "bytes": tree_bytes(entry)}
                for entry in sorted(root.iterdir())
                if entry.is_dir()
            ]
            if root.is_dir()
            else []
        )
        emit(
            {
                "sessions_root": str(root),
                "sessions": listing,
                "next": "pass a session identifier or --all to remove and free space",
            }
        )
        return 0
    target = session_dir(args.session)
    if not ledger_path(target).is_file():
        raise CommandError(
            f"{target} holds no session (ledger.jsonl absent); refusing to remove"
        )
    freed = tree_bytes(target)
    shutil.rmtree(target)
    emit({"removed": str(target), "bytes_freed": freed})
    return 0


def cmd_selftest(_args: argparse.Namespace) -> int:  # noqa: PLR0915  linear law list
    """Law checks: minting, resolution, batch expansion, transitions, views."""
    checks = 0

    def fixed_mint(words: Iterable[str]) -> str:
        return slugify(words) + "-0123456789abcdefghijklmnop"[:32]

    def rejects(thunk: Callable[[], Any], why: str) -> None:
        nonlocal checks
        try:
            thunk()
        except CommandError:
            checks += 1
            return
        raise AssertionError(f"expected rejection: {why}")

    suffix_len = 26
    minted = mint(["mitm", "fingerprint"])
    assert minted.startswith("mitm-fingerprint-")
    assert len(minted.rsplit("-", 1)[1]) == suffix_len
    assert minted.rsplit("-", 1)[1] == minted.rsplit("-", 1)[1].lower()
    assert mint(["a b", "C/d"]).startswith("a-b-c-d-")
    assert band_signal("solo") and band_signal("a-b-c-d")
    assert band_signal("two-words") is None
    checks += 5

    pool = ["tls-pin-abc123", "tls-cert-def456", "aws-east-ghi789"]
    assert resolve("tls-pin-abc123", pool) == Exact("tls-pin-abc123")
    assert resolve("pin", pool) == Recovered("tls-pin-abc123")
    assert resolve("aws east", pool) == Recovered("aws-east-ghi789")
    assert resolve("tls", pool) == Ambiguous(("tls-cert-def456", "tls-pin-abc123"))
    assert resolve("quic", pool) == NoMatch()
    checks += 5

    ledger = Ledger()
    batch = {
        "leaves": [
            {"kw": ["rent", "length"], "q": "what does Rent guarantee"},
            {"kw": ["pool", "clear"], "q": "clearArray semantics", "origin": "spawned"},
            {"kw": ["memory", "pool"], "q": "when to prefer MemoryPool"},
        ],
        "sources": [
            {
                "kw": ["bcl", "rent"],
                "leaf": "rent length",
                "cls": "constitutive",
                "title": "BCL source",
            },
            {
                "kw": ["blog", "folk"],
                "leaf": "clear",
                "cls": "reported",
                "title": "folk belief post",
            },
        ],
        "closes": [
            {"leaf": "rent length", "state": "retrieved", "sources": ["bcl"]},
            {
                "leaf": "pool clear",
                "state": "refuted",
                "sources": ["folk"],
                "premise": "assumed exact-length",
            },
            {
                "leaf": "memory",
                "state": "retired",
                "reason": "folded",
                "into": "rent length",
            },
        ],
        "sweeps": [
            {"checked": "rival accounts", "candidates": ["folk"], "survivors": []}
        ],
        "checkpoints": [{"label": "round-1", "searches": 4}],
    }
    events, minted_map, advisories = expand_batch(ledger, batch, fixed_mint)
    for event in events:
        apply(ledger, event)
    assert advisories == []  # intra-batch keyword refs are the designed path
    assert sorted(len(v) for v in minted_map.values()) == [2, 3]
    assert sections(ledger) == ["answer", "rival", "sources"]
    assert violations(ledger) == []
    assert yield_table(events) == [
        {"label": "round-1", "searches": 4, "new_sources": 2, "yield": 0.5}
    ]
    assert stated(["reported"]) == "hedged" and stated(["attested"]) == "plain"
    assert stated(["measured"]) == "hedged"
    assert stated(["measured", "measured"]) == "plain"
    checks += 8

    recovery_batch = {
        "sources": [
            {"kw": ["extra", "doc"], "leaf": "rent", "cls": "reported", "title": "t"}
        ]
    }
    _, _, recovery = expand_batch(ledger, recovery_batch, fixed_mint)
    assert any(line.startswith("recovered leaf 'rent'") for line in recovery)
    checks += 1

    contrary = {
        "closes": [
            {
                "leaf": "rent length",
                "state": "refuted",
                "sources": ["bcl"],
                "premise": "late contrary evidence",
            }
        ]
    }
    events2, _, _ = expand_batch(ledger, contrary, fixed_mint)
    for event in events2:
        apply(ledger, event)  # Retrieved -> Refuted is the one legal bend
    assert any("fold broken" in line for line in violations(ledger))
    checks += 1

    def refute_terminal() -> None:
        closes = {
            "closes": [
                {"leaf": "pool clear", "state": "retrieved", "sources": ["folk"]}
            ]
        }
        for event in expand_batch(ledger, closes, fixed_mint)[0]:
            apply(ledger, event)

    rejects(refute_terminal, "Refuted is terminal")
    rejects(lambda: expand_batch(ledger, {}, fixed_mint), "empty note")
    rejects(
        lambda: expand_batch(
            Ledger(), {"leaves": [{"kw": ["!!"], "q": "x"}]}, fixed_mint
        ),
        "unsluggable keywords",
    )
    rejects(
        lambda: expand_batch(
            Ledger(),
            {"leaves": [{"kw": ["a", "b"], "q": "x"}, {"kw": ["a", "b"], "q": "y"}]},
            fixed_mint,
        ),
        "duplicate keywords in one batch",
    )
    fresh = Ledger()
    apply(fresh, {"e": "add_leaf", "id": "solo-x", "q": "q"})
    rejects(
        lambda: apply(
            fresh,
            {
                "e": "close",
                "leaf": "solo-x",
                "state": "retired",
                "reason": "folded",
                "detail": "solo-x",
            },
        ),
        "fold target not retrieved",
    )
    rejects(
        lambda: apply(
            fresh, {"e": "sweep", "checked": "x", "candidates": [], "survivors": ["a"]}
        ),
        "survivors outside candidates",
    )
    emit({"selftest": "ok", "checks": checks})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    opener = commands.add_parser("open")
    opener.set_defaults(func=cmd_open)
    opener.add_argument("ref", help="two or three keywords in one quoted argument")
    opener.add_argument("--question")
    opener.add_argument("--focus", default=None)
    note = commands.add_parser("note")
    note.set_defaults(func=cmd_note)
    note.add_argument("session", help="session identifier; batch JSON on stdin")
    check = commands.add_parser("check")
    check.set_defaults(func=cmd_check)
    check.add_argument("session", help="session identifier")
    clean = commands.add_parser("clean")
    clean.set_defaults(func=cmd_clean)
    clean.add_argument("session", nargs="?")
    clean.add_argument("--all", action="store_true")
    selftest = commands.add_parser("selftest")
    selftest.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
