"""Book extension hooks: files under the book's `lib/` the core looks for and
calls beside or in place of its defaults. The measuring stick stays in the
core: a hook reads through core objects and never replaces data, `Market`
scoping, hashing, trial counting, or the gate.

- `lib/sources/<name>.py` `fetch(since, config) -> Loaded`: `load <name>`
  when no built-in source has the name.
- `lib/market/<name>.py` `extend(market) -> {name: callable}`: attached to
  the `Market` `signal.py` sees; a core accessor name is refused.
- `lib/metrics/<name>.py` `metric(returns, positions, market) -> float or
  None`: `scorecard.extra.<name>`, never a gate.
- `lib/sizing.py` `weights(sleeves, limits) -> {strategy: weight}`: the
  Kelly step of `check --propose`; `entry_weight`, `max_weight` per name,
  and the ruin scale still apply.
- `lib/costs.py` `cost(trade, market) -> float`: proportional cost of one
  `Trade`, in place of half-spread, commission, and impact.
- `lib/brief.py` `lines(book) -> [str]`: appended to `check --brief` within
  twelve lines.

A hook imports what it needs at module top: the book root is importable
while its module runs.

A hook's key is `<hook>/<name>`, the file stem for the single-file hooks
(`sizing/sizing`); its digest is that of the file's AST dump, so
whitespace and comments never move it. Run lines record the measured hooks,
proposals the proposed ones; `measure --repeat` refuses a moved or vanished
digest.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from btm_corekit import CommandError
from btm_finance.api import Market
from btm_finance.loader import load_file
from btm_finance.measuring import CostModel, Metric
from btm_finance.repeat import source_digest

LIB = "lib"


class Hook(StrEnum):
    SOURCES = "sources"
    MARKET = "market"
    METRICS = "metrics"
    SIZING = "sizing"
    COSTS = "costs"
    BRIEF = "brief"

    @property
    def many(self) -> bool:
        """A directory of named files, else one file named for the hook."""
        return self in {Hook.SOURCES, Hook.MARKET, Hook.METRICS}

    @property
    def entry(self) -> str:
        """The function the core calls."""
        match self:
            case Hook.SOURCES:
                return "fetch"
            case Hook.MARKET:
                return "extend"
            case Hook.METRICS:
                return "metric"
            case Hook.SIZING:
                return "weights"
            case Hook.COSTS:
                return "cost"
            case Hook.BRIEF:
                return "lines"


MEASURED = (Hook.MARKET, Hook.METRICS, Hook.COSTS)
"""Hooks `measure` uses: recorded on the run line."""
PROPOSED = (Hook.SIZING, Hook.BRIEF)
"""Hooks recorded on the proposal."""


@dataclass(frozen=True, slots=True)
class Found:
    """One hook file present in the book."""

    hook: Hook
    name: str
    path: Path

    @property
    def key(self) -> str:
        return f"{self.hook.value}/{self.name}"

    @property
    def shown(self) -> str:
        if self.hook.many:
            return f"{LIB}/{self.hook.value}/{self.name}.py"
        return f"{LIB}/{self.hook.value}.py"


def found(root: Path, hooks: Iterable[Hook] = tuple(Hook)) -> list[Found]:
    """Every hook file present, by hook then name; `__init__.py` and names
    starting `_` are helpers, not hooks."""
    lib = root / LIB
    files: list[Found] = []
    for hook in hooks:
        if not hook.many:
            path = lib / f"{hook.value}.py"
            if path.is_file():
                files.append(Found(hook, hook.value, path))
            continue
        folder = lib / hook.value
        paths = sorted(folder.glob("*.py")) if folder.is_dir() else []
        files += [Found(hook, p.stem, p) for p in paths if not p.stem.startswith("_")]
    return files


def hook_digest(item: Found) -> str:
    """The digest of the file's AST dump."""
    try:
        data = item.path.read_bytes()
    except OSError as err:
        raise CommandError(f"cannot read {item.shown}: {err}") from err
    return source_digest(data, item.shown)


def digests(items: Iterable[Found]) -> dict[str, str]:
    return {item.key: hook_digest(item) for item in items}


def drift(recorded: Mapping[str, str], now: Mapping[str, str]) -> list[str]:
    """Each recorded hook whose digest moved or whose file vanished."""
    return [
        f"{key} {'vanished' if key not in now else 'moved'}"
        for key in sorted(recorded)
        if recorded[key] != now.get(key)
    ]


def unrecorded(recorded: Mapping[str, str], now: Mapping[str, str]) -> list[str]:
    """Hooks present now that the line did not record: advisory only."""
    return sorted(set(now) - set(recorded))


def entry_of(root: Path, item: Found) -> Callable[..., Any]:
    """The hook's entry function, its module run once."""
    module = load_file(root, item.path)
    function: object = vars(module).get(item.hook.entry)
    if not callable(function):
        raise CommandError(f"{item.shown} defines no {item.hook.entry}()")
    found: Callable[..., Any] = function
    return found


def entries(root: Path, hook: Hook) -> dict[str, Callable[..., Any]]:
    """Every file of one hook, by name, loaded."""
    return {item.name: entry_of(root, item) for item in found(root, (hook,))}


def single(root: Path, hook: Hook) -> Callable[..., Any] | None:
    """A single-file hook's entry, or None when the book has none."""
    return entries(root, hook).get(hook.value)


CORE = frozenset(name for name in dir(Market) if not name.startswith("_"))
"""`Market`'s own accessors: no extension may take one of these names."""


class Extended:
    """A `Market` with the book's accessors beside the core ones; every core
    name resolves on the core `Market`, which is already scoped."""

    __slots__ = ("_core", "_extra")

    def __init__(self, core: Market, extra: Mapping[str, Callable[..., Any]]) -> None:
        self._core = core
        self._extra = dict(extra)

    def __getattr__(self, name: str) -> Any:
        if name in self._extra:
            return self._extra[name]
        return getattr(self._core, name)


Extender = Callable[[Market], Any]


def attach(market: Market, extenders: Mapping[str, Extender]) -> Market | Extended:
    """The core `Market` with each extension's callables attached; refuses a
    name that shadows a core accessor or another extension's."""
    if not extenders:
        return market
    extra: dict[str, Callable[..., Any]] = {}
    for file, extend in sorted(extenders.items()):
        made = extend(market)
        if not isinstance(made, Mapping):
            raise CommandError(f"lib/market/{file}.py extend returned no mapping")
        for name, function in made.items():
            if not isinstance(name, str) or not name.isidentifier() or name[:1] == "_":
                raise CommandError(f"lib/market/{file}.py: {name!r} is no public name")
            if name in CORE or name in extra:
                raise CommandError(
                    f"lib/market/{file}.py: {name} shadows "
                    + ("a core Market accessor" if name in CORE else "another hook")
                )
            if not callable(function):
                raise CommandError(f"lib/market/{file}.py: {name} is not callable")
            extra[name] = function
    return Extended(market, extra)


Signal = Callable[[Any, Mapping[str, float]], Any]


def extended(strategy: Signal, extenders: Mapping[str, Extender]) -> Signal:
    """`strategy` handed each day's `Market` with the book's accessors."""
    if not extenders:
        return strategy

    def call(market: Market, params: Mapping[str, float]) -> Any:
        return strategy(attach(market, extenders), params)

    return call


@dataclass(frozen=True, slots=True)
class Measured:
    """The book's `measure` hooks, loaded once: market accessors and metrics
    by file name, the cost model, and every digest for the run line."""

    market: Mapping[str, Extender]
    metrics: Mapping[str, Metric]
    cost: CostModel | None
    digests: Mapping[str, str]

    @property
    def costs(self) -> str:
        """The run line's `costs`: the book file, or `default`."""
        return f"{LIB}/{Hook.COSTS.value}.py" if self.cost is not None else "default"


def measured(root: Path, only: Iterable[str] | None = None) -> Measured:
    """Every `measure` hook present, or with `only` those whose keys it
    names: a repeat loads what its run line recorded."""
    kept = None if only is None else frozenset(only)
    items = [i for i in found(root, MEASURED) if kept is None or i.key in kept]
    loaded = {item.key: entry_of(root, item) for item in items}

    def of(hook: Hook) -> dict[str, Callable[..., Any]]:
        return {i.name: loaded[i.key] for i in items if i.hook is hook}

    return Measured(
        market=of(Hook.MARKET),
        metrics=of(Hook.METRICS),
        cost=of(Hook.COSTS).get(Hook.COSTS.value),
        digests=digests(items),
    )


@dataclass(frozen=True, slots=True)
class Use:
    """When one hook was used: a run line, a proposal, or a load."""

    key: str
    ts: str


def table(
    present: Sequence[Found], uses: Iterable[Use], today: date, idle_days: int
) -> list[dict[str, Any]]:
    """One row per hook file: uses, last use, idle when unused for
    `idle_days`. O(files + uses)."""
    counts: dict[str, int] = {}
    last: dict[str, str] = {}
    for use in uses:
        counts[use.key] = counts.get(use.key, 0) + 1
        last[use.key] = max(use.ts, last.get(use.key, use.ts))
    rows: list[dict[str, Any]] = []
    for item in present:
        stamp = last.get(item.key)
        try:
            age = None if stamp is None else (today - date.fromisoformat(stamp[:10]))
        except ValueError:
            age = None
        rows.append(
            {
                "hook": item.hook.value,
                "name": item.name,
                "path": item.shown,
                "runs": counts.get(item.key, 0),
                "last": stamp,
                "idle": age is None or age.days > idle_days,
            }
        )
    return rows
