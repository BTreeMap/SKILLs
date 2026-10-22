"""`measure` and `check <strategy>` as bridge code: the run line and its returns
file, the family trial count, the held-out split, per-agent run files, and the
standing derived from the ledger."""

from __future__ import annotations

import hashlib
import json
import threading
import time

import btm_finance
import numpy as np
import pytest
from btm_finance.cli import scoped
from btm_finance.data import raw
from btm_finance.data.raw import data_snapshot, read_manifest
from btm_finance.engine import purged_folds, sharpe
from btm_finance.measuring import post_cutoff
from btm_finance.store import open_book

SPEC_KEYS = {
    "run_id",
    "hypothesis_id",
    "family_id",
    "strategy",
    "data_snapshot",
    "code_hash",
    "code_files",
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
    assert "capacity_class" not in line
    config = json.loads((book / "strategies" / "baseline" / "config.json").read_text())
    assert (config["rebalance"], config["holding_days"]) == ("annual", 252)


def test_measure_appends_the_run_line_and_lists_its_returns(synthetic, run):
    book = synthetic(seed=7)
    before = data_snapshot(read_manifest(open_book(str(book))))
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    (line,) = run_lines(book)
    assert set(line) >= SPEC_KEYS
    assert line["run_id"] == line["id"] == document["run_id"]
    assert line["data_snapshot"] == before
    assert line["engine"] == btm_finance.__version__
    assert list(line["code_files"]) == [
        "strategies/baseline/config.json",
        "strategies/baseline/signal.py",
    ]
    assert all(len(digest) == 64 for digest in line["code_files"].values())
    assert len(line["code_hash"]) == 64
    listed = {e.path: e for e in read_manifest(open_book(str(book))).files}
    assert listed[line["returns"]].rows == line["span"]["periods"]
    assert line["scorecard"]["trials"] == 1
    code, again, _ = run(["measure", str(book), "baseline"])
    assert again["scorecard"]["trials"] == 2
    second = run_lines(book)[1]
    assert second["data_snapshot"] == before  # returns files never move it
    assert second["code_hash"] == line["code_hash"]
    assert (line["peers"], second["peers"]) == ([], [line["run_id"]])


def test_code_hash_moves_with_meaning_not_with_comments(synthetic, run):
    book = synthetic(seed=7)
    assert run(["measure", str(book), "baseline"])[0] == 0
    signal = book / "strategies" / "baseline" / "signal.py"
    signal.write_text(signal.read_text() + "\n# a comment moves nothing\n")
    assert run(["measure", str(book), "baseline"])[0] == 0
    signal.write_text(signal.read_text() + "\nEXTRA = 1\n")
    assert run(["measure", str(book), "baseline", "--reason", "third"])[0] == 0
    first, second, third = run_lines(book)
    assert first["code_hash"] == second["code_hash"] != third["code_hash"]
    path = "strategies/baseline/signal.py"
    assert first["code_files"][path] != third["code_files"][path]
    config = "strategies/baseline/config.json"
    assert first["code_files"][config] == third["code_files"][config]
    canonical = json.dumps(
        json.loads((book / config).read_text()), sort_keys=True, separators=(",", ":")
    )
    assert third["code_files"][config] == hashlib.sha256(canonical.encode()).hexdigest()


def test_held_out_measures_only_the_complement(synthetic, run):
    book = synthetic(seed=7)
    names = [f"S{i:03d}" for i in range(60)]
    research = scoped(open_book(str(book)), names, held_out=False)
    hidden = scoped(open_book(str(book)), names, held_out=True)
    assert research.isdisjoint(hidden)
    assert research | hidden == set(names)
    assert 10 <= len(hidden) <= 20  # a quarter per sector, rounded half up
    code, _, err = run(["measure", str(book), "baseline", "--held-out"])
    assert code == 0, err
    assert run_lines(book)[0]["held_out"] is True
    view = run(["check", str(book), "baseline"])[1]
    assert view["run_id"] is None  # standing reads research runs only


def test_an_agent_writes_its_own_run_file(synthetic, run):
    book = synthetic(seed=7)
    code, document, _ = run(["measure", str(book), "baseline", "--agent", "a1"])
    assert code == 0
    assert run_lines(book, "runs/a1.jsonl")[0]["agent"] == "a1"
    assert (book / "ledger" / "runs.jsonl").read_text() == ""
    view = run(["check", str(book), document["run_id"]])[1]
    assert view["run_id"] == document["run_id"]


def test_standing_names_each_blocker_with_value_and_limit(synthetic, run):
    book = synthetic(seed=7)
    code, document, _ = run(["measure", str(book), "baseline"])
    view = run(["check", str(book), "baseline"])[1]
    assert view["standing"] in {"blocked", "discard"}
    assert "no critique" in view["blockers"]
    assert not [b for b in view["blockers"] if b.startswith("crowded")]
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


def test_post_cutoff_joins_the_folds_starting_after_the_cutoff():
    # Five folds of 20 days on days 0..99: first 60 days gain, last 40 lose.
    rng = np.random.default_rng(2)
    excess = np.concatenate((rng.normal(0.002, 0.01, 60), rng.normal(-0.002, 0.01, 40)))
    dates = np.arange(100, dtype=np.int64)
    tests = [test for _, test in purged_folds(100, folds=5, embargo=0)]
    found, why = post_cutoff(dates, excess, tests, 59)
    assert (found, why) == (pytest.approx(sharpe(excess[60:])), None)
    assert found is not None and found < 0.0
    later, _ = post_cutoff(dates, excess, tests, 60)  # strictly after
    assert later == pytest.approx(sharpe(excess[80:]))
    assert post_cutoff(dates, excess, tests, None) == (
        None,
        "limits.model_cutoff is null",
    )
    assert post_cutoff(dates, excess, tests, 80) == (
        None,
        "no test fold starts after 1970-03-22",
    )


def test_measure_reports_post_cutoff_from_limits(synthetic, run):
    book = synthetic(seed=7)
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert document["scorecard"]["walk_forward"]["post_cutoff"] is None
    assert document["reasons"]["post_cutoff"] == "limits.model_cutoff is null"
    span = run_lines(book)[0]["span"]
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    limits["model_cutoff"] = span["start"]
    path.write_text(json.dumps(limits))
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    folds = document["scorecard"]["walk_forward"]
    assert isinstance(folds["post_cutoff"], float)
    assert "post_cutoff" not in document["reasons"]


def edit_limits(book, change):
    path = book / "limits.json"
    limits = json.loads(path.read_text())
    change(limits)
    path.write_text(json.dumps(limits))


GATES = {
    "trials_per_day": lambda limits: limits.update(trials_per_day=0),
    "holding": lambda limits: limits.update(min_holding_days=253),
}


@pytest.mark.parametrize("gate", sorted(GATES))
def test_reason_runs_past_each_policy_gate_and_is_stamped(synthetic, run, gate):
    book = synthetic(seed=7)
    edit_limits(book, GATES[gate])
    code, document, err = run(["measure", str(book), "baseline"])
    assert (code, document) == (1, None)
    assert "refused before running" in err and "--reason" in err
    assert (book / "ledger" / "runs.jsonl").read_text() == ""
    code, _, err = run(["measure", str(book), "baseline", "--reason", "gate test"])
    assert "override_reason" in err
    (line,) = run_lines(book)
    assert line["override_reason"] == "gate test"
    view = run(["check", str(book), "baseline"])[1]
    assert view["scorecard"]["override_reason"] == "gate test"


def test_reason_with_no_gate_to_pass_stamps_nothing(synthetic, run):
    book = synthetic(seed=7)
    code, _, err = run(["measure", str(book), "baseline", "--reason", "unneeded"])
    assert code == 0, err
    (line,) = run_lines(book)
    assert (line["override_reason"], line["universe"]) == (None, "static")


def test_commission_map_charges_by_exchange(synthetic, run):
    book = synthetic(seed=7)
    code, flat, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    edit_limits(book, lambda limits: limits.update(commission_bps={"other": 1.0}))
    code, same, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert same["scorecard"]["sharpe_net"] == flat["scorecard"]["sharpe_net"]
    dear = {"nyse": 1.0, "other": 200.0}
    edit_limits(book, lambda limits: limits.update(commission_bps=dear))
    code, mixed, err = run(["measure", str(book), "baseline"])
    assert code in {0, 1}, err
    assert mixed["scorecard"]["sharpe_net"] < flat["scorecard"]["sharpe_net"]
    assert mixed["scorecard"]["sharpe_gross"] == flat["scorecard"]["sharpe_gross"]


def test_membership_events_mark_the_run_line(synthetic, run, tmp_path):
    book = synthetic(seed=7)
    rows = "symbol,field,event_time,knowledge_time,value\n" + "".join(
        f"S{i:03d},member_x,2016-01-04,2015-12-21,1\n" for i in range(60)
    )
    path = tmp_path / "members.csv"
    path.write_text(rows)
    config = json.dumps({"events": str(path)})
    load = ["load", str(book), "csv", "--since", "2015-01-01", "--config:stdin"]
    code, _, err = run(load, config)
    assert code == 0, err
    code, _, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    assert run_lines(book)[0]["universe"] == "membership"
