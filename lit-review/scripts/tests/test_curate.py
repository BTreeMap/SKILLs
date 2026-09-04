"""The derived advice and the decision decoder: the parts of screening the
agent reads to choose its next call, and the boundary a batch crosses."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError
from btm_lit_review.constants import ReadLevel, Status
from btm_lit_review.curate import band_advisory, next_step, parse_decision
from btm_lit_review.paper import candidate


def paper(key_doi: str, **decisions):
    built = candidate(
        title="a title",
        year=2024,
        authors=("A",),
        venue="venue",
        doi=key_doi,
        arxiv_id=None,
        openalex_id=None,
        cited_by_count=1,
        abstract=None,
        pdf_url=None,
        landing_url=None,
    )
    return built.with_(**({"found_by": ("s1",)} | decisions))


CORPUS = {paper("10.1/a").key: paper("10.1/a")}
KEY = next(iter(CORPUS))


class TestNextStep:
    """Precedence, not a set of independent hints: an earlier phase always
    wins, so the agent is never told to extract before it has screened."""

    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            ((False, 9, 9, 9, ["k"]), "fill criteria"),
            ((True, 0, 9, 9, ["k"]), "run the first search"),
            ((True, 1, 3, 9, ["k"]), "screen 3 undecided"),
            ((True, 1, 0, 0, []), "nothing is included yet"),
            ((True, 1, 0, 2, ["k", "j"]), "extract 2 included papers"),
            ((True, 1, 0, 2, []), "note findings and gaps"),
        ],
    )
    def test_the_earliest_unfinished_phase_wins(self, state, expected):
        assert expected in next_step(*state)


class TestBandAdvisory:
    @pytest.mark.parametrize(
        ("level", "included", "cue"),
        [
            ("full", 3, "below"),
            ("full", 40, "above"),
            ("lite", 7, None),
            ("full", 0, None),
            ("", 12, None),
            ("invented", 12, None),
        ],
    )
    def test_only_a_known_band_with_papers_advises(self, level, included, cue):
        advice = band_advisory(level, included)
        assert (advice is None) if cue is None else (cue in advice)


class TestParseDecision:
    def test_an_unknown_key_is_refused(self):
        with pytest.raises(CommandError, match="unknown paper key"):
            parse_decision("doi:absent", {"status": "included"}, CORPUS)

    def test_an_unknown_field_is_refused_rather_than_ignored(self):
        with pytest.raises(CommandError, match="unknown fields"):
            parse_decision(KEY, {"statuss": "included"}, CORPUS)

    def test_an_exclusion_needs_its_reason(self):
        """The implication the corpus depends on: a flow count traces to a
        stated reason or it traces to nothing."""
        with pytest.raises(CommandError, match="needs a non-empty reason"):
            parse_decision(KEY, {"status": "excluded"}, CORPUS)

    def test_an_exclusion_with_a_reason_is_admitted(self):
        updates = parse_decision(
            KEY, {"status": "excluded", "reason": "off topic"}, CORPUS
        )
        assert updates["status"] is Status.EXCLUDED
        assert updates["decision_reason"] == "off topic"

    def test_an_omitted_field_is_absent_from_the_updates(self):
        """`with_` applies only what comes back, so omitting a field keeps it
        rather than resetting it to a default."""
        assert set(parse_decision(KEY, {"read_level": "abstract"}, CORPUS)) == {
            "read_level"
        }

    def test_an_explicit_null_reason_clears_it(self):
        assert parse_decision(KEY, {"reason": None}, CORPUS) == {
            "decision_reason": None
        }

    def test_a_wrongly_typed_reason_is_refused_not_coerced(self):
        """status and read_level reject a value outside their vocabulary; a
        reason has to reject a value outside its type for the same reason.
        Coercing `0` to null cleared the field instead of refusing it."""
        with pytest.raises(CommandError, match="must be text or null"):
            parse_decision(KEY, {"reason": 0}, CORPUS)

    def test_a_status_outside_the_vocabulary_names_it(self):
        with pytest.raises(CommandError, match="status of decision"):
            parse_decision(KEY, {"status": "maybe"}, CORPUS)

    def test_a_read_level_outside_the_vocabulary_names_it(self):
        with pytest.raises(CommandError, match="read_level of decision"):
            parse_decision(KEY, {"read_level": "skimmed"}, CORPUS)

    def test_a_valid_read_level_lands_in_the_domain(self):
        updates = parse_decision(KEY, {"read_level": "full-text"}, CORPUS)
        assert updates["read_level"] is ReadLevel.FULL_TEXT
