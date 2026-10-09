"""Semantic Scholar: the recorded bodies, the id forms, and the shared pool."""

from __future__ import annotations

import json

import httpx
import pytest

from btm_corekit import UpstreamError, Window
from btm_corekit.indexes import semanticscholar as s2
from btm_corekit.indexes.work import ByArxiv, ByDoi, ByNative

LOOKUP = {
    "paperId": "abd1c342495432171beb7ca8fd9551ef13cbd0ff",
    "title": "ImageNet classification with deep convolutional neural networks",
}
"""The live answer to `GET /paper/DOI:10.1145/3065386`, recorded 2026-10-08."""

PAPER = {
    "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
    "externalIds": {
        "MAG": "3015453090",
        "DBLP": "conf/acl/LoWNKW20",
        "ACL": "2020.acl-main.447",
        "DOI": "10.18653/V1/2020.ACL-MAIN.447",
        "CorpusId": 215416146,
    },
    "title": "Construction of the Literature Graph in Semantic Scholar",
    "abstract": (
        "We describe a deployed scalable system for organizing published "
        "scientific literature into a heterogeneous graph to facilitate "
        "algorithmic manipulation and discovery."
    ),
    "venue": "Annual Meeting of the Association for Computational Linguistics",
    "year": 1997,
    "citationCount": 453,
    "openAccessPdf": {
        "url": "https://www.aclweb.org/anthology/2020.acl-main.447.pdf",
        "status": "HYBRID",
        "license": "CCBY",
        "disclaimer": "Notice: This snippet is extracted from the open access paper",
    },
    "publicationDate": "2024-04-29",
    "authors": [{"authorId": "1741101", "name": "Oren Etzioni"}],
}
"""The OpenAPI document's own `FullPaper` example values: the live search
answered 429 twice, so the search shape comes from the published schema."""

SEARCH = {"total": 15117, "offset": 0, "next": 1, "data": [PAPER]}


def routed(status: int, body: object) -> tuple[httpx.Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, content=json.dumps(body).encode())

    return httpx.Client(transport=httpx.MockTransport(answer)), seen


@pytest.fixture(autouse=True)
def _unpaced(monkeypatch):
    """The paces are real and tested in test_pace; here they cost nothing."""
    for pace in (s2.KEYED_PACE, s2.KEYLESS_PACE):
        monkeypatch.setattr(pace, "interval", 0.0)
        monkeypatch.setattr(pace, "sleep", lambda seconds: None)


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setenv("BTM_SEMANTICSCHOLAR_KEY", "s2-key")


@pytest.fixture
def keyless(monkeypatch):
    monkeypatch.delenv("BTM_SEMANTICSCHOLAR_KEY", raising=False)
    s2._keyless_advisory.cache_clear()


class TestDecode:
    def test_the_recorded_lookup_crosses_with_what_it_carried(self):
        work = s2.record(s2.Paper.model_validate(LOOKUP))
        assert work.title == LOOKUP["title"]
        assert work.authors == ()
        assert work.year is None
        assert work.venue is None
        assert work.doi is None
        assert work.arxiv_id is None
        assert work.openalex_id is None
        assert work.cited_by is None
        assert work.abstract is None
        assert work.pdf_url is None
        assert work.landing_url == (
            "https://www.semanticscholar.org/paper/"
            "abd1c342495432171beb7ca8fd9551ef13cbd0ff"
        ), "with no DOI or arXiv id, the paper's own page"
        assert work.published is None

    def test_a_full_paper_crosses_with_every_field(self):
        page = s2.Page.model_validate(SEARCH)
        assert (page.total, page.offset, page.next) == (15117, 0, 1)
        work = s2.record(page.data[0])
        assert work.title == "Construction of the Literature Graph in Semantic Scholar"
        assert work.authors == ("Oren Etzioni",)
        assert work.year == 1997
        assert work.venue == (
            "Annual Meeting of the Association for Computational Linguistics"
        )
        assert work.doi == "10.18653/v1/2020.acl-main.447", "folded to bare form"
        assert work.arxiv_id is None
        assert work.openalex_id is None
        assert work.cited_by == 453
        assert work.abstract == PAPER["abstract"]
        assert work.pdf_url == "https://www.aclweb.org/anthology/2020.acl-main.447.pdf"
        assert work.landing_url == "https://doi.org/10.18653/v1/2020.acl-main.447"
        assert work.published == "2024-04-29"

    def test_a_total_sent_as_a_string_is_still_a_count(self):
        """The schema documents `total` as a string; the service sends a number."""
        assert s2.Page.model_validate({"total": "15117"}).total == 15117

    def test_an_arxiv_paper_lands_on_its_abs_page(self):
        paper = s2.Paper.model_validate(
            {"paperId": "x", "externalIds": {"ArXiv": "1706.03762"}}
        )
        work = s2.record(paper)
        assert work.arxiv_id == "1706.03762"
        assert work.landing_url == "https://arxiv.org/abs/1706.03762"

    def test_a_closed_paper_has_no_pdf_rather_than_an_empty_one(self):
        paper = s2.Paper.model_validate({"openAccessPdf": {"url": "", "status": None}})
        assert s2.record(paper).pdf_url is None

    def test_an_empty_venue_is_absence(self):
        assert s2.record(s2.Paper.model_validate({"venue": ""})).venue is None

    def test_reference_and_citation_rows_unwrap_their_paper(self):
        cited = s2.References.model_validate({"data": [{"citedPaper": PAPER}]})
        citing = s2.Citations.model_validate({"data": [{"citingPaper": PAPER}]})
        assert cited.data[0].citedPaper == citing.data[0].citingPaper


class TestRender:
    @pytest.mark.parametrize(
        ("ref", "segment"),
        [
            (
                ByNative("abd1c342495432171beb7ca8fd9551ef13cbd0ff"),
                "abd1c342495432171beb7ca8fd9551ef13cbd0ff",
            ),
            (ByNative("CorpusId:215416146"), "CorpusId:215416146"),
            (ByDoi("10.1145/3065386"), "DOI:10.1145/3065386"),
            (ByArxiv("1706.03762"), "ARXIV:1706.03762"),
        ],
    )
    def test_every_form_renders_as_its_path_segment(self, ref, segment):
        assert s2.render(ref) == segment

    @pytest.mark.parametrize(
        ("window", "spelled"),
        [
            (Window(2016, 2020), "2016-2020"),
            (Window(2010, None), "2010-"),
            (Window(None, 2015), "-2015"),
        ],
    )
    def test_an_open_end_stays_empty(self, window, spelled):
        assert s2.year_range(window) == spelled


class TestCalls:
    def test_a_search_asks_for_exactly_the_fields_a_work_reads(self, keyed):
        client, seen = routed(200, SEARCH)
        found = s2.search(client, 10_000, "q", 7, Window(2019, None))
        assert seen[0].url.path == "/graph/v1/paper/search"
        assert dict(seen[0].url.params) == {
            "query": "q",
            "limit": "7",
            "fields": s2.FIELDS,
            "year": "2019-",
        }
        assert found.total == 15117 and len(found.works) == 1

    def test_no_window_sends_no_year(self, keyed):
        client, seen = routed(200, {})
        assert s2.search(client, 10_000, "q", 7, Window()).works == ()
        assert "year" not in seen[0].url.params

    def test_a_key_rides_as_x_api_key(self, keyed):
        client, seen = routed(200, LOOKUP)
        s2.lookup(client, 10_000, ByDoi("10.1145/3065386"))
        assert seen[0].headers["x-api-key"] == "s2-key"
        assert seen[0].url.path == "/graph/v1/paper/DOI:10.1145/3065386"

    def test_a_paper_it_does_not_hold_is_absence(self, keyed):
        client, _ = routed(404, {"error": "Paper not found"})
        assert s2.lookup(client, 10_000, ByDoi("10.9/x")) is None

    def test_references_unwrap_and_report_no_total(self, keyed):
        client, seen = routed(200, {"data": [{"citedPaper": PAPER}, {}]})
        found = s2.references(client, 10_000, ByArxiv("1706.03762"), 30)
        assert seen[0].url.path == "/graph/v1/paper/ARXIV:1706.03762/references"
        assert seen[0].url.params["limit"] == "30"
        assert found.total is None, "the endpoint sends none"
        assert [work.cited_by for work in found.works] == [453]

    def test_citations_unwrap_the_citing_paper(self, keyed):
        client, seen = routed(200, {"data": [{"citingPaper": PAPER}]})
        found = s2.citations(client, 10_000, ByNative("abc"), 5)
        assert seen[0].url.path == "/graph/v1/paper/abc/citations"
        assert found.works[0].title == PAPER["title"]


class TestPool:
    def test_keyless_rides_bare_and_is_disclosed_once(self, keyless, capsys):
        client, seen = routed(200, LOOKUP)
        s2.lookup(client, 10_000, ByNative("a"))
        s2.lookup(client, 10_000, ByNative("a"))
        assert "x-api-key" not in seen[0].headers
        err = capsys.readouterr().err
        assert err.count("BTM_SEMANTICSCHOLAR_KEY") == 1
        assert "semanticscholar.org/product/api" in err
        assert "1 request per second" in err

    def test_each_access_takes_its_own_pace(self, keyed, monkeypatch):
        assert s2.credential()[1] is s2.KEYED_PACE
        monkeypatch.delenv("BTM_SEMANTICSCHOLAR_KEY")
        assert s2.credential()[1] is s2.KEYLESS_PACE

    def test_the_intervals_are_the_measured_ones(self):
        assert (s2.KEYED_INTERVAL_SECONDS, s2.KEYLESS_INTERVAL_SECONDS) == (1.0, 3.0)

    def test_a_429_is_retried_then_names_the_key(self, keyless):
        client, seen = routed(429, {"message": "Too Many Requests.", "code": "429"})
        with pytest.raises(UpstreamError, match="BTM_SEMANTICSCHOLAR_KEY") as raised:
            s2.search(client, 10_000, "q", 1, Window())
        assert len(seen) == 3, "the first try and two backoffs"
        assert raised.value.status == 429

    def test_a_keyed_429_asks_only_for_patience(self, keyed):
        client, _ = routed(429, {})
        with pytest.raises(UpstreamError, match="retry later"):
            s2.search(client, 10_000, "q", 1, Window())
