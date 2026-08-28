"""Paper identity: normalization, keys, aliases, merging, and the parse boundary."""

from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from btm_corekit import CommandError
from btm_lit_review.paper import (
    absorb,
    candidate,
    clean_text,
    merge_papers,
    normalize_arxiv_id,
    normalize_doi,
    normalize_title,
    paper_aliases,
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
    "cited_by_count": None,
    "abstract": None,
    "pdf_url": None,
    "landing_url": None,
}


def paper(**overrides):
    """candidate() forwards every Paper field, so tests state them all once."""
    return candidate(**{**BIBLIOGRAPHIC, **overrides})


class TestNormalization:
    def test_runs_of_whitespace_collapse(self):
        assert clean_text("Hello   world\n") == "Hello world"

    def test_empty_text_normalizes_to_absence(self):
        assert clean_text("   ") is None
        assert clean_text(None) is None

    @pytest.mark.parametrize(
        "raw", ["10.1/AbC", "https://doi.org/10.1/AbC", "DOI:10.1/AbC"]
    )
    def test_doi_forms_converge(self, raw):
        assert normalize_doi(raw) == "10.1/abc"

    def test_a_non_doi_normalizes_to_absence(self):
        assert normalize_doi("not-a-doi") is None

    @pytest.mark.parametrize(
        "raw", ["2401.01234", "arXiv:2401.01234v3", "https://arxiv.org/abs/2401.01234"]
    )
    def test_arxiv_forms_converge_and_drop_the_version(self, raw):
        assert normalize_arxiv_id(raw) == "2401.01234"

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
        decided = replace(existing, status="included", read_level="full-text")
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
        return asdict(paper(doi="10.1/a"))

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
        with pytest.raises(CommandError, match="unknown fields"):
            paper_from_json(row)

    def test_a_status_outside_the_vocabulary_is_refused(self):
        row = self.valid_row()
        row["status"] = "maybe"
        with pytest.raises(CommandError, match="corrupt paper record"):
            paper_from_json(row)

    def test_a_read_level_outside_the_vocabulary_is_refused(self):
        row = self.valid_row()
        row["read_level"] = "skimmed"
        with pytest.raises(CommandError, match="corrupt paper record"):
            paper_from_json(row)
