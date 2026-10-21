"""Regime records: the gate, the run stamp, staleness, the falsifier join,
and the advisory stream fields `check <strategy>` adds."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pytest
from btm_finance.data.tables import day_of
from btm_finance.regimes import Dated, regime_record, regime_stamp
from btm_finance.streams import effective_streams, pairs_of


def batch(run, book, payload):
    return run(["record", str(book), "--batch:stdin"], json.dumps(payload))


def regime(kw: list[str], **overrides) -> dict:
    entry = {
        "kw": kw,
        "as_of": "2017-06-30",
        "short_cycle": "mid-expansion",
        "long_cycle": "bubble",
        "bubble_count": {"count": 2, "evidence": ["prices high", "new entrants"]},
        "policy_mix": ["printing"],
        "other_forces": {
            "internal_order": "wide wealth gap",
            "external_order": "trade tension",
            "nature": "none noted",
            "technology": "fast invention",
        },
        "observables": {
            "real_yield": {
                "value": "-0.5%",
                "as_of": "2017-06-30",
                "source": "https://example.org/real-yield",
            }
        },
        "confidence": 0.6,
    }
    return entry | overrides


def test_the_regimes_gate_refuses_each_bad_field_by_location(book, run):
    payload = {
        "regimes": [
            regime(["bad", "date"], as_of="mid 2017"),
            regime(["too", "sure"], confidence=1.5),
            regime(["ghost", "fix"], supersedes="no-such-regime"),
            regime(["odd", "chain"], falsified=["made-up-chain"]),
        ]
    }
    code, verdict, _ = batch(run, book, payload)
    assert code == 1
    where = [problem["where"] for problem in verdict["rejected"]]
    assert where == [
        "regimes[0].as_of",
        "regimes[1].confidence",
        "regimes[2].supersedes",
        "regimes[3].falsified[0]",
    ]
    assert not (book / "ledger" / "regimes.jsonl").exists()


def test_free_text_outside_the_four_checked_fields_lands(book, run):
    entry = regime(
        ["free", "text"],
        short_cycle="boom, by the operator's read",
        policy_mix="none yet",
        bubble_count="not counted",
        other_forces=None,
    )
    code, receipt, err = batch(run, book, {"regimes": [entry]})
    assert code == 0, err
    assert receipt["accepted"] == {"regime": 1}
    line = json.loads((book / "ledger" / "regimes.jsonl").read_text())
    assert line["short_cycle"] == "boom, by the operator's read"


def test_a_correction_must_supersede_the_live_line(book, run):
    code, receipt, err = batch(run, book, {"regimes": [regime(["first", "read"])]})
    assert code == 0, err
    first = receipt["new"]["regimes"]["first-read"]
    fix = regime(["second", "read"], supersedes=first)
    assert batch(run, book, {"regimes": [fix]})[0] == 0
    again = regime(["third", "read"], supersedes=first)
    code, verdict, _ = batch(run, book, {"regimes": [again]})
    assert code == 1
    assert [p["where"] for p in verdict["rejected"]] == ["regimes[0].supersedes"]


def test_a_regime_lands_and_a_correction_supersedes_it(book, run):
    code, receipt, err = batch(run, book, {"regimes": [regime(["first", "read"])]})
    assert code == 0, err
    first = receipt["new"]["regimes"]["first-read"]
    fix = regime(["second", "read"], supersedes=first, as_of="2017-07-31")
    code, receipt, err = batch(run, book, {"regimes": [fix]})
    assert code == 0, err
    code, view, _ = run(["check", str(book)])
    assert view["regime"]["id"] == receipt["new"]["regimes"]["second-read"]
    assert view["regime"]["as_of"] == "2017-07-31"
    assert view["regime"]["stale"] is True


def test_a_short_evidence_list_is_advisory_only(book, run):
    entry = regime(["thin", "list"], bubble_count={"count": 3, "evidence": ["one"]})
    code, _, err = batch(run, book, {"regimes": [entry]})
    assert code == 0, err
    assert "give one per item present" in err


def dated(name: str, day: str, *falsified: str) -> Dated:
    return Dated(id=name, as_of=date.fromisoformat(day), falsified=falsified)


def test_the_stamp_counts_window_days_per_regime_span():
    first = day_of(date(2020, 1, 1))
    window = np.arange(first, first + 10, dtype=np.int64)  # Jan 1 to Jan 10
    records = [
        dated("r1", "2020-01-03"),
        dated("r2", "2020-01-07"),
        dated("r3", "2020-02-01"),  # after the window: spans none of it
    ]
    spanned, days = regime_stamp(window, records)
    assert spanned == ("r1", "r2")
    assert days == {"none": 2, "r1": 4, "r2": 4}
    spanned, days = regime_stamp(window, [dated("r0", "2019-12-01"), *records])
    assert spanned == ("r0", "r1", "r2")
    assert days == {"r0": 2, "r1": 4, "r2": 4}
    assert regime_stamp(window, []) == ((), {"none": 10})


def test_the_regime_record_is_stale_past_the_limit():
    records = [dated("old", "2020-01-01"), dated("new", "2020-03-01")]
    on_day = regime_record(records, date(2020, 5, 30), 90)  # 90 days after
    assert on_day is not None and (on_day.id, on_day.stale) == ("new", False)
    late = regime_record(records, date(2020, 5, 31), 90)  # 91 days after
    assert late is not None and late.stale is True
    assert regime_record([], date(2020, 5, 31), 90) is None


def event_hypothesis(make_hypothesis, kw: list[str], chain: str) -> dict:
    return make_hypothesis(
        kw,
        family_id="event-drift",
        chain=chain,
        expectation_source="consensus estimate the day before",
        discounted="price holds consensus; we disagree on speed",
        confidence=0.4,
    )


def test_a_fired_falsifier_warns_exactly_the_hypotheses_citing_it(
    book, run, families, make_hypothesis
):
    families(book, **{"event-drift": {"trials": 8, "event": True}})
    hypotheses = [
        event_hypothesis(make_hypothesis, ["drift", "one"], "expectation-vs-outcome"),
        event_hypothesis(make_hypothesis, ["drift", "two"], "spin-off-supply"),
        event_hypothesis(make_hypothesis, ["drift", "three"], "expectation-vs-outcome"),
    ]
    code, receipt, err = batch(run, book, {"hypotheses": hypotheses})
    assert code == 0, err
    made = receipt["new"]["hypotheses"]
    reject = {
        "kw": ["drop", "three"],
        "subject": made["drift-three"],
        "action": "reject",
        "reason": "operator dropped it",
    }
    fired = regime(["chain", "broke"], falsified=["expectation-vs-outcome"])
    code, _, err = batch(run, book, {"decisions": [reject], "regimes": [fired]})
    assert code == 0, err
    code, view, err = run(["check", str(book)])
    warned = [w["hypothesis"] for w in view["warnings"] if "chain" in w]
    assert warned == [made["drift-one"]]
    assert "write an objection pad entry" in err


def test_a_run_is_stamped_and_check_shows_its_concentration(synthetic, run):
    book = synthetic(seed=7)
    payload = {
        "regimes": [
            regime(["mid", "cycle"], as_of="2017-06-30"),
            regime(["late", "cycle"], as_of="2018-06-29"),
        ]
    }
    code, receipt, err = batch(run, book, payload)
    assert code == 0, err
    ids = receipt["new"]["regimes"]
    code, document, err = run(["measure", str(book), "baseline"])
    assert code == 0, err
    line = json.loads((book / "ledger" / "runs.jsonl").read_text().splitlines()[-1])
    assert line["regimes"] == [ids["mid-cycle"], ids["late-cycle"]]
    assert list(line["regime_days"]) == ["none", ids["mid-cycle"], ids["late-cycle"]]
    assert sum(line["regime_days"].values()) == line["span"]["periods"]
    assert document["regime_days"] == line["regime_days"]
    code, view, err = run(["check", str(book), "baseline"])
    assert code == 0, err
    shares = view["regime_concentration"]
    assert sum(shares.values()) == pytest.approx(1.0)
    assert view["correlation"] == {}
    assert view["effective_streams"] == 1.0
    assert "adds a trial, not a stream" in err


def series(seed: int, size: int = 500) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    return np.arange(size, dtype=np.int64), rng.normal(0.0, 0.01, size)


def test_a_copy_is_one_stream_and_independent_sleeves_are_two():
    original = series(1)
    copied = {"a": original, "b": (original[0].copy(), original[1].copy())}
    pairs = pairs_of(copied)
    found = effective_streams(["a", "b"], pairs)
    assert found is not None and abs(found - 1.0) < 0.05
    independent = pairs_of({"a": series(1), "b": series(2)})
    found = effective_streams(["a", "b"], independent)
    assert found is not None and found > 1.5
