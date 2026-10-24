"""Tiingo daily prices: raw OHLCV, `adj_factor` = adjClose / close, and the
dividend and split columns as events dated on the bar."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from datetime import date

import numpy as np
from pydantic import TypeAdapter, ValidationError

from btm_corekit import (
    CommandError,
    Model,
    NonEmpty,
    Pace,
    Upstream,
    UpstreamError,
    get_bytes,
    signal,
)
from btm_finance.data.sources import client, not_found
from btm_finance.data.tables import (
    Bars,
    EventRows,
    Loaded,
    bars_from,
    concat_bars,
    concat_events,
    days,
    texts,
)

KEY_ENV = "TIINGO_API_KEY"
PRICES = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"
INTERVAL = 0.5
CAP = 64 * 1024 * 1024


class TiingoConfig(Model):
    """`symbols` replaces the universe."""

    symbols: tuple[NonEmpty, ...] | None = None


class Price(Upstream):
    date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    adjClose: float | None = None
    divCash: float = 0.0
    splitFactor: float = 1.0


PRICE_LIST = TypeAdapter(list[Price])


def nan(value: float | None) -> float:
    return np.nan if value is None else value


def parse(data: bytes, symbol: str, where: str) -> tuple[Bars, list[EventRows]]:
    """One ticker's price list as bars plus `dividend` and `split` events."""
    try:
        prices = PRICE_LIST.validate_python(json.loads(data))
    except (ValueError, ValidationError) as err:
        raise UpstreamError(
            f"{where} no longer answers as a price list: {err}"
        ) from err
    stamps = [price.date[:10] for price in prices]
    close = np.asarray([nan(p.close) for p in prices], dtype=np.float64)
    adjusted = np.asarray([nan(p.adjClose) for p in prices], dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = np.where(close > 0, adjusted / close, np.nan)
    bars = bars_from(
        [symbol] * len(prices),
        stamps,
        {
            "open": [nan(p.open) for p in prices],
            "high": [nan(p.high) for p in prices],
            "low": [nan(p.low) for p in prices],
            "close": close.tolist(),
            "volume": [nan(p.volume) for p in prices],
            "adj_factor": factor.tolist(),
        },
        [""] * len(prices),
        where,
    )
    on = days(stamps, where)
    dividend = np.asarray([p.divCash for p in prices], dtype=np.float64)
    split = np.asarray([p.splitFactor for p in prices], dtype=np.float64)
    flows: list[EventRows] = []
    for name, column, mask in (
        ("dividend", dividend, dividend != 0.0),
        ("split", split, split != 1.0),
    ):
        count = int(mask.sum())
        flows.append(
            EventRows(
                texts([symbol] * count),
                texts([name] * count),
                on[mask],
                on[mask],
                column[mask],
            )
        )
    return bars, flows


def token() -> str:
    """The key from the environment; never echoed."""
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise CommandError(f"set {KEY_ENV} to a Tiingo API token, then load again")
    return key


def fetch(symbols: Sequence[str], since: date, today: date) -> Loaded:
    headers = {"Authorization": f"Token {token()}"}
    params = {
        "startDate": since.isoformat(),
        "endDate": today.isoformat(),
        "format": "json",
    }
    pace = Pace(INTERVAL)
    bars: list[Bars] = []
    events: list[EventRows] = []
    for symbol in symbols:
        url = PRICES.format(ticker=symbol.lower().replace(".", "-"))
        pace.wait()
        try:
            payload = get_bytes(client(), url, CAP, params, headers)
        except CommandError as err:
            if isinstance(err, UpstreamError) or not not_found(err):
                raise
            signal(f"tiingo: no prices for {symbol}; skipped")
            continue
        found, flows = parse(payload, symbol, url)
        bars.append(found)
        events.extend(flows)
    return Loaded(concat_bars(bars), concat_events(events))
