"""`measure --repeat`, pure: what stops a rerun, and the scorecard diff.

A rerun is refused, never approximated, when its inputs moved: code, raw
data, or a peer's stored series. The shell reads git and the store; this
module judges.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping, Sequence
from enum import StrEnum

from btm_corekit import CommandError, Model
from btm_finance.measuring import number

CONFIG = "config.json"


class Presence(StrEnum):
    """One manifest-listed file against its bytes on disk."""

    INTACT = "intact"
    CHANGED = "changed"
    VANISHED = "vanished"


class Rule(StrEnum):
    """How one leaf was compared: absolute at or below 1, relative above."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    EXACT = "exact"


class Diff(Model):
    path: str
    recorded: object
    recomputed: object
    rule: Rule


class RepeatReport(Model):
    run_id: str
    strategy: str
    reproduced: bool
    tolerance: float
    compared: int
    diffs: tuple[Diff, ...]
    advisories: tuple[str, ...]


def canonical_source(source: bytes, name: str = "signal.py") -> bytes:
    """`ast.dump` of the module: whitespace and comments never move it; a
    Python upgrade that changes the dump does."""
    try:
        return ast.dump(ast.parse(source)).encode()
    except (SyntaxError, ValueError) as err:
        raise CommandError(f"{name} does not parse: {err}") from err


def canonical_config(config: bytes) -> bytes:
    """Parsed JSON, keys sorted, fixed separators: indentation never moves it."""
    try:
        parsed = json.loads(config)
    except ValueError as err:
        raise CommandError(f"config.json is not JSON: {err}") from err
    return json.dumps(
        parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def canonical(path: str, data: bytes) -> bytes:
    """`config.json` as parsed JSON, any other code file as its AST dump."""
    if path.rpartition("/")[2] == CONFIG:
        return canonical_config(data)
    return canonical_source(data, path)


def code_drift(
    then: Mapping[str, bytes],
    now: Mapping[str, bytes | None],
    reached: Sequence[str],
) -> list[str]:
    """Code paths whose canonical form moved from the recorded blob (`then`,
    from `git cat-file`) against the working tree (`now`, None when gone), then
    each path the strategy reaches today that the run did not."""
    moved = [
        path
        for path in sorted(then)
        if now.get(path) is None
        or canonical(path, then[path]) != canonical(path, now[path] or b"")
    ]
    return moved + sorted(set(reached) - set(then))


def data_drift(
    recorded: str,
    current: str,
    presence: Sequence[tuple[str, Presence]],
    added: Sequence[str],
) -> list[str]:
    """Raw files whose bytes left the manifest, then, when the snapshot moved,
    source files listed after the run. O(files)."""
    problems = [
        f"{path} {state.value} since listed in data/manifest.json"
        for path, state in presence
        if state is not Presence.INTACT
    ]
    if recorded != current:
        problems += [f"{path} loaded after the run" for path in added]
        if not problems:
            problems.append(
                "data_snapshot differs: a source digest in data/manifest.json "
                "was edited or removed"
            )
    return problems


def peer_drift(peers: Mapping[str, Presence | None]) -> list[str]:
    """Each listed peer whose returns file is unlisted (None), gone, or edited."""
    return [
        f"peer {run_id}: returns file "
        + ("not listed in data/manifest.json" if state is None else state.value)
        for run_id, state in peers.items()
        if state is not Presence.INTACT
    ]


def leaf(
    path: str, recorded: object, recomputed: object, tolerance: float
) -> Diff | None:
    """One leaf: numbers within `tolerance` (absolute when both magnitudes are
    at or below 1, relative to the larger otherwise); anything else equal."""
    a, b = number(recorded), number(recomputed)
    if a is None or b is None:
        if recorded == recomputed:
            return None
        return Diff(
            path=path, recorded=recorded, recomputed=recomputed, rule=Rule.EXACT
        )
    scale = max(abs(a), abs(b))
    rule = Rule.ABSOLUTE if scale <= 1.0 else Rule.RELATIVE
    bound = tolerance if rule is Rule.ABSOLUTE else tolerance * scale
    if abs(a - b) <= bound:
        return None
    return Diff(path=path, recorded=recorded, recomputed=recomputed, rule=rule)


def compare(
    recorded: object, recomputed: object, tolerance: float, path: str = "scorecard"
) -> tuple[int, list[Diff]]:
    """Leaves compared and every diff, keys in sorted order; a key on one side
    only, or lists of different length, is one diff. O(leaves)."""
    if isinstance(recorded, Mapping) and isinstance(recomputed, Mapping):
        count, diffs = 0, []
        for key in sorted(set(recorded) | set(recomputed), key=str):
            if key not in recorded or key not in recomputed:
                diffs.append(
                    Diff(
                        path=f"{path}.{key}",
                        recorded=recorded.get(key),
                        recomputed=recomputed.get(key),
                        rule=Rule.EXACT,
                    )
                )
                count += 1
                continue
            more, found = compare(
                recorded[key], recomputed[key], tolerance, f"{path}.{key}"
            )
            count, diffs = count + more, diffs + found
        return count, diffs
    if (
        isinstance(recorded, list | tuple)
        and isinstance(recomputed, list | tuple)
        and len(recorded) == len(recomputed)
    ):
        count, diffs = 0, []
        for index, (a, b) in enumerate(zip(recorded, recomputed, strict=True)):
            more, found = compare(a, b, tolerance, f"{path}[{index}]")
            count, diffs = count + more, diffs + found
        return count, diffs
    found_leaf = leaf(path, recorded, recomputed, tolerance)
    return 1, [] if found_leaf is None else [found_leaf]


def advisories(recorded: Mapping[str, str], current: Mapping[str, str]) -> list[str]:
    """Engine entries that moved: the skill commit and library versions."""
    return [
        f"{name} {recorded.get(name)} -> {current.get(name)}"
        for name in sorted(set(recorded) | set(current))
        if recorded.get(name) != current.get(name)
    ]
