"""The session marker and the linked corpus, decoded rather than assumed."""

from __future__ import annotations

import json

import pytest

from btm_corekit import CommandError
from btm_peer_review.store import load_corpus


class TestCorpusDecoding:
    def test_a_full_lit_review_row_loads(self, tmp_path):
        """lit-review writes a dozen fields this review never reads; the
        decoder takes the four it needs and leaves the rest."""
        papers = tmp_path / "papers.jsonl"
        papers.write_text(
            json.dumps(
                {
                    "key": "doi:10.1/a",
                    "title": "T",
                    "year": 2020,
                    "authors": ["A"],
                    "venue": None,
                    "doi": "10.1/a",
                    "status": "included",
                    "read_level": "abstract",
                    "found_by": ["s1"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        corpus = load_corpus(papers)
        assert corpus.lookup("DOI:10.1/A").year == 2020

    def test_a_row_without_a_key_is_refused(self, tmp_path):
        """A silent skip hid exactly the drift this decoder exists to catch."""
        papers = tmp_path / "papers.jsonl"
        papers.write_text(json.dumps({"title": "T"}) + "\n", encoding="utf-8")
        with pytest.raises(CommandError, match="key"):
            load_corpus(papers)
