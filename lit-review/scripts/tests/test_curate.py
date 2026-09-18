"""The derived advice and the decision decoder: the parts of screening the
agent reads to choose its next call, and the boundary a batch crosses."""

from __future__ import annotations

import pytest

from btm_corekit import Work
from btm_lit_review.constants import ReadLevel, Status
from btm_lit_review.corpus.curate import Screening, band_advisory, next_step
from btm_lit_review.corpus.paper import paper_from


def paper(key_doi: str, **decisions):
    built = paper_from(
        Work(
            title="a title",
            year=2024,
            authors=("A",),
            venue="venue",
            doi=key_doi,
            arxiv_id=None,
            openalex_id=None,
            cited_by=1,
            abstract=None,
            pdf_url=None,
            landing_url=None,
            published=None,
        )
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


class TestScreening:
    """One batch, one verdict: every unknown key and every malformed decision
    comes back together, and nothing reaches the corpus until none remain."""

    def screened(self, decisions):
        screening = Screening(CORPUS)
        screening.take(decisions)
        return screening

    def located(self, decisions):
        return [(p.where, p.fix, p.hint) for p in self.screened(decisions).problems]

    def test_three_unknown_keys_come_back_in_one_verdict_with_did_you_means(self):
        near = f"{KEY[:-1]}b"
        problems = self.located({key: {} for key in (near, "doi:absent", "nonsense")})
        assert [where for where, _, _ in problems] == [near, "doi:absent", "nonsense"]
        assert KEY in problems[0][2]

    def test_an_unknown_field_is_located_rather_than_ignored(self):
        """The verdict names the offending key, so the fix is one edit."""
        assert self.located({KEY: {"statuss": "included"}})[0][0] == f"{KEY}.statuss"

    def test_a_decision_that_is_not_an_object_is_refused(self):
        """A bare string once read as a set of one-letter field names."""
        where, fix, _ = self.located({KEY: "included"})[0]
        assert where == KEY and "valid dictionary" in fix

    def test_an_exclusion_needs_its_reason(self):
        """The implication the corpus depends on: a flow count traces to a
        stated reason or it traces to nothing."""
        where, fix, _ = self.located({KEY: {"status": "excluded"}})[0]
        assert where == f"{KEY}.reason" and "carries the reason" in fix

    def test_a_bad_key_never_hides_the_bad_decision_beside_it(self):
        problems = self.located({"doi:absent": {}, KEY: {"status": "maybe"}})
        assert [where for where, _, _ in problems] == ["doi:absent", f"{KEY}.status"]

    def test_an_exclusion_with_a_reason_is_admitted(self):
        screening = self.screened({KEY: {"status": "excluded", "reason": "off topic"}})
        assert screening.clean
        assert screening.updates[KEY]["status"] is Status.EXCLUDED
        assert screening.updates[KEY]["decision_reason"] == "off topic"

    def test_a_malformed_decision_stages_no_update(self):
        assert self.screened({KEY: {"status": "maybe"}}).updates == {}


class TestDecisionUpdates:
    def parsed(self, decision):
        screening = Screening(CORPUS)
        screening.take({KEY: decision})
        assert screening.clean, [p.view() for p in screening.problems]
        return screening.updates[KEY]

    def test_an_omitted_field_is_absent_from_the_updates(self):
        """`with_` applies only what comes back, so omitting a field keeps it
        rather than resetting it to a default."""
        assert set(self.parsed({"read_level": "abstract"})) == {"read_level"}

    def test_an_explicit_null_reason_clears_it(self):
        assert self.parsed({"reason": None}) == {"decision_reason": None}

    def test_a_valid_read_level_lands_in_the_domain(self):
        assert self.parsed({"read_level": "full-text"})["read_level"] is (
            ReadLevel.FULL_TEXT
        )


class TestVocabulary:
    """A value outside a closed vocabulary is refused, never coerced: coercing
    `0` to null once cleared a reason instead of refusing it."""

    @pytest.mark.parametrize(
        ("decision", "field"),
        [
            ({"reason": 0}, "reason"),
            ({"status": "maybe"}, "status"),
            ({"read_level": "skimmed"}, "read_level"),
            ({"status": None}, "status"),
        ],
    )
    def test_the_verdict_names_the_field(self, decision, field):
        screening = Screening(CORPUS)
        screening.take({KEY: decision})
        assert [p.where for p in screening.problems] == [f"{KEY}.{field}"]
