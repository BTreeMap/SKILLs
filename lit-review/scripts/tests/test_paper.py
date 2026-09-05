"""Paper identity: normalization, keys, aliases, merging, and the parse boundary."""

from __future__ import annotations

import pytest

from btm_corekit import (
    CommandError,
    Work,
    dump,
)
from btm_lit_review.constants import ReadLevel, Status
from btm_lit_review.corpus.paper import (
    absorb,
    merge_papers,
    normalize_title,
    paper_aliases,
    paper_from,
    paper_from_json,
    paper_key,
)

BIBLIOGRAPHIC = {
    "title": "T",
    "year": None,
    "authors": (),
    "venue": None,
    "doi": None,
    "arxiv_id": None,
    "openalex_id": None,
    "cited_by": None,
    "abstract": None,
    "pdf_url": None,
    "landing_url": None,
    "published": None,
}


def paper(**overrides):
    """One crossed record, so a test states only the field it varies."""
    return paper_from(Work(**{**BIBLIOGRAPHIC, **overrides}))


class TestNormalization:
    """Only what this member owns; the identifier normalizers moved to the
    kernel with their tests."""

    def test_title_normalization_ignores_case_and_punctuation(self):
        assert normalize_title("The Cat: A Study!") == normalize_title(
            "the cat a study"
        )


class TestKeys:
    def test_a_doi_outranks_other_identifiers(self):
        assert paper_key("10.1/a", "2401.01234", "Title") == "doi:10.1/a"

    def test_an_arxiv_id_is_used_when_no_doi_exists(self):
        assert paper_key(None, "2401.01234", "Title") == "arxiv:2401.01234"

    def test_a_title_is_the_last_resort(self):
        assert paper_key(None, None, "The Title").startswith("title:")

    def test_aliases_cover_every_identifier_a_record_carries(self):
        record = paper(doi="10.1/a", arxiv_id="2401.01234")
        assert set(paper_aliases(record)) >= {"doi:10.1/a", "arxiv:2401.01234"}


class TestMerge:
    def test_merging_fills_gaps_without_overwriting(self):
        existing = paper(doi="10.1/a", year=2020)
        incoming = paper(doi="10.1/a", year=2021, venue="Journal")
        merged = merge_papers(existing, incoming)
        assert merged.year == 2020  # first writer wins
        assert merged.venue == "Journal"  # gap filled

    def test_a_decision_already_taken_never_moves(self):
        existing = paper(doi="10.1/a")
        decided = existing.with_(status=Status.INCLUDED, read_level=ReadLevel.FULL_TEXT)
        merged = merge_papers(decided, paper(doi="10.1/a", venue="J"))
        assert merged.status == "included"
        assert merged.read_level == "full-text"

    def test_absorb_deduplicates_by_identifier(self):
        corpus, new = absorb({}, [paper(doi="10.1/a")])
        corpus, again = absorb(corpus, [paper(doi="10.1/a", venue="J")])
        assert len(corpus) == 1
        assert (new, again) == (1, 0)

    def test_absorb_keeps_distinct_papers_apart(self):
        corpus, _ = absorb({}, [paper(title="A", doi="10.1/a")])
        corpus, _ = absorb(corpus, [paper(title="B", doi="10.1/b")])
        assert len(corpus) == 2

    def test_absorb_matches_across_identifier_kinds(self):
        """A record sharing only an arXiv id is the same paper."""
        corpus, _ = absorb({}, [paper(doi="10.1/a", arxiv_id="2401.01234")])
        corpus, new = absorb(corpus, [paper(arxiv_id="2401.01234")])
        assert len(corpus) == 1 and new == 0


class TestParseBoundary:
    def valid_row(self) -> dict:
        return dump(paper(doi="10.1/a"))

    def test_a_record_this_program_wrote_parses_back(self):
        row = self.valid_row()
        assert paper_from_json(row).title == "T"

    def test_tuple_fields_survive_the_json_round_trip(self):
        row = self.valid_row()
        row["authors"] = ["Ada", "Grace"]
        assert paper_from_json(row).authors == ("Ada", "Grace")

    def test_an_unknown_field_is_refused(self):
        row = self.valid_row()
        row["invented"] = 1
        with pytest.raises(CommandError, match="Extra inputs are not permitted"):
            paper_from_json(row)

    def test_a_status_outside_the_vocabulary_is_refused(self):
        """The rejection names the field, the key, and the offending value."""
        row = self.valid_row()
        row["status"] = "maybe"
        with pytest.raises(CommandError, match=r"status: Input should be"):
            paper_from_json(row)

    def test_a_read_level_outside_the_vocabulary_is_refused(self):
        row = self.valid_row()
        row["read_level"] = "skimmed"
        with pytest.raises(CommandError, match=r"read_level: Input should be"):
            paper_from_json(row)

    def test_an_exclusion_without_a_reason_is_refused(self):
        """The write paths already hold this; so must the read path, or a
        hand-edited corpus breaks the report's flow counts in silence."""
        row = self.valid_row()
        row["status"] = "excluded"
        row["decision_reason"] = None
        with pytest.raises(CommandError, match="excluded paper carries the reason"):
            paper_from_json(row)

    def test_a_reasoned_exclusion_parses_into_the_closed_vocabulary(self):
        row = self.valid_row()
        row["status"] = "excluded"
        row["decision_reason"] = "off topic"
        paper = paper_from_json(row)
        assert paper.status is Status.EXCLUDED
        assert paper.read_level is ReadLevel.NONE
