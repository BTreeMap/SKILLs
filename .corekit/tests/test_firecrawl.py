"""The Firecrawl Research Index: the recorded bodies, the id forms, the cap."""

from __future__ import annotations

import json

import httpx
import pytest

from btm_corekit import CommandError, UpstreamError, Window
from btm_corekit.indexes import firecrawl
from btm_corekit.indexes.work import ByArxiv, ByDoi, ByNative, Passage

ATTENTION_ABSTRACT = (
    "The dominant sequence transduction models are based on complex recurrent "
    "or convolutional neural networks in an encoder-decoder configuration. The "
    "best performing models also connect the encoder and decoder through an "
    "attention mechanism. We propose a new simple network architecture, the "
    "Transformer, based solely on attention mechanisms, dispensing with "
    "recurrence and convolutions entirely. Experiments on two machine "
    "translation tasks show these models to be superior in quality while being "
    "more parallelizable and requiring significantly less time to train. Our "
    "model achieves 28.4 BLEU on the WMT 2014 English-to-German translation "
    "task, improving over the existing best results, including ensembles by "
    "over 2 BLEU. On the WMT 2014 English-to-French translation task, our model "
    "establishes a new single-model state-of-the-art BLEU score of 41.8 after "
    "training for 3.5 days on eight GPUs, a small fraction of the training "
    "costs of the best models from the literature. We show that the Transformer "
    "generalizes well to other tasks by applying it successfully to English "
    "constituency parsing both with large and limited training data."
)

SEARCH = {
    "success": True,
    "partial": False,
    "results": [
        {
            "paperId": "8319239866974784291",
            "primaryId": "arxiv:1706.03762",
            "ids": {"arxiv": ["1706.03762"]},
            "title": "Attention Is All You Need",
            "abstract": ATTENTION_ABSTRACT,
            "score": 0.9852259683067269,
        }
    ],
}
"""The live answer to `GET /search/research/papers?query=attention is all you
need&k=1`, recorded keyless on 2026-10-08."""

PAPER = {
    "success": True,
    "paper": {
        "paperId": "2014215642691656232",
        "ids": {"arxiv": ["2105.05233"]},
        "title": "Diffusion Models Beat GANs on Image Synthesis",
        "abstract": (
            "We show that diffusion models can achieve image sample quality "
            "superior to the current state-of-the-art generative models..."
        ),
        "authors": "Prafulla Dhariwal, Alexander Nichol",
        "categories": ["cs.LG"],
        "createdDate": "Wed, 11 May 2021 18:01:01 GMT",
        "updateDate": "2021-06-01",
    },
}
"""The paper endpoint's documented example (OpenAPI, retrieved 2026-10-08)."""

READ = {
    **PAPER,
    "paperId": "2014215642691656232",
    "query": "classifier guidance",
    "passages": [
        {"text": "We find that classifier guidance improves FID.", "score": 0.71},
        {"text": "   ", "score": 0.1},
        {"text": "| model | FID |\n| --- | --- |\n| ADM-G | 4.59 |", "score": 0.52},
    ],
}
"""Read mode: `ResearchReadPaperResponse` as its schema names the fields."""

SIMILAR = {
    "success": True,
    "results": [
        {
            "paperId": "482107036680302043",
            "primaryId": "arxiv:2006.11239",
            "ids": {"arxiv": ["2006.11239"]},
            "title": "Denoising Diffusion Probabilistic Models",
            "abstract": "We present high quality image synthesis results...",
            "score": 0.032119,
            "signals": {
                "structural": 12,
                "semantic": 0.61,
                "articleRank": 0.00031,
                "seedOverlap": 2,
            },
        }
    ],
    "poolSize": 40,
    "truncated": False,
}
"""The `/similar` endpoint's documented example."""


def routed(status: int, body: object) -> tuple[httpx.Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, content=json.dumps(body).encode())

    return httpx.Client(transport=httpx.MockTransport(answer)), seen


@pytest.fixture(autouse=True)
def keyless(monkeypatch):
    monkeypatch.delenv("BTM_FIRECRAWL_KEY", raising=False)


class TestDecode:
    def test_the_recorded_search_result_crosses_with_every_field(self):
        [paper] = firecrawl.Results.model_validate(SEARCH).results
        assert paper.score == 0.9852259683067269
        work = firecrawl.record(paper)
        assert work.title == "Attention Is All You Need"
        assert work.authors == (), "a search result carries no authors"
        assert work.year is None, "nor a date"
        assert work.venue is None
        assert work.doi is None
        assert work.arxiv_id == "1706.03762"
        assert work.openalex_id is None
        assert work.cited_by is None
        assert work.abstract == ATTENTION_ABSTRACT
        assert work.pdf_url is None
        assert work.landing_url == "https://arxiv.org/abs/1706.03762"
        assert work.published is None

    def test_the_paper_endpoint_crosses_with_every_field(self):
        body = firecrawl.Read.model_validate(PAPER)
        assert body.paper is not None
        assert body.paper.categories == ("cs.LG",)
        work = firecrawl.record(body.paper)
        assert work.title == "Diffusion Models Beat GANs on Image Synthesis"
        assert work.authors == ("Prafulla Dhariwal", "Alexander Nichol")
        assert work.year == 2021
        assert work.venue is None
        assert work.doi is None
        assert work.arxiv_id == "2105.05233", "from ids, with no primaryId sent"
        assert work.openalex_id is None
        assert work.cited_by is None
        assert work.abstract and work.abstract.startswith("We show that diffusion")
        assert work.pdf_url is None
        assert work.landing_url == "https://arxiv.org/abs/2105.05233"
        assert work.published == "2021-05-11", "the RFC 2822 stamp as an ISO day"

    def test_an_iso_created_date_passes_through(self):
        paper = firecrawl.Paper(createdDate="2021-05-11")
        assert firecrawl.record(paper).published == "2021-05-11"

    def test_an_unparseable_created_date_is_absence(self):
        work = firecrawl.record(firecrawl.Paper(createdDate="sometime in May"))
        assert (work.year, work.published) == (None, None)

    def test_a_doi_primary_id_lands_on_the_doi(self):
        paper = firecrawl.Paper(primaryId="doi:10.1101/2020.01.01.123456")
        work = firecrawl.record(paper)
        assert work.doi == "10.1101/2020.01.01.123456"
        assert work.landing_url == "https://doi.org/10.1101/2020.01.01.123456"

    def test_a_pubmed_paper_has_no_landing_this_index_vouches_for(self):
        work = firecrawl.record(firecrawl.Paper(primaryId="pmid:12345"))
        assert (work.doi, work.arxiv_id, work.landing_url) == (None, None, None)

    def test_the_similar_shape_decodes_as_a_ranking(self):
        similar = firecrawl.Similar.model_validate(SIMILAR)
        assert (similar.poolSize, similar.truncated) == (40, False)
        assert firecrawl.record(similar.results[0]).arxiv_id == "2006.11239"


class TestRender:
    @pytest.mark.parametrize(
        ("ref", "segment"),
        [
            (ByNative("8319239866974784291"), "8319239866974784291"),
            (ByArxiv("1706.03762"), "arxiv:1706.03762"),
            (ByDoi("10.1101/2020.01.01.123456"), "doi:10.1101%2F2020.01.01.123456"),
        ],
    )
    def test_every_form_renders_as_one_path_segment(self, ref, segment):
        assert firecrawl.render(ref) == segment


class TestCalls:
    def test_a_search_sends_k_and_the_window_as_date_bounds(self):
        client, seen = routed(200, SEARCH)
        found = firecrawl.search(client, 10_000, "attention", 2, Window(2017, 2018))
        assert seen[0].url.path == "/v2/search/research/papers"
        assert dict(seen[0].url.params) == {
            "query": "attention",
            "k": "2",
            "from": "2017-01-01",
            "to": "2018-12-31",
        }
        assert found.total is None, "the index sends no total"
        assert found.works[0].arxiv_id == "1706.03762"

    def test_keyless_rides_bare_and_a_key_rides_as_a_bearer(self, monkeypatch):
        client, seen = routed(200, SEARCH)
        firecrawl.search(client, 10_000, "q", 1, Window())
        monkeypatch.setenv("BTM_FIRECRAWL_KEY", "fc-123")
        firecrawl.search(client, 10_000, "q", 1, Window())
        assert "authorization" not in seen[0].headers
        assert seen[1].headers["authorization"] == "Bearer fc-123"

    def test_a_429_names_the_daily_cap_and_the_key(self):
        client, seen = routed(429, {})
        with pytest.raises(UpstreamError, match="daily cap") as raised:
            firecrawl.search(client, 10_000, "q", 1, Window())
        assert "BTM_FIRECRAWL_KEY" in str(raised.value)
        assert len(seen) == 1, "a daily cap is not retried into"

    def test_success_false_is_an_upstream_failure(self):
        client, _ = routed(200, {"success": False, "results": []})
        with pytest.raises(UpstreamError, match="success=false"):
            firecrawl.search(client, 10_000, "q", 1, Window())

    def test_a_partial_answer_is_disclosed(self, capsys):
        client, _ = routed(200, {**SEARCH, "partial": True})
        assert firecrawl.search(client, 10_000, "q", 1, Window()).works
        assert "partially" in capsys.readouterr().err

    def test_a_lookup_reads_the_paper_endpoint(self):
        client, seen = routed(200, PAPER)
        work = firecrawl.lookup(client, 10_000, ByArxiv("2105.05233"))
        assert seen[0].url.path == "/v2/search/research/papers/arxiv:2105.05233"
        assert dict(seen[0].url.params) == {}
        assert work is not None and work.year == 2021

    def test_a_paper_it_does_not_hold_is_absence_to_a_lookup(self):
        client, _ = routed(404, {})
        assert firecrawl.lookup(client, 10_000, ByNative("1")) is None


class TestPassages:
    def test_a_query_reads_ranked_passages_and_drops_blank_ones(self):
        client, seen = routed(200, READ)
        found = firecrawl.passages(
            client, 10_000, ByNative("2014215642691656232"), "classifier guidance", 3
        )
        assert dict(seen[0].url.params) == {"query": "classifier guidance", "k": "3"}
        assert found == (
            Passage(text="We find that classifier guidance improves FID.", score=0.71),
            Passage(
                text="| model | FID |\n| --- | --- |\n| ADM-G | 4.59 |", score=0.52
            ),
        ), "a markdown table keeps its line breaks"

    def test_no_query_is_the_abstract_unscored(self):
        client, seen = routed(200, PAPER)
        [passage] = firecrawl.passages(client, 10_000, ByArxiv("2105.05233"), None, 4)
        assert dict(seen[0].url.params) == {}, "k is only valid beside a query"
        assert passage.score is None
        assert passage.text.startswith("We show that diffusion")

    def test_a_paper_it_does_not_hold_is_a_refusal_not_silence(self):
        client, _ = routed(404, {})
        with pytest.raises(CommandError, match="holds no paper") as raised:
            firecrawl.passages(client, 10_000, ByNative("1"), "q", 4)
        assert not isinstance(raised.value, UpstreamError)
