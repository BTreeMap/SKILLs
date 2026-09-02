"""The decoder: a ledger row exists only inside the vocabulary and its refs."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError
from btm_peer_review.constants import Bank, Kind
from btm_peer_review.ledger import replay
from btm_peer_review.state import Missing, Quoted

CLAIM = {"e": "claim", "id": "c1", "verbatim": "v", "page": 1}


def objection(**fields):
    base = {
        "e": "objection",
        "id": "o1",
        "kind": "control",
        "severity": "major",
        "text": "t",
        "anchors": ["q"],
    }
    return [CLAIM, {**base, **fields}]


class TestDecoder:
    def test_a_well_formed_log_replays_into_typed_records(self):
        ledger = replay(
            [
                *objection(claim="c1"),
                {"e": "walk", "bank": "design", "note": "n"},
                {"e": "withdraw", "objection": "o1", "reason": "r"},
            ]
        )
        record = ledger.objections["o1"]
        assert record.kind is Kind.CONTROL and record.kind.bank is Bank.DESIGN
        assert record.evidence == Quoted(("q",))
        assert ledger.walks == {Bank.DESIGN: "n"} and ledger.withdrawn == {"o1": "r"}

    def test_missing_is_the_other_evidence_variant(self):
        ledger = replay(objection(anchors=[], missing="error bars"))
        assert ledger.objections["o1"].evidence == Missing("error bars")

    @pytest.mark.parametrize(
        ("fields", "message"),
        [
            ({"kind": "vibes"}, "vocabulary"),
            ({"severity": "huge"}, "vocabulary"),
            ({"claim": "c9"}, "unknown claim"),
            ({"anchors": [], "missing": None}, "lacks evidence"),
            ({"missing": "x"}, "both anchors and missing"),
            ({"prior": ["doi:10.1/a"]}, "novelty kinds alone"),
            ({"kind": "first"}, "novelty kinds alone"),
        ],
    )
    def test_malformed_rows_fail_loudly(self, fields, message):
        with pytest.raises(CommandError, match=message):
            replay(objection(**fields))

    def test_unknown_walk_bank_and_withdraw_target_fail(self):
        with pytest.raises(CommandError, match="vocabulary"):
            replay([{"e": "walk", "bank": "vibes"}])
        with pytest.raises(CommandError, match="unknown"):
            replay([{"e": "withdraw", "objection": "o9", "reason": "r"}])
