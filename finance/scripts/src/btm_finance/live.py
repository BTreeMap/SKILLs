"""`check --live`, pure: each paper or live sleeve's realized path from its
fills against the scorer's model path, the review bounds, and the report.

A sleeve's capital is its first fill day's gross traded value; later fills
self-finance from its cash, which earns `rf`. Opening holdings belong to no
sleeve. The command takes no action: a pause is the operator's decision.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

import numpy as np

from btm_corekit import Model
from btm_finance.data.panel import Panel
from btm_finance.data.tables import Days, Floats, date_of, day_of
from btm_finance.engine import max_drawdown
from btm_finance.engine.metrics import PERIODS_PER_YEAR
from btm_finance.models import Side, Status
from btm_finance.scoring import Setting, Strategy, run_variant

STALE_DAYS = 5  # trading days without a new bar before data counts as stale
WEEK = 7  # calendar days one recorded breach covers
REPORT_LINES = 20
NEXT = (
    "read each breach with the operator; a pause is a decision line plus the "
    "operator's edit of strategies/<name>/status, never this command"
)
Series = tuple[Days, Floats]


class Watch(StrEnum):
    """Incident kinds `check --live` writes."""

    DRAWDOWN = "drawdown"
    UNDERPERFORM = "underperform"
    SLIPPAGE = "slippage"
    TRACKING = "tracking"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class Fill:
    """One sleeve fill: quantity signed by side; `reference` is the
    proposal's price for that order, when known."""

    symbol: str
    signed: float
    price: float
    day: int
    reference: float | None


def fill_of(row: Mapping[str, Any], reference: float | None) -> Fill:
    side = Side(str(row["side"]))
    quantity = float(row["quantity"])
    return Fill(
        symbol=str(row["symbol"]),
        signed=quantity if side is Side.BUY else -quantity,
        price=float(row["price"]),
        day=day_of(date.fromisoformat(str(row["date"]))),
        reference=reference,
    )


def reference_prices(proposals: Mapping[str, Any]) -> dict[tuple[str, str, str], float]:
    """(proposal stem, symbol, side) to that order's `price`, the reference
    close `advise` sized it at. O(orders)."""
    found: dict[tuple[str, str, str], float] = {}
    for stem, document in proposals.items():
        orders = document.get("orders") if isinstance(document, Mapping) else None
        for order in orders if isinstance(orders, list) else []:
            price = order.get("price") if isinstance(order, Mapping) else None
            if isinstance(price, int | float) and not isinstance(price, bool):
                key = (stem, str(order.get("symbol")), str(order.get("side")))
                found[key] = float(price)
    return found


def carried(grid: Floats) -> Floats:
    """Each NaN takes the last finite value above it, else the first below;
    an all-NaN column stays NaN. O(T N)."""
    rows = np.arange(grid.shape[0])[:, None]
    columns = np.arange(grid.shape[1])
    known = np.isfinite(grid)
    last = np.maximum.accumulate(np.where(known, rows, 0), axis=0)
    out = grid[last, columns]
    first = grid[np.argmax(known, axis=0), columns]
    return np.where(np.isfinite(out), out, first[None, :])


@dataclass(frozen=True, slots=True, eq=False)
class Sleeve:
    """Realized daily returns from the first fill day; `late` counts fills
    dated after the last bar, `unpriced` symbols marked at fill price."""

    dates: Days
    returns: Floats
    late: int
    unpriced: tuple[str, ...]


def realized(fills: Sequence[Fill], panel: Panel, rf: Floats) -> Sleeve | None:
    """Units are shares over the fill day's `adj`, marked at `close * adj`.
    O(D S + F) for D days from the first fill, S symbols, F fills."""
    if not fills:
        return None
    start = int(np.searchsorted(panel.dates, min(f.day for f in fills), side="left"))
    dates = panel.dates[start:]
    if not len(dates):
        return None
    rows = np.searchsorted(dates, [f.day for f in fills], side="left")
    kept = [
        (f, int(r)) for f, r in zip(fills, rows.tolist(), strict=True) if r < len(dates)
    ]
    symbols = sorted({f.symbol for f, _ in kept})
    index = {name: column for column, name in enumerate(panel.names)}
    place = {name: column for column, name in enumerate(symbols)}
    width = len(symbols)
    price = np.full((len(dates), width), np.nan)
    adj = np.ones((len(dates), width))
    for column, symbol in enumerate(symbols):
        if symbol in index:
            price[:, column] = (panel.close * panel.adj)[start:, index[symbol]]
            adj[:, column] = panel.adj[start:, index[symbol]]
    price, adj = carried(price), np.nan_to_num(carried(adj), nan=1.0)
    unpriced = tuple(
        s for c, s in enumerate(symbols) if not np.isfinite(price[:, c]).any()
    )
    for symbol in unpriced:
        column = place[symbol]
        price[:, column] = next(f.price for f, _ in kept if f.symbol == symbol)
        adj[:, column] = 1.0
    units = np.zeros((len(dates), width))
    flow = np.zeros(len(dates))
    for fill, row in kept:
        column = place[fill.symbol]
        units[row, column] += fill.signed / adj[row, column]
        flow[row] -= fill.signed * fill.price
    capital = sum(abs(f.signed) * f.price for f, r in kept if r == 0)
    interest = 1.0 + rf[start:]
    interest[0] = 1.0
    growth = np.cumprod(interest)
    cash = growth * (capital + np.cumsum(flow / growth))
    nav = cash + (np.cumsum(units, axis=0) * price).sum(axis=1)
    before = np.concatenate(([capital], nav[:-1]))
    return Sleeve(dates, nav / before - 1.0, len(fills) - len(kept), unpriced)


def model_path(
    setting: Setting, strategy: Strategy, params: Mapping[str, float]
) -> Series | None:
    """The scorer's base run, net of modeled costs: one simulation."""
    variant = run_variant(setting, strategy, params)
    return None if variant is None else (variant.dates, variant.cost.net)


def since(series: Series, first: int) -> Series:
    dates, values = series
    cut = int(np.searchsorted(dates, first, side="left"))
    return dates[cut:], values[cut:]


def aligned(a: Series, b: Series) -> tuple[Days, Floats, Floats]:
    shared, left, right = np.intersect1d(a[0], b[0], return_indices=True)
    return shared, a[1][left], b[1][right]


def tracking_error(sleeve: Sleeve, model: Series) -> float | None:
    """Annualized std of realized minus model on shared days. O(D log D)."""
    _, mine, theirs = aligned((sleeve.dates, sleeve.returns), model)
    if len(mine) < 2:  # noqa: PLR2004 - a std needs two days
        return None
    return float(np.std(mine - theirs, ddof=1) * math.sqrt(PERIODS_PER_YEAR))


def slippage(fills: Sequence[Fill]) -> float | None:
    """Mean of (fill minus reference) over reference, sign flipped for sells:
    positive is cost. Fills without a reference are left out."""
    shares = [
        math.copysign(1.0, f.signed) * (f.price - f.reference) / f.reference
        for f in fills
        if f.reference
    ]
    return float(np.mean(shares)) if shares else None


def monthly(dates: Days, returns: Floats) -> Floats:
    """Compounded return per calendar month, oldest first. O(D)."""
    months = dates.astype("datetime64[D]").astype("datetime64[M]").astype(np.int64)
    starts = np.flatnonzero(np.concatenate(([True], months[1:] != months[:-1])))
    compounded: Floats = np.multiply.reduceat(1.0 + returns, starts) - 1.0
    return compounded


def months_below(sleeve: Sleeve, baseline: Sleeve) -> int:
    """Consecutive months, ending at the latest, the sleeve trails the
    baseline sleeve on shared days."""
    dates, mine, theirs = aligned(
        (sleeve.dates, sleeve.returns), (baseline.dates, baseline.returns)
    )
    if not len(dates):
        return 0
    below = monthly(dates, mine) < monthly(dates, theirs)
    above = np.flatnonzero(~below)
    return int(len(below) - (above[-1] + 1)) if len(above) else len(below)


def trading_days_after(last: int, today: date) -> int:
    """Weekdays after the last bar up to and including `today`."""
    first = np.datetime64(date_of(last) + timedelta(days=1), "D")
    end = np.datetime64(today + timedelta(days=1), "D")
    return int(np.busday_count(first, end)) if end > first else 0


class Measure(Model):
    value: float | None
    limit: float | None
    breach: bool


def measure(
    value: float | None, limit: float | None, *, reach: bool = False
) -> Measure:
    """Breach above `limit`, or at it with `reach`; a null never breaches."""
    over = (
        value is not None
        and limit is not None
        and (value >= limit if reach else value > limit)
    )
    return Measure(value=value, limit=limit, breach=over)


@dataclass(frozen=True, slots=True)
class RunFacts:
    """What the strategy's newest research run line contributes."""

    run_id: str
    max_drawdown: float
    half_spread: float | None


@dataclass(frozen=True, slots=True)
class Bounds:
    drawdown_multiple: float
    underperform_months: int
    tracking: float
    commission: float  # decimal, one way


@dataclass(frozen=True, slots=True, eq=False)
class Case:
    """One sleeve's evidence; `baseline` is None for the baseline itself or
    when the baseline holds no paper or live sleeve."""

    strategy: str
    status: Status
    fills: tuple[Fill, ...]
    sleeve: Sleeve | None
    model: Series | None
    baseline: Sleeve | None
    run: RunFacts | None
    stale_days: int
    notes: tuple[str, ...]


class LiveRow(Model):
    strategy: str
    status: Status
    run_id: str | None
    fills: int
    first_fill: str | None
    days: int
    realized_return: float | None
    model_return: float | None
    tracking: Measure
    slippage: Measure
    drawdown: Measure
    underperform: Measure
    stale: Measure
    notes: tuple[str, ...]

    def measures(self) -> dict[Watch, Measure]:
        return {
            Watch.DRAWDOWN: self.drawdown,
            Watch.UNDERPERFORM: self.underperform,
            Watch.SLIPPAGE: self.slippage,
            Watch.TRACKING: self.tracking,
            Watch.STALE: self.stale,
        }


def compounded(values: Floats) -> float | None:
    return float(np.prod(1.0 + values) - 1.0) if len(values) else None


def row_of(case: Case, bounds: Bounds) -> LiveRow:
    """Every metric of one sleeve against its bound; null where the evidence
    is absent, and a null never breaches."""
    sleeve, run = case.sleeve, case.run
    model = (
        since(case.model, int(sleeve.dates[0]))
        if case.model is not None and sleeve is not None
        else None
    )
    notes = list(case.notes)
    if sleeve is not None and sleeve.late:
        notes.append(f"{sleeve.late} fill(s) after the last bar left out")
    if sleeve is not None and sleeve.unpriced:
        notes.append(f"no bars for {', '.join(sleeve.unpriced)}: held at fill price")
    under = (
        months_below(sleeve, case.baseline)
        if sleeve is not None and case.baseline is not None
        else None
    )
    return LiveRow(
        strategy=case.strategy,
        status=case.status,
        run_id=run.run_id if run else None,
        fills=len(case.fills),
        first_fill=date_of(int(sleeve.dates[0])).isoformat() if sleeve else None,
        days=len(sleeve.dates) if sleeve else 0,
        realized_return=compounded(sleeve.returns) if sleeve else None,
        model_return=compounded(model[1]) if model is not None else None,
        tracking=measure(
            tracking_error(sleeve, model) if sleeve and model else None,
            bounds.tracking,
        ),
        slippage=measure(
            slippage(case.fills),
            run.half_spread + bounds.commission
            if run and run.half_spread is not None
            else None,
        ),
        drawdown=measure(
            max_drawdown(sleeve.returns) if sleeve else None,
            bounds.drawdown_multiple * run.max_drawdown if run else None,
        ),
        underperform=measure(
            None if under is None else float(under),
            float(bounds.underperform_months) if under is not None else None,
            reach=True,
        ),
        stale=measure(float(case.stale_days), float(STALE_DAYS)),
        notes=tuple(notes),
    )


class Breach(Model):
    kind: Watch
    strategy: str
    value: float
    limit: float


def breaches_of(rows: Sequence[LiveRow]) -> list[Breach]:
    return [
        Breach(kind=kind, strategy=row.strategy, value=m.value, limit=m.limit)
        for row in rows
        for kind, m in row.measures().items()
        if m.breach and m.value is not None and m.limit is not None
    ]


def recorded_on(row: Mapping[str, Any]) -> date | None:
    raw = row.get("as_of") or str(row.get("ts", ""))[:10]
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return None


def fresh(
    found: Sequence[Breach], incidents: Sequence[Mapping[str, Any]], today: date
) -> tuple[list[Breach], list[Breach]]:
    """(to append, already recorded): a breach of the same strategy and kind
    recorded in the 7 days up to `today` is not appended again."""
    recent = {
        (str(row.get("strategy")), str(row.get("kind")))
        for row in incidents
        if (day := recorded_on(row)) is not None and 0 <= (today - day).days < WEEK
    }
    new = [b for b in found if (b.strategy, b.kind.value) not in recent]
    return new, [b for b in found if (b.strategy, b.kind.value) in recent]


class LiveReport(Model):
    book: str
    as_of: str
    last_bar: str | None
    strategies: tuple[LiveRow, ...]
    breaches: tuple[Breach, ...]
    new: tuple[str, ...]
    repeated: int
    report: str
    next: str


def shown(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}g}"


def report_of(rows: Sequence[LiveRow], as_of: date, last_bar: str | None) -> str:
    """At most 20 lines: a header, one line per sleeve, one per breach."""
    lines = [f"check --live {as_of.isoformat()}; last bar {last_bar or 'none'}"]
    if not rows:
        lines.append("no paper or live strategy; nothing tracked")
    for row in rows:
        lines.append(
            f"{row.strategy} ({row.status.value}): {row.days} days, realized "
            f"{shown(row.realized_return)} vs model {shown(row.model_return)}, "
            f"TE {shown(row.tracking.value)}, slip {shown(row.slippage.value)}, "
            f"DD {shown(row.drawdown.value)}"
        )
        lines += [
            f"  breach {kind.value}: {shown(m.value)} over {shown(m.limit)}"
            for kind, m in row.measures().items()
            if m.breach
        ]
    if len(lines) > REPORT_LINES:
        cut = len(lines) - REPORT_LINES + 1
        lines = [*lines[: REPORT_LINES - 1], f"... {cut} more line(s) in strategies"]
    return "\n".join(lines)
