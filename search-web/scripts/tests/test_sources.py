"""Each backend's projection onto the one result shape."""

from __future__ import annotations

import hashlib
import json

import httpx
import pytest
from btm_search_web import sources
from btm_search_web.records import Result, trimmed

from btm_corekit import ByArxiv, ByDoi, ByNative, CommandError, Passage, dump
from btm_corekit.indexes import arxiv, semanticscholar

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


@pytest.fixture(autouse=True)
def _unpaced(monkeypatch):
    """The kernel's paces are tested there; here they cost nothing."""
    paces = (arxiv.PACE, semanticscholar.KEYED_PACE, semanticscholar.KEYLESS_PACE)
    for pace in paces:
        monkeypatch.setattr(pace, "interval", 0.0)


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
        [row] = sources.scholar("x", 1, "openalex")
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
        [row] = sources.scholar("x", 1, "crossref")
        assert row.year == 2019 and row.cited_by == 7

    def test_arxiv_reads_the_atom_feed(self, served):
        served(ARXIV_FEED.encode())
        [row] = sources.scholar("x", 1, "arxiv")
        assert row.title == "A Title With Space"
        assert row.published == "2025-01-02" and row.year == 2025
        assert row.doi == "10.1/x"

    def test_semanticscholar_answers_in_the_one_shape(self, served):
        served(
            {
                "total": 1,
                "data": [
                    {
                        "paperId": "abc",
                        "title": "A paper",
                        "year": 2012,
                        "citationCount": 9,
                        "externalIds": {"DOI": "10.1/S"},
                    }
                ],
            }
        )
        [row] = sources.scholar("x", 1, "semanticscholar")
        assert row.source == "semanticscholar"
        assert (row.doi, row.year, row.cited_by) == ("10.1/s", 2012, 9)
        assert row.url == "https://doi.org/10.1/s"

    def test_firecrawl_answers_in_the_one_shape(self, served):
        served(
            {
                "success": True,
                "results": [
                    {
                        "paperId": "8319239866974784291",
                        "primaryId": "arxiv:1706.03762",
                        "title": "Attention Is All You Need",
                        "abstract": "The dominant models.",
                        "score": 0.98,
                    }
                ],
            }
        )
        [row] = sources.scholar("x", 1, "firecrawl")
        assert row.source == "firecrawl"
        assert row.url == "https://arxiv.org/abs/1706.03762"
        assert row.snippet == "The dominant models."


class TestParseRef:
    @pytest.mark.parametrize(
        ("token", "ref"),
        [
            ("10.1145/3065386", ByDoi("10.1145/3065386")),
            ("https://doi.org/10.1145/3065386", ByDoi("10.1145/3065386")),
            ("1706.03762", ByArxiv("1706.03762")),
            ("arXiv:1706.03762v7", ByArxiv("1706.03762")),
            ("https://arxiv.org/abs/hep-th/9901001", ByArxiv("hep-th/9901001")),
            ("10.48550/arXiv.1706.03762", ByArxiv("1706.03762")),
            ("8319239866974784291", ByNative("8319239866974784291")),
            (" W2741809807 ", ByNative("W2741809807")),
        ],
    )
    def test_every_written_form_parses_to_one_ref(self, token, ref):
        """The DOI arXiv registers names the arXiv paper: an index holding the
        preprint knows it by that id, not by the DataCite DOI."""
        assert sources.parse_ref(token) == ref

    def test_an_empty_reference_is_refused(self):
        with pytest.raises(CommandError, match="DOI, an arXiv id"):
            sources.parse_ref("  ")

    @pytest.mark.parametrize(
        ("ref", "spelled"),
        [
            (ByDoi("10.1/a"), "doi:10.1/a"),
            (ByArxiv("1706.03762"), "arxiv:1706.03762"),
            (ByNative("123"), "123"),
        ],
    )
    def test_the_parsed_ref_is_echoed_in_one_spelling(self, ref, spelled):
        assert sources.spelled(ref) == spelled


class TestRead:
    def test_passages_come_back_ranked(self, served):
        served(
            {
                "success": True,
                "paper": {"paperId": "1", "title": "T", "abstract": "A."},
                "passages": [{"text": "Multi-head attention.", "score": 0.8}],
            }
        )
        found = sources.read(ByArxiv("1706.03762"), "heads", 4, "firecrawl")
        assert found == (Passage(text="Multi-head attention.", score=0.8),)

    def test_an_index_without_passages_names_the_ones_with(self):
        with pytest.raises(CommandError, match="indexes that do: firecrawl"):
            sources.read(ByArxiv("1706.03762"), "heads", 4, "openalex")


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


class TestSave:
    def test_the_raw_body_lands_unchanged_with_its_digest(self, served, tmp_path):
        """A data file is pinned by the bytes the server sent, so nothing in
        between may extract, decode, or refuse them, a PDF included."""
        body = b"%PDF-1.7\n" + bytes(range(256)) * 64
        served(body)
        target = tmp_path / "data" / "set.bin"
        saved = sources.save("https://example.org/set.bin", target)
        assert target.read_bytes() == body
        assert saved == sources.Saved(len(body), hashlib.sha256(body).hexdigest())

    def test_an_existing_file_is_refused_and_left_alone(self, served, tmp_path):
        served(b"new")
        target = tmp_path / "set.csv"
        target.write_bytes(b"old")
        with pytest.raises(CommandError, match="exists"):
            sources.save("https://example.org/set.csv", target)
        assert target.read_bytes() == b"old"

    def test_a_non_http_url_is_refused_before_any_file(self, tmp_path):
        target = tmp_path / "x"
        with pytest.raises(CommandError, match="http or https"):
            sources.save("file:///etc/passwd", target)
        assert not target.exists()
