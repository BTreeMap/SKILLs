"""Derived views: section derivation, violations, hedges, yield, counts."""

from __future__ import annotations

import pytest

from btm_ponder.state import (
    Folded,
    Leaf,
    Ledger,
    Open,
    Refuted,
    Retired,
    Retrieved,
    Source,
    Unresolved,
)
from btm_ponder.views import (
    counts_of,
    hedges,
    leaf_view,
    sections,
    stated,
    violations,
    yield_table,
)


def ledger_with(*leaves: tuple[str, Leaf], swept: bool = False, **sources) -> Ledger:
    built = Ledger(leaves=dict(leaves), swept=swept)
    for sid, cls in sources.items():
        built.sources[sid] = Source("leaf", cls, "title", "")
        built.source_order.append(sid)
    return built


class TestStated:
    @pytest.mark.parametrize("cls", ["constitutive", "attested"])
    def test_one_authoritative_source_speaks_plainly(self, cls):
        assert stated([cls]) == "plain"

    def test_one_measured_source_stays_hedged(self):
        assert stated(["measured"]) == "hedged"

    def test_two_measured_sources_corroborate(self):
        assert stated(["measured", "measured"]) == "plain"

    def test_reported_alone_stays_hedged(self):
        assert stated(["reported"]) == "hedged"

    def test_no_sources_stay_hedged(self):
        assert stated([]) == "hedged"


class TestSections:
    def test_answer_and_sources_always_render(self):
        assert sections(Ledger()) == ["answer", "sources"]

    def test_a_sweep_alone_earns_a_rival_section(self):
        assert "rival" in sections(Ledger(swept=True))

    def test_a_refuted_leaf_earns_a_rival_section(self):
        built = ledger_with(("a", Leaf("q", "frame", Refuted(("s",), "p"))))
        assert "rival" in sections(built)

    def test_an_unresolved_leaf_earns_an_open_section(self):
        built = ledger_with(("a", Leaf("q", "frame", Unresolved("searched", "d"))))
        assert "open" in sections(built)

    def test_chain_needs_more_than_two_retrieved_leaves(self):
        two = ledger_with(
            ("a", Leaf("q", "frame", Retrieved(("s",)))),
            ("b", Leaf("q", "frame", Retrieved(("s",)))),
        )
        assert "chain" not in sections(two)

    def test_three_retrieved_leaves_earn_a_chain(self):
        three = ledger_with(
            ("a", Leaf("q", "frame", Retrieved(("s",)))),
            ("b", Leaf("q", "frame", Retrieved(("s",)))),
            ("c", Leaf("q", "frame", Retrieved(("s",)))),
        )
        assert "chain" in sections(three)


class TestViolations:
    def test_an_open_leaf_blocks_the_draft(self):
        built = ledger_with(("a", Leaf("q", "frame", Open())), swept=True)
        assert any("open leaf blocks draft" in line for line in violations(built))

    def test_a_missing_sweep_is_a_violation(self):
        assert any("no sweep recorded" in line for line in violations(Ledger()))

    def test_a_swept_closed_ledger_is_clean(self):
        built = ledger_with(("a", Leaf("q", "frame", Retrieved(("s",)))), swept=True)
        assert violations(built) == []

    def test_a_fold_onto_a_refuted_target_breaks(self):
        built = ledger_with(
            ("a", Leaf("q", "frame", Refuted(("s",), "p"))),
            ("b", Leaf("q", "frame", Folded("a"))),
            swept=True,
        )
        assert any("fold broken" in line for line in violations(built))

    def test_a_fold_onto_a_missing_target_breaks(self):
        built = ledger_with(("b", Leaf("q", "frame", Folded("ghost"))), swept=True)
        assert any("fold broken" in line for line in violations(built))

    def test_a_retirement_never_breaks(self):
        built = ledger_with(
            ("b", Leaf("q", "frame", Retired("changes nothing"))),
            swept=True,
        )
        assert violations(built) == []


class TestHedges:
    def test_a_reported_leaf_earns_a_hedge_advisory(self):
        built = ledger_with(
            ("a", Leaf("q", "frame", Retrieved(("s1",)))), swept=True, s1="reported"
        )
        assert any("hedge the wording" in line for line in hedges(built))

    def test_a_constitutive_leaf_earns_none(self):
        built = ledger_with(
            ("a", Leaf("q", "frame", Retrieved(("s1",)))), swept=True, s1="constitutive"
        )
        assert hedges(built) == []

    def test_refuted_leaves_are_judged_too(self):
        built = ledger_with(
            ("a", Leaf("q", "frame", Refuted(("s1",), "p"))), swept=True, s1="reported"
        )
        assert len(hedges(built)) == 1

    def test_open_leaves_are_not_judged(self):
        built = ledger_with(("a", Leaf("q", "frame", Open())), swept=True)
        assert hedges(built) == []


class TestYieldTable:
    def test_sources_are_attributed_to_the_round_that_found_them(self):
        events = [
            {"e": "add_source"},
            {"e": "add_source"},
            {"e": "checkpoint", "label": "round-1", "searches": 4},
        ]
        assert yield_table(events) == [
            {"label": "round-1", "searches": 4, "new_sources": 2, "yield": 0.5}
        ]

    def test_each_checkpoint_restarts_the_count(self):
        events = [
            {"e": "add_source"},
            {"e": "checkpoint", "label": "one", "searches": 1},
            {"e": "add_source"},
            {"e": "checkpoint", "label": "two", "searches": 1},
        ]
        assert [row["new_sources"] for row in yield_table(events)] == [1, 1]

    def test_a_round_with_no_searches_reports_no_ratio(self):
        events = [{"e": "checkpoint", "label": "one", "searches": 0}]
        assert yield_table(events)[0]["yield"] is None

    def test_an_unlabelled_round_is_numbered(self):
        events = [{"e": "checkpoint", "searches": 2}]
        assert yield_table(events)[0]["label"] == "round-1"

    def test_sources_after_the_last_checkpoint_are_not_reported(self):
        assert yield_table([{"e": "add_source"}]) == []


class TestLeafView:
    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            (Open(), "open"),
            (Retrieved(("s",)), "retrieved"),
            (Refuted(("s",), "p"), "refuted"),
            (Unresolved("searched", "d"), "unresolved"),
            (Retired("why"), "retired"),
            (Folded("a"), "folded"),
        ],
    )
    def test_every_variant_has_a_view(self, state, expected):
        assert leaf_view(state)["state"] == expected

    def test_refuted_view_carries_its_premise(self):
        assert leaf_view(Refuted(("s",), "assumed x"))["premise"] == "assumed x"

    def test_counts_tally_by_state(self):
        built = ledger_with(
            ("a", Leaf("q", "frame", Open())),
            ("b", Leaf("q", "frame", Open())),
            ("c", Leaf("q", "frame", Retrieved(("s",)))),
        )
        assert counts_of(built) == {"open": 2, "retrieved": 1}

    def test_an_empty_ledger_counts_nothing(self):
        assert counts_of(Ledger()) == {}
