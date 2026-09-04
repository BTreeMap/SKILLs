"""The scholarly indexes: what their records mean and how a feed parses."""

from __future__ import annotations

import json

import httpx
import pytest

from btm_corekit import (
    ArxivFeed,
    CrossrefItem,
    OpenAlexWork,
    arxiv_feed,
    batched,
    crossref_filter,
    crossref_page,
    openalex_page,
    year_filter,
)

FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>412</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.01234v2</id>
    <title>A Study of Things</title>
    <summary>We study things.</summary>
    <published>2024-01-05T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <journal_ref>J. Things 3</journal_ref>
    <arxiv:doi>10.1/xyz</arxiv:doi>
    <link title="pdf" href="http://arxiv.org/pdf/2401.01234v2"/>
  </entry>
</feed>"""


def answering(payload: bytes) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=payload)
        )
    )


def serving(record: object) -> httpx.Client:
    return answering(json.dumps(record).encode())


class TestOpenAlexWork:
    def test_an_inverted_abstract_rebuilds_its_word_order(self):
        work = OpenAlexWork.model_validate(
            {"abstract_inverted_index": {"a": [0, 2], "b": [1]}}
        )
        assert work.abstract == "a b a"

    def test_no_abstract_is_empty_text(self):
        assert OpenAlexWork().abstract == ""

    def test_the_key_is_the_last_segment_of_the_url(self):
        assert OpenAlexWork(id="https://openalex.org/W123").key == "W123"

    def test_authors_come_back_flat(self):
        work = OpenAlexWork.model_validate(
            {"authorships": [{"author": {"display_name": "Ada"}}, {"author": {}}]}
        )
        assert work.authors == ("Ada",)

    def test_a_field_the_index_added_is_not_fatal(self):
        """Another service owns this shape and may extend it."""
        assert OpenAlexWork.model_validate({"invented_next_year": 1}).id == ""


class TestCrossrefItem:
    def test_a_date_part_becomes_a_year(self):
        item = CrossrefItem.model_validate({"issued": {"date-parts": [[2022, 4]]}})
        assert item.issued.year == 2022

    def test_an_absent_date_is_absent(self):
        assert CrossrefItem().issued.year is None

    def test_a_name_joins_its_halves(self):
        item = CrossrefItem.model_validate(
            {"author": [{"given": "Grace", "family": "Hopper"}, {"family": "Ada"}]}
        )
        assert item.authors == ("Grace Hopper", "Ada")


class TestArxivFeed:
    def test_a_feed_parses_into_entries(self):
        feed = arxiv_feed(answering(FEED.encode()), 10_000, "things", 1)
        assert feed.total == 412
        [entry] = feed.entries
        assert entry.title == "A Study of Things"
        assert entry.authors == ("Ada Lovelace", "Grace Hopper")
        assert entry.doi == "10.1/xyz"
        assert entry.journal_ref == "J. Things 3"
        assert entry.pdf_url == "http://arxiv.org/pdf/2401.01234v2"

    def test_an_empty_feed_is_not_a_failure(self):
        empty = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        assert arxiv_feed(answering(empty.encode()), 10_000, "x", 1) == ArxivFeed()


class TestPages:
    def test_an_openalex_page_carries_its_total(self):
        page = openalex_page(
            serving({"meta": {"count": 9}, "results": [{"display_name": "T"}]}),
            10_000,
            {},
        )
        assert page.meta.count == 9 and page.results[0].display_name == "T"

    def test_a_crossref_page_carries_its_total(self):
        message = crossref_page(
            serving({"message": {"total-results": 4, "items": [{"DOI": "10.1/a"}]}}),
            10_000,
            {},
        )
        assert message.total == 4 and message.items[0].doi == "10.1/a"


class TestQueryHelpers:
    @pytest.mark.parametrize(
        ("bounds", "expected"),
        [
            ((None, None), ""),
            ((2020, None), "from_publication_date:2020-01-01"),
            ((None, 2024), "to_publication_date:2024-12-31"),
        ],
    )
    def test_a_year_window_names_only_the_bounds_it_has(self, bounds, expected):
        assert year_filter(*bounds) == expected

    def test_crossref_spells_its_window_differently(self):
        assert crossref_filter(2020, 2024) == (
            "from-pub-date:2020-01-01,until-pub-date:2024-12-31"
        )

    def test_batching_covers_every_id_once(self):
        ids = [str(n) for n in range(7)]
        assert [list(batch) for batch in batched(ids, 3)] == [
            ["0", "1", "2"],
            ["3", "4", "5"],
            ["6"],
        ]
        assert batched([], 3) == []
