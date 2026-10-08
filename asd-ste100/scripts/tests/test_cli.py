"""The command surface end to end over the miniature release."""

from __future__ import annotations

import json

import pytest

from btm_asd_ste100 import cli


@pytest.fixture
def served(cache, monkeypatch, make_release, make_client):
    files = make_release()
    monkeypatch.setattr(cli, "client_for", lambda *_a, **_k: make_client(files))
    return files


def run(argv, capsys):
    code = cli.main(argv)
    out = capsys.readouterr()
    return code, (json.loads(out.out) if out.out else None), out.err


class TestCheck:
    def test_an_empty_cache_fetches_first_and_says_so(self, served, capsys):
        code, report, err = run(["check", "--text", "Remove the test."], capsys)
        assert code == 0 and report["ok"] and report["version"] == "v0.1.0"
        assert "fetching it first" in err

    def test_the_allow_file_declares_terms(self, served, tmp_path, capsys):
        allow = tmp_path / "terms.txt"
        allow.write_text("pump\n", encoding="utf-8")
        argv = ["check", "--text", "Remove the pump.", "--allow:file", str(allow)]
        code, report, _ = run(argv, capsys)
        assert code == 0 and report["ok"] and report["allowed"] == 2

    def test_an_empty_text_is_exit_one(self, served, capsys):
        code, _, err = run(["check", "--text", "  "], capsys)
        assert code == 1 and "empty" in err

    def test_a_bad_mode_is_exit_one(self, served, capsys):
        code, _, _ = run(["check", "--text", "x", "--mode", "poem"], capsys)
        assert code == 1

    def test_no_release_is_exit_two_naming_the_version(
        self, cache, monkeypatch, make_client, capsys
    ):
        monkeypatch.setattr(cli, "client_for", lambda *_a, **_k: make_client({}))
        code, _, err = run(["check", "--text", "Remove the test."], capsys)
        assert code == 2 and "ste-tax v0.1.0" in err


class TestLookup:
    def test_an_unapproved_word_comes_with_its_alternatives(self, served, capsys):
        code, doc, _ = run(["lookup", "Ensure"], capsys)
        (entry,) = doc["entries"]
        assert code == 0 and entry["alternatives"] == ["make sure (v)"]

    def test_a_form_finds_its_headword(self, served, capsys):
        _, doc, _ = run(["lookup", "removed"], capsys)
        assert [e["word"] for e in doc["entries"]] == ["REMOVE"]

    def test_an_absent_word_says_what_to_do(self, served, capsys):
        _, doc, _ = run(["lookup", "frobnicate"], capsys)
        assert doc["entries"] == [] and "technical" in doc["next"]


class TestFetchAndClean:
    def test_fetch_then_clean_reports_the_bytes(self, served, capsys):
        code, doc, _ = run(["fetch"], capsys)
        assert code == 0 and len(doc["artifacts"]) == 3
        code, receipt, _ = run(["clean"], capsys)
        assert code == 0 and receipt["bytes_freed"] > 0
        _, again, _ = run(["clean", "--all"], capsys)
        assert again == {"removed": None, "bytes_freed": 0}
