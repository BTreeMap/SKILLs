"""Search and snowball over the registry, against mocked transports."""

from __future__ import annotations

import io
import json
import sys

import httpx
import pytest

from btm_corekit import ByArxiv, ByDoi, ByNative, CommandError, Work
from btm_corekit.indexes import arxiv, semanticscholar
from btm_lit_review.cli import build_parser, main
from btm_lit_review.corpus import gather, sources
from btm_lit_review.corpus.gather import resolve_ref
from btm_lit_review.corpus.paper import paper_from
from btm_lit_review.session import Session, load_papers, save_papers


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    monkeypatch.delenv("BTM_SEMANTICSCHOLAR_KEY", raising=False)
    monkeypatch.delenv("BTM_FIRECRAWL_KEY", raising=False)
    monkeypatch.setenv("BTM_OPENALEX_KEY", "k")
    paces = (arxiv.PACE, semanticscholar.KEYED_PACE, semanticscholar.KEYLESS_PACE)
    for pace in paces:
        monkeypatch.setattr(pace, "interval", 0.0)


def run(argv, capsys, stdin=None):
    original = sys.stdin
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    try:
        code = main(argv)
    finally:
        sys.stdin = original
    captured = capsys.readouterr()
    document = json.loads(captured.out) if captured.out.strip() else None
    return code, document, captured.err


def work(**fields) -> Work:
    bare = dict.fromkeys(
        (
            "title",
            "year",
            "venue",
            "doi",
            "arxiv_id",
            "openalex_id",
            "cited_by",
            "abstract",
            "pdf_url",
            "landing_url",
            "published",
        )
    )
    return Work(**{**bare, "authors": (), **fields})


@pytest.fixture
def upstream(monkeypatch):
    """Answer every request with `body`, recording what went out."""
    seen: list[httpx.Request] = []

    def serve(body, status=200):
        def answer(request):
            seen.append(request)
            payload = body(request) if callable(body) else body
            raw = payload if isinstance(payload, str) else json.dumps(payload)
            return httpx.Response(status, content=raw.encode())

        client = httpx.Client(transport=httpx.MockTransport(answer))
        monkeypatch.setattr(sources, "client", lambda: client)
        monkeypatch.setattr(gather, "client", lambda: client)
        return seen

    return serve


@pytest.fixture
def session(tmp_path, capsys):
    root = tmp_path / "review"
    run(["init", str(root)], capsys, stdin='{"question": "q"}')
    built = Session(root)
    protocol = json.loads(built.protocol_path.read_text())
    protocol["criteria"] = {"include": ["on topic"], "exclude": ["off topic"]}
    built.protocol_path.write_text(json.dumps(protocol))
    seed = paper_from(work(title="Seed", doi="10.1/a", openalex_id="W1"))
    save_papers(built, {seed.key: seed})
    return built


def log(session: Session) -> list[dict]:
    return [json.loads(line) for line in session.log_path.read_text().splitlines()]


FIRECRAWL = {
    "success": True,
    "results": [
        {
            "paperId": "8319239866974784291",
            "primaryId": "arxiv:1706.03762",
            "title": "Attention Is All You Need",
            "abstract": "Transformers.",
            "score": 0.98,
        }
    ],
}


class TestSearch:
    def test_any_registered_index_is_a_source(self):
        args = build_parser().parse_args(["search", "s", "--source", "firecrawl"])
        assert args.source == "firecrawl"

    def test_an_index_with_no_total_logs_null_and_no_truncation(
        self, session, capsys, upstream
    ):
        seen = upstream(FIRECRAWL)
        code, document, err = run(
            ["search", str(session.root), "--source", "firecrawl", "--limit", "5"],
            capsys,
            stdin='{"query": "attention"}',
        )
        assert code == 0
        assert seen[0].url.params["k"] == "5"
        assert document["total_matches"] is None
        assert document["truncated"] is False and "matches upstream" not in err
        assert "arxiv:1706.03762" in load_papers(session)
        assert log(session)[0]["source"] == "firecrawl"

    def test_the_window_disclaimer_comes_from_the_kernel(
        self, session, capsys, upstream
    ):
        upstream('<feed xmlns="http://www.w3.org/2005/Atom"></feed>')
        _, _, err = run(
            ["search", str(session.root), "--source", "arxiv", "--from-year", "2020"],
            capsys,
            stdin='{"query": "ti:x"}',
        )
        assert "arxiv ignores year bounds" in err

    def test_a_known_total_above_the_fetch_still_signals(
        self, session, capsys, upstream
    ):
        upstream({"meta": {"count": 90}, "results": [{"id": "W5", "title": "T"}]})
        _, document, err = run(
            ["search", str(session.root), "--source", "openalex"],
            capsys,
            stdin='{"query": "q"}',
        )
        assert document["total_matches"] == 90 and document["truncated"] is True
        assert "90 matches upstream" in err


class TestResolveRef:
    def test_openalex_takes_the_native_id_the_paper_carries(self):
        seed = paper_from(work(title="S", doi="10.1/a", openalex_id="W1"))
        assert resolve_ref({seed.key: seed}, "10.1/a", "openalex") == (
            "doi:10.1/a",
            ByNative("W1"),
        )

    def test_another_index_falls_back_to_the_doi(self):
        seed = paper_from(work(title="S", doi="10.1/a", openalex_id="W1"))
        assert resolve_ref({seed.key: seed}, seed.key, "semanticscholar")[1] == (
            ByDoi("10.1/a")
        )

    def test_then_to_the_arxiv_id(self):
        seed = paper_from(work(title="S", arxiv_id="1706.03762"))
        assert resolve_ref({seed.key: seed}, "arXiv:1706.03762", "openalex") == (
            "arxiv:1706.03762",
            ByArxiv("1706.03762"),
        )

    def test_a_paper_with_no_identifier_is_refused(self):
        seed = paper_from(work(title="Only a title"))
        with pytest.raises(CommandError, match="no semanticscholar id, DOI, or arXiv"):
            resolve_ref({seed.key: seed}, seed.key, "semanticscholar")

    def test_a_token_matching_no_paper_is_refused(self):
        with pytest.raises(CommandError, match="search for it first"):
            resolve_ref({}, "10.9/x", "openalex")


class TestSnowball:
    def test_only_an_index_with_a_graph_is_a_choice(self):
        parser = build_parser()
        assert (
            parser.parse_args(
                ["snowball", "s", "--seed", "k", "--direction", "forward"]
            ).source
            == "openalex"
        )
        with pytest.raises(CommandError, match="invalid choice"):
            parser.parse_args(
                [
                    "snowball",
                    "s",
                    "--seed",
                    "k",
                    "--direction",
                    "forward",
                    "--source",
                    "crossref",
                ]
            )

    def test_semanticscholar_walks_references_by_doi(self, session, capsys, upstream):
        seen = upstream(
            {
                "data": [
                    {
                        "citedPaper": {
                            "paperId": "p2",
                            "title": "Cited",
                            "externalIds": {"DOI": "10.1/b"},
                        }
                    }
                ]
            }
        )
        code, document, _ = run(
            [
                "snowball",
                str(session.root),
                "--seed",
                "doi:10.1/a",
                "--direction",
                "backward",
                "--source",
                "semanticscholar",
            ],
            capsys,
        )
        assert code == 0
        assert seen[0].url.path == "/graph/v1/paper/DOI:10.1/a/references"
        assert document["new"] == 1 and document["total_matches"] is None
        assert log(session)[0]["source"] == "semanticscholar"
        assert "doi:10.1/b" in load_papers(session)

    def test_openalex_citations_start_from_the_native_id(
        self, session, capsys, upstream
    ):
        seen = upstream({"meta": {"count": 1}, "results": [{"id": "W7"}]})
        run(
            [
                "snowball",
                str(session.root),
                "--seed",
                "doi:10.1/a",
                "--direction",
                "forward",
            ],
            capsys,
        )
        assert len(seen) == 1, "the native id needs no lookup"
        assert seen[0].url.params["filter"] == "cites:W1"

    def test_an_empty_reference_list_is_named_a_metadata_gap(
        self, session, capsys, upstream
    ):
        upstream({"id": "W1", "referenced_works": []})
        _, document, err = run(
            [
                "snowball",
                str(session.root),
                "--seed",
                "doi:10.1/a",
                "--direction",
                "backward",
            ],
            capsys,
        )
        assert document["fetched"] == 0
        assert "openalex lists no references for doi:10.1/a" in err
