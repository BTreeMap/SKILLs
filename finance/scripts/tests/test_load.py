"""`load` through the raw store: the csv round trip, immutable numbered files,
and the integrity check that halts on a changed or missing file."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
from btm_finance.data.assemble import assemble
from btm_finance.data.panel import DelistKind
from btm_finance.data.tables import day_of
from btm_finance.store import open_book

from btm_corekit import dispatch

BARS = """Ticker,date,open,high,low,close,volume,exchange
AAA,2024-01-02,10,11,9,10.5,1000,NASDAQ
AAA,2024-01-03,10.5,12,10,11.5,1200,NASDAQ
BBB,2024-01-02,20,21,19,20.5,500,NYSE
"""
EVENTS = """symbol,field,event_time,knowledge_time,value
BBB,delisting,2024-01-03,2024-01-04,performance
AAA,revenue,2023-12-31,2024-02-15,100
"""


def config(tmp_path: Path, name: str, **files: str) -> Path:
    paths = {}
    for kind, body in files.items():
        path = tmp_path / f"{name}.{kind}.csv"
        path.write_text(body)
        paths[kind] = str(path)
    target = tmp_path / f"{name}.json"
    mapped = any("Ticker" in body for body in files.values())
    columns = {"columns": {"symbol": "Ticker"}} if mapped else {}
    target.write_text(json.dumps({**paths, **columns}))
    return target


def load(run, book, cfg, since="2024-01-01"):
    return run(["load", str(book), "csv", "--since", since, "--config:file", str(cfg)])


def incidents(book: Path) -> list[dict]:
    path = book / "ledger" / "incidents.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def test_csv_round_trips_through_the_store_and_assembly(tmp_path, book, run):
    cfg = config(tmp_path, "one", bars=BARS, events=EVENTS)
    code, receipt, err = load(run, book, cfg)
    assert code == 0, err
    assert receipt["rows"] == {"bars": 3, "events": 2}
    paths = [f["path"] for f in receipt["files"]]
    assert paths == [f"data/raw/csv/{Path(p).name}" for p in paths] and all(
        (book / p).is_file() for p in paths
    )
    manifest = json.loads((book / "data" / "manifest.json").read_text())
    assert [f["sha256"] for f in manifest["files"]] == [
        f["sha256"] for f in receipt["files"]
    ]

    panel, events = assemble(open_book(str(book)))
    assert panel.names == ("AAA", "BBB")
    assert panel.close[:, 0].tolist() == [10.5, 11.5]
    assert np.isnan(panel.close[1, 1])
    assert [e.value for e in panel.exchange] == ["nasdaq", "nyse"]
    assert panel.delisting(1).kind is DelistKind.PERFORMANCE
    assert events.latest("AAA", "revenue", day_of_iso("2024-02-14")) is None
    assert events.latest("AAA", "revenue", day_of_iso("2024-02-15"))[1] == 100.0


def day_of_iso(text: str) -> int:
    return day_of(date.fromisoformat(text))


def test_a_same_day_reload_writes_a_numbered_sibling_and_wins(tmp_path, book, run):
    load(run, book, config(tmp_path, "one", bars=BARS))
    fix = "symbol,date,close\nAAA,2024-01-03,99\n"
    code, receipt, err = load(run, book, config(tmp_path, "two", bars=fix))
    assert code == 0, err
    [stored] = receipt["files"]
    assert Path(stored["path"]).name.split(".")[0].endswith("-2")
    panel, _ = assemble(open_book(str(book)))
    assert panel.close[:, 0].tolist() == [10.5, 99.0]
    assert len(json.loads((book / "data" / "manifest.json").read_text())["files"]) == 2


def test_since_defaults_to_the_day_after_the_last_covered_date(tmp_path, book, run):
    load(run, book, config(tmp_path, "one", bars=BARS))
    cfg = config(tmp_path, "two", bars=BARS)
    code, receipt, err = run(["load", str(book), "csv", "--config:file", str(cfg)])
    assert code == 0
    assert receipt["since"] == "2024-01-04"
    assert receipt["files"] == []
    assert "3 row(s) before 2024-01-04 dropped" in err


def test_a_one_byte_corruption_halts_load_and_assembly(tmp_path, book, run):
    _, receipt, _ = load(run, book, config(tmp_path, "one", bars=BARS))
    target = book / receipt["files"][0]["path"]
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0x01
    target.write_bytes(bytes(data))

    code, _, err = load(
        run, book, config(tmp_path, "two", bars=BARS), since="2024-01-01"
    )
    assert code == 1
    assert receipt["files"][0]["path"] in err
    [line] = incidents(book)
    assert line["file"] == receipt["files"][0]["path"]
    assert line["found"] != line["expected"]
    assert target.read_bytes() == bytes(data)

    assert dispatch(lambda: len(assemble(open_book(str(book))))) == 1
    assert len(incidents(book)) == 2

    code, view, _ = run(["check", str(book)])
    assert code == 0 and view["chain"]["breaks"] == 0
    assert view["incidents"]["logged"][-1]["kind"] == "integrity"


def test_a_listed_file_missing_on_disk_is_an_incident(tmp_path, book, run):
    _, receipt, _ = load(run, book, config(tmp_path, "one", bars=BARS))
    (book / receipt["files"][0]["path"]).unlink()
    code, _, err = load(run, book, config(tmp_path, "two", bars=BARS))
    assert code == 1 and "missing on disk" in err
    [line] = incidents(book)
    assert line["found"] is None


def test_csv_refuses_without_config_and_on_a_bad_row(tmp_path, book, run):
    code, _, err = run(["load", str(book), "csv"])
    assert code == 1 and "--config:file" in err
    bad = "symbol,date,close\nAAA,2024-13-01,1\n"
    code, _, err = load(run, book, config(tmp_path, "bad", bars=bad))
    assert code == 1 and "row 1" in err
    odd = "symbol,field,event_time,knowledge_time,value\n"
    odd += "A,delisting,2024-01-02,2024-01-02,7\n"
    code, _, err = load(run, book, config(tmp_path, "odd", events=odd))
    assert code == 1 and "line 2" in err
    assert not (book / "data" / "manifest.json").exists()
