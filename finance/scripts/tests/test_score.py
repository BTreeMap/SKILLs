"""`score` and `check <strategy>` as bridge code: the run line and its returns
file, the family trial count, the held-out split, per-agent run files, and the
standing derived from the ledger."""

from __future__ import annotations

import json
import threading
import time

import numpy as np
from btm_finance.cli import scoped
from btm_finance.data import raw
from btm_finance.data.raw import data_snapshot, read_manifest
from btm_finance.store import open_book

SPEC_KEYS = {
    "run_id",
    "hypothesis_id",
    "family_id",
    "strategy",
    "data_snapshot",
    "code_hash",
    "config",
    "scorecard",
    "engine",
    "tolerance",
    "held_out",
    "exclusions",
    "refused",
    "params",
}


def run_lines(book, name="runs.jsonl"):
    return [
        json.loads(line) for line in (book / "ledger" / name).read_text().splitlines()
    ]


def test_start_registers_the_baseline_hypothesis(book, run):
    (line,) = [json.loads(x) for x in (book / "ledger" / "hypotheses.jsonl").open()]
    assert (line["strategy"], line["family_id"]) == ("baseline", "baseline")
    assert line["capacity_class"] == "crowded"
    config = json.loads((book / "strategies" / "baseline" / "config.json").read_text())
    assert (config["rebalance"], config["holding_days"]) == ("annual", 252)


def test_score_appends_the_run_line_and_lists_its_returns(synthetic, run):
    book = synthetic(seed=7)
    before = data_snapshot(read_manifest(open_book(str(book))))
    code, document, err = run(["score", str(book), "baseline"])
    assert code == 0, err
    (line,) = run_lines(book)
    assert set(line) >= SPEC_KEYS
    assert line["run_id"] == line["id"] == document["run_id"]
    assert line["data_snapshot"] == before
    assert line["engine"]["btm_finance"] == "0.1.0"
    listed = {e.path: e for e in read_manifest(open_book(str(book))).files}
    assert listed[line["returns"]].rows == line["span"]["periods"]
    assert line["scorecard"]["trials"] == 1
    code, again, _ = run(["score", str(book), "baseline"])
    assert again["scorecard"]["trials"] == 2
    second = run_lines(book)[1]
    assert second["data_snapshot"] == before  # returns files never move it
    assert second["code_hash"] == line["code_hash"]
    assert (line["peers"], second["peers"]) == ([], [line["run_id"]])


def test_held_out_scores_only_the_complement(synthetic, run):
    book = synthetic(seed=7)
    names = [f"S{i:03d}" for i in range(60)]
    research = scoped(open_book(str(book)), names, held_out=False)
    hidden = scoped(open_book(str(book)), names, held_out=True)
    assert research.isdisjoint(hidden)
    assert research | hidden == set(names)
    assert 10 <= len(hidden) <= 20  # a quarter per sector, rounded half up
    code, _, err = run(["score", str(book), "baseline", "--held-out"])
    assert code == 0, err
    assert run_lines(book)[0]["held_out"] is True
    view = run(["check", str(book), "baseline"])[1]
    assert view["run_id"] is None  # standing reads research runs only


def test_an_agent_writes_its_own_run_file(synthetic, run):
    book = synthetic(seed=7)
    code, document, _ = run(["score", str(book), "baseline", "--agent", "a1"])
    assert code == 0
    assert run_lines(book, "runs/a1.jsonl")[0]["agent"] == "a1"
    assert not (book / "ledger" / "runs.jsonl").exists()
    view = run(["check", str(book), document["run_id"]])[1]
    assert view["run_id"] == document["run_id"]


def test_standing_names_each_blocker_with_value_and_limit(synthetic, run):
    book = synthetic(seed=7)
    code, document, _ = run(["score", str(book), "baseline"])
    view = run(["check", str(book), "baseline"])[1]
    assert view["standing"] in {"blocked", "discard"}
    assert "no critique" in view["blockers"]
    assert (
        "crowded: capacity_class crowded needs an override decision" in view["blockers"]
    )
    critique = {
        "kw": ["base", "read"],
        "run_id": document["run_id"],
        "blockers": ["survivorship in the universe file"],
        "concerns": [],
        "by": "test",
    }
    code, _, err = run(
        ["record", str(book), "--batch:stdin"], json.dumps({"critiques": [critique]})
    )
    assert code == 0, err
    view = run(["check", str(book), "baseline"])[1]
    assert "critique: survivorship in the universe file" in view["blockers"]
    assert "no critique" not in view["blockers"]


def test_interleaved_manifest_writers_keep_every_entry(synthetic, monkeypatch):
    """Each writer stalls inside its read-modify-write; the lock serializes
    them, so no entry is lost."""
    book = open_book(str(synthetic(seed=7)))
    slow = raw.write_atomic

    def stall(path, text):
        time.sleep(0.02)
        slow(path, text)

    monkeypatch.setattr(raw, "write_atomic", stall)
    dates = np.arange(19000, 19005, dtype=np.int64)
    series = np.zeros(5)

    def writer(tag):
        for k in range(5):
            raw.write_returns(book, f"{tag}-{k}", dates=dates, gross=series, net=series)

    threads = [threading.Thread(target=writer, args=(tag,)) for tag in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    paths = {e.path for e in read_manifest(book).files}
    assert {raw.returns_path(f"{t}-{k}") for t in "ab" for k in range(5)} <= paths
