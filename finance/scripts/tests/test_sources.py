"""Each source's parser on a hand-written payload in its documented format,
then the live routes under the `network` marker."""

from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest
from btm_finance.data.sources import Throttle, csv, edgar, french, tiingo
from btm_finance.data.tables import day_of

from btm_corekit import UpstreamError

FF5 = """This file was created using the CRSP database.
The Tbill return is the simple daily rate.

,Mkt-RF,SMB,HML,RMW,CMA,RF
19630701,   -0.67,    0.02,   -0.35,    0.03,    0.13,    0.012
19630702,    0.79,   -0.28,    0.28,   -0.08,   -0.21,    0.012

Copyright Kenneth R. French
"""
MOM = """This file was created using the CRSP database.
Missing data are indicated by -99.99 or -999.

,Mom
19630701,    0.56
19630702,  -99.99
"""


def zipped(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def test_french_reads_percent_as_decimal_and_skips_missing():
    rows = french.parse(french.unzipped(zipped("F.CSV", FF5), "ff5"), "ff5")
    assert len(rows) == 12
    assert set(rows.symbol.tolist()) == {"_factors"}
    first = (rows.field == "mkt_rf") & (rows.event_time == day_of(date(1963, 7, 1)))
    assert rows.value[first].tolist() == [pytest.approx(-0.0067)]
    assert np.array_equal(rows.event_time, rows.knowledge_time)
    mom = french.parse(MOM, "mom")
    assert mom.field.tolist() == ["mom"] and len(mom) == 1


def test_french_refuses_a_changed_layout():
    with pytest.raises(UpstreamError, match="unknown column"):
        french.parse(",Mkt-RF,Value\n19630701,1,2\n", "x")
    with pytest.raises(UpstreamError, match="no zip"):
        french.unzipped(b"not a zip", "x")


TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1067983, "ticker": "BRK-B", "title": "Berkshire"},
}


def fact(end, val, filed, form, start=None):
    row = {"end": end, "val": val, "accn": "0000", "fy": 2023, "fp": "Q1"}
    row |= {"form": form, "filed": filed, "frame": None}
    return row | ({"start": start} if start else {})


FACTS = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "label": "Revenues",
                "units": {
                    "USD": [
                        fact("2023-03-31", 100, "2023-05-01", "10-Q", "2023-01-01"),
                        fact("2023-03-31", 105, "2024-05-01", "10-Q", "2023-01-01"),
                        fact("2023-06-30", 210, "2023-08-01", "10-Q", "2023-01-01"),
                        fact("2023-12-31", 400, "2024-02-01", "10-K", "2023-01-01"),
                        fact("2023-03-31", 100, "2023-05-02", "8-K", "2023-01-01"),
                    ]
                },
            },
            "Assets": {"units": {"USD": [fact("2023-03-31", 9, "2023-05-01", "10-Q")]}},
        },
        "dei": {},
    },
}


def test_edgar_keeps_filings_with_filed_as_knowledge_time():
    tickers = edgar.parse_tickers(json.dumps(TICKERS).encode())
    assert edgar.cik_of(tickers, "brk.b") == 1067983
    assert edgar.cik_of(tickers, "MSFT") is None
    rows = edgar.parse_facts(
        json.dumps(FACTS).encode(), "AAPL", ("Revenues", "Assets", "Missing"), "x"
    )
    got = sorted(
        zip(
            rows.field.tolist(),
            rows.knowledge_time.tolist(),
            rows.value.tolist(),
            strict=True,
        )
    )
    filed = day_of(date(2023, 5, 1))
    assert got == [
        ("Assets", filed, 9.0),
        ("Revenues", filed, 100.0),
        ("Revenues", day_of(date(2024, 5, 1)), 105.0),
        ("Revenues:fy", day_of(date(2024, 2, 1)), 400.0),
    ]
    assert set(rows.event_time.tolist()) == {
        day_of(date(2023, 3, 31)),
        day_of(date(2023, 12, 31)),
    }


PRICES = [
    {
        "date": "2024-01-02T00:00:00.000Z",
        "open": 10,
        "high": 11,
        "low": 9,
        "close": 10,
        "volume": 1000,
        "adjClose": 5,
        "divCash": 0.0,
        "splitFactor": 1.0,
    },
    {
        "date": "2024-01-03T00:00:00.000Z",
        "open": 10,
        "high": 11,
        "low": 9,
        "close": 8,
        "volume": 900,
        "adjClose": 8,
        "divCash": 0.25,
        "splitFactor": 2.0,
    },
]


def test_tiingo_divides_adj_close_by_close_and_splits_flows_into_events():
    bars, flows = tiingo.parse(json.dumps(PRICES).encode(), "AAA", "x")
    assert bars.adj_factor.tolist() == [0.5, 1.0]
    assert bars.date.tolist() == [day_of(date(2024, 1, 2)), day_of(date(2024, 1, 3))]
    found = {f.field[0]: f.value.tolist() for f in flows if len(f)}
    assert found == {"dividend": [0.25], "split": [2.0]}
    with pytest.raises(UpstreamError):
        tiingo.parse(b'{"detail": "Not found."}', "AAA", "x")


def test_tiingo_refuses_without_its_key(monkeypatch):
    monkeypatch.delenv(tiingo.KEY_ENV, raising=False)
    with pytest.raises(Exception, match=tiingo.KEY_ENV):
        tiingo.token()


def test_csv_config_needs_a_file_and_maps_columns():
    with pytest.raises(ValueError, match="bars CSV"):
        csv.CsvConfig()
    rows = csv.parse_bars(
        b"Sym,Day,Last\nA,2024-01-02,3\n",
        {"symbol": "Sym", "date": "Day", "close": "Last"},
        "x",
    )
    assert rows.close.tolist() == [3.0] and np.isnan(rows.open[0])
    assert rows.adj_factor.tolist() == [1.0]


def test_throttle_waits_out_its_interval():
    now = [0.0]
    slept: list[float] = []
    throttle = Throttle(0.1, clock=lambda: now[0], sleep=slept.append)
    throttle.wait()
    now[0] = 0.03
    throttle.wait()
    assert slept == [pytest.approx(0.07)]


@pytest.mark.network
def test_live_french_answers_in_the_parsed_shape():
    rows = french.fetch(french.FrenchConfig()).events
    assert rows is not None
    assert {"mkt_rf", "mom", "rf"} <= set(rows.field.tolist())


@pytest.mark.network
def test_live_edgar_answers_in_the_parsed_shape():
    rows = edgar.fetch(edgar.EdgarConfig(), ["AAPL"]).events
    assert rows is not None and len(rows) > 0
    assert np.all(rows.knowledge_time >= rows.event_time)


@pytest.mark.network
def test_live_tiingo_answers_in_the_parsed_shape():
    if not os.environ.get(tiingo.KEY_ENV):
        pytest.skip(f"{tiingo.KEY_ENV} is not set; the tiingo route was not reached")
    today = datetime.now(UTC).date()
    loaded = tiingo.fetch(["AAPL"], today - timedelta(days=30), today)
    assert loaded.bars is not None and len(loaded.bars) > 0
