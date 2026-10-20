"""Synthetic books for tests and the skill's reference scorecard: a seeded
one-factor-plus-sectors panel, delistings of both kinds, `_factors` events
that drive the returns, and point-in-time filings with a knowledge lag.

Never real data: every number comes from `numpy.random.default_rng(seed)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from btm_finance.cli import start
from btm_finance.data.panel import DelistKind
from btm_finance.data.raw import store
from btm_finance.data.tables import (
    Bars,
    Days,
    EventRows,
    Floats,
    Loaded,
    Source,
    date_of,
    texts,
)
from btm_finance.store import open_book

FIRST = date(2015, 1, 5)
SECTORS = ("energy", "finance", "health", "industrial", "tech", "utility")
EXCHANGES = ("nyse", "nasdaq", "amex")
FACTOR_FIELDS = ("mkt_rf", "smb", "hml", "rmw", "cma", "mom")
RF = 0.0001
FILING_EVERY = 63  # trading days between filings
FILING_LAG = 40  # calendar days from period end to filing
# (column, row share, kind): one performance delisting on nyse and on nasdaq,
# one merger, at fixed shares of the horizon.
DELISTED = (
    (6, 0.6, DelistKind.PERFORMANCE),
    (10, 0.7, DelistKind.PERFORMANCE),
    (14, 0.8, DelistKind.MERGER),
)
DIVIDEND = 0.02  # paid by names 0 and 1 at mid-horizon


@dataclass(frozen=True, slots=True, eq=False)
class Synthetic:
    """A universe CSV, bars, and events, as a `csv` load would store them;
    `returns` is the true daily total return, days by names."""

    universe: str
    bars: Bars
    events: EventRows
    dates: Days
    returns: Floats


def trading_days(count: int) -> Days:
    """The first `count` weekdays from `FIRST`, as days since 1970-01-01."""
    start = np.datetime64(FIRST, "D")
    span = start + np.arange(count * 7 // 5 + 7)
    weekdays = span[np.is_busday(span)][:count]
    return weekdays.astype(np.int64)


Row = tuple[str, str, int, int, float]


def factor_rows(dates: Days, factors: Floats) -> list[Row]:
    """`_factors` rows, known on their own date, plus a constant rf."""
    rows: list[Row] = []
    for row, stamp in enumerate(dates.tolist()):
        for field, value in zip(FACTOR_FIELDS, factors[row].tolist(), strict=True):
            rows.append(("_factors", field, stamp, stamp, value))
        rows.append(("_factors", "rf", stamp, stamp, RF))
    return rows


def event_table(rows: list[Row]) -> EventRows:
    return EventRows(
        texts([r[0] for r in rows]),
        texts([r[1] for r in rows]),
        np.asarray([r[2] for r in rows], dtype=np.int64),
        np.asarray([r[3] for r in rows], dtype=np.int64),
        np.asarray([r[4] for r in rows], dtype=np.float64),
    )


def bars_table(
    symbols: list[str], dates: Days, alive: NDArray[np.bool_], grids: dict[str, Floats]
) -> Bars:
    """One bar per live (date, name) cell; exchange left to the universe."""
    cell = np.nonzero(alive)
    return Bars.columns(
        {
            "symbol": texts([symbols[c] for c in cell[1].tolist()]),
            "date": dates[cell[0]],
            "open": grids["open"][cell],
            "high": grids["high"][cell],
            "low": grids["low"][cell],
            "close": grids["close"][cell],
            "volume": grids["volume"][cell],
            "adj_factor": grids["adj"][cell],
            "exchange": texts([""] * len(cell[0])),
        }
    )


def make_panel(
    seed: int,
    names: int = 60,
    days: int = 1200,
    *,
    structure: bool = True,
    alpha: float = 0.0,
) -> Synthetic:
    """`structure` False is pure noise: idiosyncratic returns plus rf, with
    factor events drawn but driving nothing. `alpha` is the cross-name std of
    a persistent daily drift no factor spans."""
    rng = np.random.default_rng(seed)
    dates = trading_days(days)
    symbols = [f"S{i:03d}" for i in range(names)]
    sector = np.arange(names) % len(SECTORS)
    factors = rng.normal(0.0, 0.004, (days, len(FACTOR_FIELDS)))
    factors[:, 0] = rng.normal(0.0003, 0.01, days)
    loadings = rng.normal(0.0, 0.5, (names, len(FACTOR_FIELDS)))
    loadings[:, 0] = rng.normal(1.0, 0.3, names)
    shocks = rng.normal(0.0, 0.004, (days, len(SECTORS)))
    noise = rng.normal(0.0, 0.015, (days, names))
    drift = rng.normal(0.0, alpha, names) if alpha > 0 else np.zeros(names)
    returns = RF + noise + drift
    if structure:
        returns += factors @ loadings.T + shocks[:, sector]
    returns = np.maximum(returns, -0.5)
    wealth = rng.uniform(20.0, 120.0, names) * np.cumprod(1.0 + returns, axis=0)
    paid = np.ones((days, names))
    paid[days // 2 :, :2] = 1.0 - DIVIDEND
    close = wealth * paid
    adj = np.where(paid < 1.0, 1.0, 1.0 - DIVIDEND)
    adj[:, 2:] = 1.0
    before = np.vstack((close[:1] / (1.0 + returns[:1]), close[:-1]))
    opened = (
        before
        * (1.0 + returns) ** 0.3
        * np.where(np.diff(paid, axis=0, prepend=1.0) < 0.0, 1.0 - DIVIDEND, 1.0)
    )
    wick = np.abs(rng.normal(0.0, 0.006, (2, days, names)))
    high = np.maximum(opened, close) * np.exp(wick[0])
    low = np.minimum(opened, close) * np.exp(-wick[1])
    level = 1e6 * rng.lognormal(0.0, 0.6, names)
    volume = level * rng.lognormal(0.0, 0.3, (days, names))
    alive = np.ones((days, names), dtype=bool)
    rows: list[Row] = []
    for column, share, kind in DELISTED:
        if column >= names:
            continue
        cut = int(days * share)
        alive[cut:, column] = False
        stamp = int(dates[cut])
        rows.append((symbols[column], "delisting", stamp, stamp, kind.code))
    rows += factor_rows(dates, factors)
    shares = 1e6 * rng.lognormal(3.0, 0.5, names)
    book_ratio = rng.uniform(0.3, 1.2, names)
    for column in range(names):
        for row in range(column % FILING_EVERY, days, FILING_EVERY):
            if not alive[row, column]:
                break
            period, known = int(dates[row]), int(dates[row]) + FILING_LAG
            equity = float(book_ratio[column] * shares[column] * close[row, column])
            symbol = symbols[column]
            rows.append((symbol, "StockholdersEquity", period, known, equity))
            rows.append(
                (symbol, "CommonStockSharesOutstanding", period, known, shares[column])
            )
    grids = {"open": opened, "high": high, "low": low, "close": close}
    bars = bars_table(symbols, dates, alive, grids | {"volume": volume, "adj": adj})
    universe = "symbol,sector,exchange\n" + "".join(
        f"{symbols[c]},{SECTORS[sector[c]]},{EXCHANGES[c % len(EXCHANGES)]}\n"
        for c in range(names)
    )
    return Synthetic(universe, bars, event_table(rows), dates, returns)


def make_book(  # noqa: PLR0913 - one synthetic book's whole recipe
    root: Path,
    seed: int,
    names: int = 60,
    days: int = 1200,
    *,
    structure: bool = True,
    alpha: float = 0.0,
) -> Synthetic:
    """`start` at `root` with the synthetic universe, whose held-out list is
    deterministic, and the panel stored as a csv load."""
    data = make_panel(seed, names, days, structure=structure, alpha=alpha)
    start(root, 10_000_000, data.universe)
    book = open_book(str(root))
    first = date_of(int(data.dates[0]))
    store(
        book,
        Source.CSV,
        Loaded(data.bars, data.events),
        since=first,
        today=date_of(int(data.dates[-1])),
    )
    return data
