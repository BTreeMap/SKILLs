"""SEC companyfacts: us-gaap values from 10-K and 10-Q filings; `end` is the
event time, `filed` the knowledge time, a restatement a later-filed row."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import numpy as np
from pydantic import ValidationError

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
from btm_finance.data.tables import EventRows, Loaded, concat_events, day_of, texts

TICKERS = "https://www.sec.gov/files/company_tickers.json"
FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
DEFAULT_TAGS = (
    "Revenues",
    "NetIncomeLoss",
    "StockholdersEquity",
    "Assets",
    "Liabilities",
    "CommonStockSharesOutstanding",
    "OperatingIncomeLoss",
    "NetCashProvidedByUsedInOperatingActivities",
)
FORMS = frozenset({"10-K", "10-Q"})
UNITS = ("USD", "shares", "USD/shares", "pure")
QUARTER_DAYS = (80, 100)
YEAR_DAYS = (350, 380)
ANNUAL = ":fy"
INTERVAL = 0.11  # SEC fair access: at most 10 requests per second
CAP = 256 * 1024 * 1024


class EdgarConfig(Model):
    """`tags` replaces the default us-gaap list; `symbols` the universe."""

    tags: tuple[NonEmpty, ...] = DEFAULT_TAGS
    symbols: tuple[NonEmpty, ...] | None = None


class Fact(Upstream):
    end: date
    val: float
    filed: date
    form: str
    start: date | None = None


def loads(data: bytes, where: str) -> Any:
    try:
        return json.loads(data)
    except ValueError as err:
        raise UpstreamError(f"non-JSON response from {where}") from err


def parse_tickers(data: bytes) -> dict[str, int]:
    """Ticker (upper case) to CIK from `company_tickers.json`."""
    body = loads(data, TICKERS)
    if not isinstance(body, dict):
        raise UpstreamError(f"{TICKERS} is no JSON object")
    found: dict[str, int] = {}
    for row in body.values():
        if not isinstance(row, dict):
            continue
        ticker, cik = row.get("ticker"), row.get("cik_str")
        if isinstance(ticker, str) and isinstance(cik, int):
            found.setdefault(ticker.upper(), cik)
    return found


def cik_of(tickers: Mapping[str, int], symbol: str) -> int | None:
    """SEC spells a share class with `-`: `BRK.B` is looked up as `BRK-B`."""
    key = symbol.upper()
    return tickers.get(key, tickers.get(key.replace(".", "-")))


def field_of(tag: str, fact: Fact) -> str | None:
    """Instants and one-quarter spans keep the tag; a fiscal year gets `:fy`;
    year-to-date spans are dropped."""
    if fact.start is None:
        return tag
    span = (fact.end - fact.start).days
    if QUARTER_DAYS[0] <= span <= QUARTER_DAYS[1]:
        return tag
    if YEAR_DAYS[0] <= span <= YEAR_DAYS[1]:
        return tag + ANNUAL
    return None


def chosen_unit(units: Mapping[str, Any]) -> str | None:
    return next((u for u in UNITS if u in units), next(iter(units), None))


def parse_facts(data: bytes, symbol: str, tags: Sequence[str], where: str) -> EventRows:
    """One company's rows for `tags`, 10-K and 10-Q only, one unit per tag."""
    body = loads(data, where)
    gaap = body.get("facts", {}).get("us-gaap", {}) if isinstance(body, dict) else {}
    fields: list[str] = []
    event: list[int] = []
    known: list[int] = []
    values: list[float] = []
    for tag in tags:
        units = gaap.get(tag, {}).get("units", {})
        unit = chosen_unit(units)
        if unit is None:
            continue
        for raw in units[unit]:
            try:
                fact = Fact.model_validate(raw)
            except ValidationError as err:
                raise UpstreamError(f"{where} {tag} changed shape: {err}") from err
            name = field_of(tag, fact) if fact.form in FORMS else None
            if name is None:
                continue
            fields.append(name)
            event.append(day_of(fact.end))
            known.append(day_of(fact.filed))
            values.append(fact.val)
    return EventRows(
        texts([symbol] * len(fields)),
        texts(fields),
        np.asarray(event, dtype=np.int64),
        np.asarray(known, dtype=np.int64),
        np.asarray(values, dtype=np.float64),
    )


def fetch(config: EdgarConfig, symbols: Sequence[str]) -> Loaded:
    pace = Pace(INTERVAL)
    pace.wait()
    tickers = parse_tickers(get_bytes(client(), TICKERS, CAP))
    parts: list[EventRows] = []
    for symbol in symbols:
        cik = cik_of(tickers, symbol)
        if cik is None:
            signal(f"edgar: no CIK for {symbol}; skipped")
            continue
        url = FACTS.format(cik=cik)
        pace.wait()
        try:
            payload = get_bytes(client(), url, CAP)
        except CommandError as err:
            if isinstance(err, UpstreamError) or not not_found(err):
                raise
            signal(f"edgar: no companyfacts for {symbol}; skipped")
            continue
        parts.append(parse_facts(payload, symbol, config.tags, url))
    return Loaded(None, concat_events(parts))
