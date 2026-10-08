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
        assert code == 0 and report["ok"] and report["version"] == "v0.1.1"
        assert "fetching it first" in err

    def test_the_allow_file_declares_terms(self, served, tmp_path, capsys):
        allow = tmp_path / "terms.txt"
        allow.write_text("pump\n", encoding="utf-8")
        argv = ["check", "--text", "Remove the pump.", "--allow:file", str(allow)]
        code, report, _ = run(argv, capsys)
        assert code == 0 and report["ok"] and report["allowed"] == 1

    def test_markdown_section_and_lines(self, served, tmp_path, capsys):
        page = tmp_path / "page.md"
        page.write_text("# A\n\nRemove the pump.\n\n# B\n\nRemove it.\n", "utf-8")
        argv = ["check", "--text:file", str(page), "--format", "markdown"]
        _, report, _ = run([*argv, "--section", "A"], capsys)
        (f,) = report["findings"]
        assert (f["token"], f["lines"], report["section"]) == ("pump", [3], "A")

    def test_a_section_without_markdown_is_exit_one(self, served, capsys):
        argv = ["check", "--text", "Remove it.", "--section", "A"]
        code, _, err = run(argv, capsys)
        assert code == 1 and "--format markdown" in err

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
        assert code == 2 and "ste-tax v0.1.1" in err


class TestLookup:
    def test_an_unapproved_word_comes_with_its_alternatives(self, served, capsys):
        code, doc, _ = run(["lookup", "Ensure"], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        assert code == 0 and entry["alternatives"] == ["make sure (v)"]

    def test_each_alternative_sits_beside_its_example(self, served, capsys):
        _, doc, _ = run(["lookup", "return"], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        (choice,) = entry["choices"]
        assert choice == {
            "use": "do (v)",
            "ste": "DO THE TEST AGAIN.",
            "not_ste": "Return to the test.",
        }
        assert "ste_example" not in entry

    def test_unpaired_examples_stay_raw(self, served, capsys):
        _, doc, _ = run(["lookup", "ensure"], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        assert "choices" not in entry and entry["ste_example"]

    def test_a_form_finds_its_headword(self, served, capsys):
        _, doc, _ = run(["lookup", "removed"], capsys)
        assert [e["word"] for e in doc["words"][0]["entries"]] == ["REMOVE"]

    def test_several_words_in_one_call(self, served, capsys):
        _, doc, _ = run(["lookup", "removed", "frobnicate"], capsys)
        assert [w["word"] for w in doc["words"]] == ["removed", "frobnicate"]

    def test_an_inflected_unapproved_word_finds_its_headword(self, served, capsys):
        _, doc, _ = run(["lookup", "ensured"], capsys)
        (got,) = doc["words"]
        assert got["headword"] == "ensure" and got["entries"][0]["word"] == "ensure"

    def test_an_absent_word_says_what_to_do(self, served, capsys):
        _, doc, _ = run(["lookup", "frobnicate"], capsys)
        (got,) = doc["words"]
        assert got["entries"] == [] and "technical" in got["next"]


class TestFetchAndClean:
    def test_fetch_then_clean_reports_the_bytes(self, served, capsys):
        code, doc, _ = run(["fetch"], capsys)
        assert code == 0 and len(doc["artifacts"]) == 3
        code, receipt, _ = run(["clean"], capsys)
        assert code == 0 and receipt["bytes_freed"] > 0
        _, again, _ = run(["clean", "--all"], capsys)
        assert again == {"removed": None, "bytes_freed": 0}
