"""cite: the lit-review corpus read as Works, then the registry in order."""

from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest

from btm_corekit import (
    CommandError,
    Parser,
    UpstreamError,
    read_shelf,
    run_cli,
    wire_cite,
)
from btm_corekit.indexes import arxiv, openalex, semanticscholar
from btm_corekit.indexes import cite as citing

RECORDED = Path(__file__).parent / "fixtures" / "papers.jsonl"
"""Three rows recorded from a lit-review session's papers.jsonl, abstracts
cut to 120 characters: an included DOI record, an excluded arXiv record
whose DOI is arXiv's own, and a title-keyed record with neither identifier."""


@pytest.fixture(autouse=True)
def unpaced(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keyless Semantic Scholar and arXiv pace their calls; the order under
    test does not depend on the wait."""
    monkeypatch.setattr(semanticscholar.KEYLESS_PACE, "sleep", lambda seconds: None)
    monkeypatch.setattr(arxiv.PACE, "sleep", lambda seconds: None)
    monkeypatch.delenv(openalex.KEY_ENV, raising=False)
    monkeypatch.delenv(semanticscholar.KEY_ENV, raising=False)


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    session = tmp_path / "controlled-language-abc"
    session.mkdir()
    (session / "protocol.json").write_text("{}", encoding="utf-8")
    path = session / "papers.jsonl"
    path.write_text(RECORDED.read_text(encoding="utf-8"), encoding="utf-8")
    return path


EMPTY_FEED = b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>'


def refusing() -> httpx.Client:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"no request owed: {request.url}")

    return httpx.Client(transport=httpx.MockTransport(refuse))


def answering(
    statuses: dict[str, int], asked: list[str], body: object = None
) -> httpx.Client:
    """Each host answers its status; a 200 carries `body`. Records hosts."""

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.host)
        status = statuses[request.url.host]
        payload = json.dumps(body if status == 200 else {}).encode()
        return httpx.Response(status, content=payload)

    return httpx.Client(transport=httpx.MockTransport(answer))


class TestShelf:
    def test_a_recorded_corpus_reads_into_works(self, corpus):
        shelf = read_shelf(corpus)
        assert len(shelf.works) == 3
        work = shelf.works["doi:10.48550/arxiv.2302.11957"]
        assert work.cited_by == 21, "cited_by_count crosses into Work.cited_by"
        assert work.arxiv_id == "2302.11957"
        assert work.published is None
        assert shelf.name == "controlled-language-abc"

    @pytest.mark.parametrize(
        ("ref", "key"),
        [
            (
                "doi:10.1109/cei66465.2025.11398497",
                "doi:10.1109/cei66465.2025.11398497",
            ),
            ("10.1109/CEI66465.2025.11398497", "doi:10.1109/cei66465.2025.11398497"),
            (
                "https://doi.org/10.1109/cei66465.2025.11398497",
                "doi:10.1109/cei66465.2025.11398497",
            ),
            ("2302.11957", "doi:10.48550/arxiv.2302.11957"),
            ("arXiv:2302.11957v2", "doi:10.48550/arxiv.2302.11957"),
        ],
    )
    def test_a_key_doi_or_arxiv_id_finds_its_record(self, corpus, ref, key):
        assert read_shelf(corpus).find(ref) == key

    def test_an_absent_reference_finds_nothing(self, corpus):
        assert read_shelf(corpus).find("10.9/elsewhere") is None

    def test_a_row_without_a_key_is_refused_by_name(self, tmp_path):
        path = tmp_path / "papers.jsonl"
        path.write_text('{"title": "T"}\n', encoding="utf-8")
        with pytest.raises(CommandError, match="key"):
            read_shelf(path)

    def test_a_missing_corpus_is_refused(self, tmp_path):
        with pytest.raises(CommandError, match="no corpus"):
            read_shelf(tmp_path / "papers.jsonl")


class TestOrder:
    def test_the_corpus_answers_before_any_request(self, corpus):
        found = citing.cite("2302.11957", read_shelf(corpus), refusing())
        assert found.key == "doi:10.48550/arxiv.2302.11957"
        assert found.source == "controlled-language-abc"
        assert found.title == "Sentence Simplification via Large Language Models"

    def test_a_doi_walks_openalex_then_semanticscholar_then_crossref(self):
        asked: list[str] = []
        client = answering(
            {
                "api.openalex.org": 404,
                "api.semanticscholar.org": 404,
                "api.crossref.org": 200,
            },
            asked,
            {"message": {"DOI": "10.1/a", "title": ["Found Late"]}},
        )
        found = citing.cite("10.1/a", None, client)
        assert asked == [
            "api.openalex.org",
            "api.semanticscholar.org",
            "api.crossref.org",
        ]
        assert (found.source, found.key, found.title) == (
            "crossref",
            None,
            "Found Late",
        )
        assert len(found.retrieved) == 10

    def test_an_arxiv_id_asks_arxiv_alone(self):
        asked: list[str] = []

        def empty_feed(request: httpx.Request) -> httpx.Response:
            asked.append(request.url.host)
            return httpx.Response(200, content=EMPTY_FEED)

        client = httpx.Client(transport=httpx.MockTransport(empty_feed))
        with pytest.raises(CommandError, match=r"no record for 2401\.00001 in arxiv"):
            citing.cite("2401.00001", None, client)
        assert asked == ["export.arxiv.org"]

    def test_a_corpus_miss_falls_through_with_a_signal(self, corpus, capsys):
        asked: list[str] = []
        client = answering(
            {
                "api.openalex.org": 404,
                "api.semanticscholar.org": 404,
                "api.crossref.org": 404,
            },
            asked,
        )
        with pytest.raises(CommandError, match="no record"):
            citing.cite("10.9/elsewhere", read_shelf(corpus), client)
        assert "lacks 10.9/elsewhere" in capsys.readouterr().err

    def test_a_miss_beside_an_upstream_failure_is_worth_a_retry(self):
        asked: list[str] = []
        client = answering(
            {
                "api.openalex.org": 503,
                "api.semanticscholar.org": 404,
                "api.crossref.org": 404,
            },
            asked,
        )
        with pytest.raises(UpstreamError, match="openalex"):
            citing.cite("10.1/a", None, client)
        assert "api.crossref.org" in asked, "a failed index does not stop the walk"

    @pytest.mark.parametrize("ref", ["not an id", "title:some paper"])
    def test_no_identifier_and_no_corpus_hit_is_a_fix(self, ref):
        with pytest.raises(CommandError, match="no DOI or arXiv id"):
            citing.cite(ref, None, refusing())


class TestWiring:
    def built(self, attached=None) -> Parser:
        parser = Parser()
        wire_cite(parser.add_subparsers(dest="command", required=True), "t", attached)
        return parser

    def test_cite_emits_one_citation_from_a_named_corpus(self, corpus, capsys):
        code = run_cli(
            self.built(), ["cite", "2302.11957", "--corpus", str(corpus.parent)]
        )
        assert code == 0
        document = json.loads(capsys.readouterr().out)
        assert document["key"] == "doi:10.48550/arxiv.2302.11957"
        assert document["source"] == "controlled-language-abc"

    def test_a_session_reads_its_attached_corpus(self, corpus, capsys):
        parser = self.built(lambda session: corpus if session == "mine" else None)
        assert (
            run_cli(
                parser,
                ["cite", "doi:10.1109/cei66465.2025.11398497", "--session", "mine"],
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["year"] == 2025

    def test_session_is_offered_only_where_links_exist(self, capsys):
        assert run_cli(self.built(), ["cite", "x", "--session", "s"]) == 1
        assert "unrecognized" in capsys.readouterr().err

    def test_corpus_and_session_are_one_choice(self, corpus, capsys):
        parser = self.built(lambda session: corpus)
        argv = ["cite", "x", "--corpus", str(corpus.parent), "--session", "s"]
        assert run_cli(parser, argv) == 1
        assert "not allowed" in capsys.readouterr().err


def test_the_pipe_is_never_read(monkeypatch, corpus, capsys):
    """REF is configuration in argv; cite owns no content slot."""
    monkeypatch.setattr("sys.stdin", io.StringIO("ignored"))
    parser = Parser()
    wire_cite(parser.add_subparsers(dest="command", required=True), "t")
    assert run_cli(parser, ["cite", "2302.11957", "--corpus", str(corpus.parent)]) == 0
