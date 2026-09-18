"""The command surface: one document out, the cache in between."""

from __future__ import annotations

import json
import tempfile

import pytest
from btm_search_web import cli, sources
from btm_search_web.constants import MAX_RESULTS
from btm_search_web.records import Result

from btm_corekit import cache_dir


@pytest.fixture(autouse=True)
def temp_cache(tmp_path, monkeypatch):
    """The cache lives in temp space, so moving temp space moves the cache."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return cache_dir("search-web")


def run(argv, capsys):
    code = cli.main(argv)
    out = capsys.readouterr()
    return code, json.loads(out.out), out.err


class TestVerbs:
    def test_a_query_returns_the_one_shape(self, capsys, monkeypatch):
        monkeypatch.setattr(
            sources, "web", lambda query, limit: [Result(title="T", source="web")]
        )
        code, document, _ = run(["web", "--query", "chaos"], capsys)
        assert code == 0
        assert document["verb"] == "web" and document["count"] == 1
        assert document["results"][0]["title"] == "T"

    def test_an_empty_result_names_the_next_move(self, capsys, monkeypatch):
        monkeypatch.setattr(sources, "wiki", lambda query, limit: [])
        _, document, _ = run(["wiki", "--query", "zzz"], capsys)
        assert document["count"] == 0 and "widen" in document["next"]

    def test_the_second_identical_query_costs_no_request(self, capsys, monkeypatch):
        calls = []

        def once(query, limit):
            calls.append(query)
            return [Result(title="T", source="web")]

        monkeypatch.setattr(sources, "web", once)
        run(["web", "--query", "chaos"], capsys)
        _, document, err = run(["web", "--query", "chaos"], capsys)
        assert calls == ["chaos"]
        assert document["count"] == 1 and "cached" in err

    def test_a_different_limit_is_a_different_query(self, capsys, monkeypatch):
        calls = []
        monkeypatch.setattr(
            sources,
            "web",
            lambda query, limit: calls.append(limit) or [Result(title="T", source="w")],
        )
        run(["web", "--query", "chaos", "--limit", "3"], capsys)
        run(["web", "--query", "chaos", "--limit", "5"], capsys)
        assert calls == [3, 5]


class TestFetch:
    def test_the_second_fetch_of_one_url_costs_no_request(self, capsys, monkeypatch):
        calls = []

        def once(url):
            calls.append(url)
            return "the readable body"

        monkeypatch.setattr(sources, "fetch", once)
        _, first, _ = run(["fetch", "https://x.org/a"], capsys)
        _, second, err = run(["fetch", "https://x.org/a"], capsys)
        assert calls == ["https://x.org/a"]
        assert second == first and second["chars"] == len("the readable body")
        assert "cached" in err

    def test_a_different_url_is_a_different_page(self, capsys, monkeypatch):
        monkeypatch.setattr(sources, "fetch", lambda url: url)
        run(["fetch", "https://x.org/a"], capsys)
        _, document, err = run(["fetch", "https://x.org/b"], capsys)
        assert document["text"] == "https://x.org/b" and "cached" not in err


class TestLimit:
    def test_a_limit_below_one_is_rejected_before_any_request(
        self, capsys, monkeypatch
    ):
        """Nothing is worth asking for zero rows, so argparse refuses the line
        rather than letting a clamp invent a number."""
        monkeypatch.setattr(
            sources, "web", lambda query, limit: pytest.fail("a request went out")
        )
        assert cli.main(["web", "--query", "chaos", "--limit", "0"]) == 1
        assert "1 or more" in capsys.readouterr().err

    def test_a_limit_above_the_cap_is_clamped_and_says_so(self, capsys, monkeypatch):
        """A silent clamp is a lie about what ran: the signal and the record
        both name the number actually used."""
        asked: list[int] = []
        monkeypatch.setattr(
            sources, "web", lambda query, limit: asked.append(limit) or []
        )
        _, document, err = run(["web", "--query", "c", "--limit", "500"], capsys)
        assert asked == [MAX_RESULTS]
        assert document["limit"] == MAX_RESULTS
        assert f"capped to {MAX_RESULTS}" in err

    def test_a_limit_under_the_cap_passes_through_unsignalled(
        self, capsys, monkeypatch
    ):
        monkeypatch.setattr(sources, "wiki", lambda query, limit: [])
        _, document, err = run(["wiki", "--query", "c", "--limit", "3"], capsys)
        assert document["limit"] == 3 and "capped" not in err


class TestSalvage:
    @pytest.mark.parametrize("corruption", ["{not json", '{"rows": 3}'])
    def test_an_undecodable_slot_is_dropped_and_recomputed(
        self, capsys, monkeypatch, temp_cache, corruption
    ):
        """A cache slot is regenerable, so one that will not decode costs the
        request that filled it and never the command."""
        calls: list[str] = []
        monkeypatch.setattr(
            sources,
            "web",
            lambda query, limit: (
                calls.append(query) or [Result(title="T", source="web")]
            ),
        )
        run(["web", "--query", "chaos"], capsys)
        [slot] = list(temp_cache.iterdir())
        slot.write_text(corruption, encoding="utf-8")
        _, document, err = run(["web", "--query", "chaos"], capsys)
        assert calls == ["chaos", "chaos"]
        assert document["count"] == 1
        assert "unreadable cache slot" in err


class TestClean:
    def test_clean_reports_what_it_freed(self, capsys, monkeypatch, temp_cache):
        monkeypatch.setattr(
            sources, "web", lambda query, limit: [Result(title="T", source="web")]
        )
        run(["web", "--query", "chaos"], capsys)
        _, document, _ = run(["clean"], capsys)
        assert document["removed"] == str(temp_cache)
        assert document["bytes_freed"] > 0
        assert not temp_cache.exists()

    def test_clean_on_an_empty_cache_is_not_a_failure(self, capsys):
        code, document, _ = run(["clean"], capsys)
        assert code == 0
        assert document == {"removed": None, "bytes_freed": 0}
