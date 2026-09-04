"""Each backend's projection onto the one result shape."""

from __future__ import annotations

import json

import httpx
import pytest
from btm_search_web import sources
from btm_search_web.records import Result, trimmed

from btm_corekit import CommandError, dump

ARXIV_FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <title>A  Title   With Space</title>
    <summary>An abstract.</summary>
    <published>2025-01-02T00:00:00Z</published>
    <arxiv:doi>10.1/x</arxiv:doi>
  </entry>
</feed>"""


def answering(payload: bytes, status: int = 200):
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, content=payload)
        )
    )


@pytest.fixture
def served(monkeypatch):
    def serve(payload):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        monkeypatch.setattr(sources, "client", lambda: answering(body))

    return serve


class TestShape:
    def test_a_snippet_is_collapsed_and_cut(self):
        assert trimmed("  two   words \n here ", 9) == "two words..."

    def test_absent_scholarly_fields_leave_the_record(self):
        """One shape for every backend: dump omits what a web hit lacks."""
        assert set(dump(Result(title="T", source="web"))) == {
            "title",
            "url",
            "snippet",
            "source",
        }


class TestInstant:
    def test_an_abstract_becomes_the_first_row(self, served):
        served(
            {
                "Heading": "Chaos theory",
                "AbstractText": "A branch of mathematics.",
                "AbstractURL": "https://en.wikipedia.org/wiki/Chaos_theory",
                "RelatedTopics": [{"Text": "Lorenz system", "FirstURL": "https://x"}],
            }
        )
        rows = sources.instant("chaos theory")
        assert rows[0].title == "Chaos theory" and rows[0].source == "instant"
        assert rows[1].title == "Lorenz system"

    def test_no_answer_is_no_rows(self, served):
        served({"AbstractText": "", "RelatedTopics": []})
        assert sources.instant("zzz") == []


class TestScholar:
    def test_openalex_reconstructs_its_inverted_abstract(self, served):
        served(
            {
                "results": [
                    {
                        "display_name": "Predicting uncertainty",
                        "doi": "https://doi.org/10.1/a",
                        "publication_year": 2000,
                        "cited_by_count": 464,
                        "abstract_inverted_index": {"chaotic": [1], "the": [0]},
                    }
                ]
            }
        )
        [row] = sources.scholar("x", 1, sources.Scholar.OPENALEX)
        assert row.doi == "10.1/a" and row.year == 2000 and row.cited_by == 464
        assert row.snippet == "the chaotic"

    def test_crossref_reads_its_date_parts(self, served):
        served(
            {
                "message": {
                    "items": [
                        {
                            "title": ["A paper"],
                            "DOI": "10.1/b",
                            "URL": "https://doi.org/10.1/b",
                            "issued": {"date-parts": [[2019, 3]]},
                            "is-referenced-by-count": 7,
                        }
                    ]
                }
            }
        )
        [row] = sources.scholar("x", 1, sources.Scholar.CROSSREF)
        assert row.year == 2019 and row.cited_by == 7

    def test_arxiv_reads_the_atom_feed(self, served):
        served(ARXIV_FEED.encode())
        [row] = sources.scholar("x", 1, sources.Scholar.ARXIV)
        assert row.title == "A Title With Space"
        assert row.published == "2025-01-02" and row.year == 2025
        assert row.doi == "10.1/x"


class TestFetch:
    def test_a_pdf_is_refused_rather_than_mangled(self, served):
        served(b"%PDF-1.7\nbinary")
        with pytest.raises(CommandError, match="read-pdf"):
            sources.fetch("https://example.org/x.pdf")

    def test_a_page_with_no_article_says_so(self, served):
        served(b"<html><body><script>var x = 1;</script></body></html>")
        with pytest.raises(CommandError, match="no readable article"):
            sources.fetch("https://example.org/listing")

    def test_a_non_http_url_is_refused_before_any_request(self):
        with pytest.raises(CommandError, match="http or https"):
            sources.fetch("file:///etc/passwd")

    def test_an_article_comes_back_as_text(self, served):
        served(
            b"<html><body><article><h1>T</h1>"
            b"<p>"
            + b"A sentence that is long enough to survive extraction. " * 4
            + b"</p></article></body></html>"
        )
        assert "long enough" in sources.fetch("https://example.org/a")
