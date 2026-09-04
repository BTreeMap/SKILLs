"""The command surface: one document out, the cache in between."""

from __future__ import annotations

import json

import pytest
from btm_search_web import cache, cli, sources
from btm_search_web.records import Result


@pytest.fixture(autouse=True)
def temp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path / "cache")


def run(argv, capsys):
    code = cli.main(argv)
    out = capsys.readouterr()
    return code, json.loads(out.out), out.err


class TestVerbs:
    def test_a_query_returns_the_one_shape(self, capsys, monkeypatch):
        monkeypatch.setattr(
            sources, "web", lambda query, limit: [Result(title="T", source="web")]
        )
        code, document, _ = run(["web", "chaos"], capsys)
        assert code == 0
        assert document["verb"] == "web" and document["count"] == 1
        assert document["results"][0]["title"] == "T"

    def test_an_empty_result_names_the_next_move(self, capsys, monkeypatch):
        monkeypatch.setattr(sources, "wiki", lambda query, limit: [])
        _, document, _ = run(["wiki", "zzz"], capsys)
        assert document["count"] == 0 and "widen" in document["next"]

    def test_the_second_identical_query_costs_no_request(self, capsys, monkeypatch):
        calls = []

        def once(query, limit):
            calls.append(query)
            return [Result(title="T", source="web")]

        monkeypatch.setattr(sources, "web", once)
        run(["web", "chaos"], capsys)
        _, document, err = run(["web", "chaos"], capsys)
        assert calls == ["chaos"]
        assert document["count"] == 1 and "cached" in err

    def test_a_different_limit_is_a_different_query(self, capsys, monkeypatch):
        calls = []
        monkeypatch.setattr(
            sources,
            "web",
            lambda query, limit: calls.append(limit) or [Result(title="T", source="w")],
        )
        run(["web", "chaos", "--limit", "3"], capsys)
        run(["web", "chaos", "--limit", "5"], capsys)
        assert calls == [3, 5]


class TestClean:
    def test_clean_reports_what_it_freed(self, capsys, monkeypatch):
        monkeypatch.setattr(
            sources, "web", lambda query, limit: [Result(title="T", source="web")]
        )
        run(["web", "chaos"], capsys)
        _, document, _ = run(["clean"], capsys)
        assert document["bytes_freed"] > 0
        assert not cache.cache_dir().exists()

    def test_clean_on_an_empty_cache_is_not_a_failure(self, capsys):
        code, document, _ = run(["clean"], capsys)
        assert code == 0 and document["bytes_freed"] == 0
