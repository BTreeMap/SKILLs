"""Event transitions: what the ledger admits, and what it refuses."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError
from btm_ponder.ledger import apply, replay
from btm_ponder.state import (
    MAX_EVENTS,
    Leaf,
    Ledger,
    Open,
    Refuted,
    Retired,
    Retrieved,
    Unresolved,
)


def seeded() -> Ledger:
    """A leaf with one source, the shape most closes need."""
    ledger = Ledger()
    apply(ledger, {"e": "add_leaf", "id": "leaf-a", "q": "question"})
    apply(
        ledger,
        {
            "e": "add_source",
            "id": "src-a",
            "leaf": "leaf-a",
            "cls": "constitutive",
            "title": "spec",
        },
    )
    return ledger


class TestAddLeaf:
    def test_admitted_leaf_starts_open(self):
        ledger = Ledger()
        apply(ledger, {"e": "add_leaf", "id": "leaf-a", "q": "question"})
        assert ledger.leaves["leaf-a"] == Leaf("question", "frame", Open())

    def test_origin_defaults_to_frame(self):
        ledger = Ledger()
        apply(ledger, {"e": "add_leaf", "id": "leaf-a", "q": "q"})
        assert ledger.leaves["leaf-a"].origin == "frame"

    def test_spawned_origin_is_admitted(self):
        ledger = Ledger()
        apply(ledger, {"e": "add_leaf", "id": "a", "q": "q", "origin": "spawned"})
        assert ledger.leaves["a"].origin == "spawned"

    @pytest.mark.parametrize(
        "event",
        [
            {"e": "add_leaf", "id": "", "q": "q"},
            {"e": "add_leaf", "id": "a", "q": ""},
            {"e": "add_leaf", "id": "a", "q": "q", "origin": "invented"},
        ],
    )
    def test_malformed_leaves_are_refused(self, event):
        with pytest.raises(CommandError):
            apply(Ledger(), event)

    def test_duplicate_leaf_id_is_refused(self):
        ledger = Ledger()
        apply(ledger, {"e": "add_leaf", "id": "a", "q": "q"})
        with pytest.raises(CommandError, match="duplicate leaf id"):
            apply(ledger, {"e": "add_leaf", "id": "a", "q": "other"})


class TestAddSource:
    def test_source_order_records_arrival(self):
        ledger = seeded()
        apply(
            ledger,
            {
                "e": "add_source",
                "id": "src-b",
                "leaf": "leaf-a",
                "cls": "reported",
                "title": "post",
            },
        )
        assert ledger.source_order == ["src-a", "src-b"]

    def test_source_must_attach_to_a_known_leaf(self):
        with pytest.raises(CommandError, match="unknown leaf id"):
            apply(
                seeded(),
                {
                    "e": "add_source",
                    "id": "s",
                    "leaf": "absent",
                    "cls": "reported",
                    "title": "t",
                },
            )

    def test_class_outside_the_set_is_refused(self):
        with pytest.raises(CommandError, match="cls must be one of"):
            apply(
                seeded(),
                {
                    "e": "add_source",
                    "id": "s",
                    "leaf": "leaf-a",
                    "cls": "hearsay",
                    "title": "t",
                },
            )

    def test_url_is_optional(self):
        ledger = seeded()
        assert ledger.sources["src-a"].url == ""


class TestCloses:
    def test_retrieved_records_its_sources(self):
        ledger = seeded()
        apply(
            ledger,
            {
                "e": "close",
                "leaf": "leaf-a",
                "state": "retrieved",
                "sources": ["src-a"],
            },
        )
        assert ledger.leaves["leaf-a"].state == Retrieved(("src-a",))

    def test_retrieved_without_a_source_is_refused(self):
        with pytest.raises(CommandError, match="requires at least one source"):
            apply(seeded(), {"e": "close", "leaf": "leaf-a", "state": "retrieved"})

    def test_refuted_requires_the_contradicted_premise(self):
        with pytest.raises(CommandError, match="requires the contradicted premise"):
            apply(
                seeded(),
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "refuted",
                    "sources": ["src-a"],
                },
            )

    def test_unresolved_requires_detail(self):
        with pytest.raises(CommandError, match="unresolved requires detail"):
            apply(
                seeded(),
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "unresolved",
                    "reason": "searched",
                },
            )

    def test_unresolved_carries_reason_and_detail(self):
        ledger = seeded()
        apply(
            ledger,
            {
                "e": "close",
                "leaf": "leaf-a",
                "state": "unresolved",
                "reason": "searched",
                "detail": "no source found",
            },
        )
        assert ledger.leaves["leaf-a"].state == Unresolved(
            "searched", "no source found"
        )

    def test_close_on_unknown_leaf_is_refused(self):
        with pytest.raises(CommandError, match="unknown leaf id"):
            apply(seeded(), {"e": "close", "leaf": "absent", "state": "retrieved"})

    def test_close_citing_unknown_source_is_refused(self):
        with pytest.raises(CommandError, match="unknown source id"):
            apply(
                seeded(),
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "retrieved",
                    "sources": ["ghost"],
                },
            )


class TestFolds:
    def test_fold_into_a_retrieved_leaf_is_admitted(self):
        ledger = seeded()
        apply(
            ledger,
            {
                "e": "close",
                "leaf": "leaf-a",
                "state": "retrieved",
                "sources": ["src-a"],
            },
        )
        apply(ledger, {"e": "add_leaf", "id": "leaf-b", "q": "second"})
        apply(
            ledger,
            {
                "e": "close",
                "leaf": "leaf-b",
                "state": "retired",
                "reason": "folded",
                "detail": "leaf-a",
            },
        )
        assert ledger.leaves["leaf-b"].state == Retired("folded", "leaf-a")

    def test_fold_into_an_open_leaf_is_refused(self):
        ledger = seeded()
        apply(ledger, {"e": "add_leaf", "id": "leaf-b", "q": "second"})
        with pytest.raises(CommandError, match="fold target must be retrieved"):
            apply(
                ledger,
                {
                    "e": "close",
                    "leaf": "leaf-b",
                    "state": "retired",
                    "reason": "folded",
                    "detail": "leaf-a",
                },
            )

    def test_fold_into_a_missing_leaf_is_refused(self):
        with pytest.raises(CommandError, match="fold target does not exist"):
            apply(
                seeded(),
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "retired",
                    "reason": "folded",
                    "detail": "ghost",
                },
            )

    def test_immaterial_requires_the_conclusion_it_leaves_standing(self):
        with pytest.raises(CommandError, match="immaterial detail"):
            apply(
                seeded(),
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "retired",
                    "reason": "immaterial",
                },
            )


class TestTransitionLegality:
    def closed(self, state: str, **extra) -> Ledger:
        ledger = seeded()
        apply(
            ledger,
            {
                "e": "close",
                "leaf": "leaf-a",
                "state": state,
                "sources": ["src-a"],
                **extra,
            },
        )
        return ledger

    def test_retrieved_may_bend_to_refuted(self):
        ledger = self.closed("retrieved")
        apply(
            ledger,
            {
                "e": "close",
                "leaf": "leaf-a",
                "state": "refuted",
                "sources": ["src-a"],
                "premise": "late contrary evidence",
            },
        )
        assert isinstance(ledger.leaves["leaf-a"].state, Refuted)

    def test_refuted_is_terminal(self):
        ledger = self.closed("refuted", premise="assumed exact length")
        with pytest.raises(CommandError, match="illegal transition"):
            apply(
                ledger,
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "retrieved",
                    "sources": ["src-a"],
                },
            )

    def test_retrieved_may_not_become_unresolved(self):
        ledger = self.closed("retrieved")
        with pytest.raises(CommandError, match="illegal transition"):
            apply(
                ledger,
                {
                    "e": "close",
                    "leaf": "leaf-a",
                    "state": "unresolved",
                    "reason": "searched",
                    "detail": "d",
                },
            )


class TestSweepAndCheckpoint:
    def test_sweep_sets_the_swept_flag(self):
        ledger = Ledger()
        apply(
            ledger,
            {"e": "sweep", "checked": "rivals", "candidates": [], "survivors": []},
        )
        assert ledger.swept is True

    def test_survivors_must_be_a_subset_of_candidates(self):
        with pytest.raises(CommandError, match="subset of candidates"):
            apply(
                Ledger(),
                {"e": "sweep", "checked": "x", "candidates": [], "survivors": ["a"]},
            )

    def test_sweep_requires_what_was_checked(self):
        with pytest.raises(CommandError, match="sweep requires"):
            apply(Ledger(), {"e": "sweep", "checked": "  "})

    def test_checkpoint_requires_a_non_negative_count(self):
        with pytest.raises(CommandError, match="non-negative integer"):
            apply(Ledger(), {"e": "checkpoint", "searches": -1})


class TestReplay:
    def test_replay_is_a_left_fold_over_the_log(self):
        events = [
            {"e": "add_leaf", "id": "a", "q": "q"},
            {"e": "sweep", "checked": "x", "candidates": [], "survivors": []},
        ]
        ledger = replay(events)
        assert ledger.events == 2
        assert ledger.swept is True

    def test_empty_log_replays_to_an_empty_ledger(self):
        assert replay([]).leaves == {}

    def test_a_tampered_line_names_its_position(self):
        with pytest.raises(CommandError, match="ledger line 2 does not replay"):
            replay(
                [
                    {"e": "add_leaf", "id": "a", "q": "q"},
                    {"e": "add_leaf", "id": "a", "q": "again"},
                ]
            )

    def test_unknown_event_kind_is_refused(self):
        with pytest.raises(CommandError, match="unknown event kind"):
            apply(Ledger(), {"e": "teleport"})

    def test_event_cap_is_a_runaway_backstop(self):
        ledger = Ledger()
        ledger.events = MAX_EVENTS
        with pytest.raises(CommandError, match="event cap reached"):
            apply(ledger, {"e": "add_leaf", "id": "a", "q": "q"})
