"""The command surface end to end over the miniature release."""

from __future__ import annotations

import json

import pytest

from btm_asd_ste100 import cli
from btm_asd_ste100.records import Entry


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
        assert code == 0 and report["ok"] and report["version"] == "v0.1.2"
        assert "fetching it first" in err

    def test_the_accept_file_declares_terms(self, served, tmp_path, capsys):
        accept = tmp_path / "terms.txt"
        accept.write_text("pump\n", encoding="utf-8")
        argv = ["check", "--text", "Remove the pump.", "--accept:file", str(accept)]
        code, report, _ = run(argv, capsys)
        assert code == 0 and report["ok"] and report["accepted"] == 1

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
        assert code == 2 and "ste-tax v0.1.2" in err


class TestCheckJsonl:
    def test_one_report_per_line_from_one_lexicon_index(
        self, served, monkeypatch, capsys
    ):
        built, index = [], cli.vocabulary
        monkeypatch.setattr(cli, "vocabulary", lambda x: built.append(1) or index(x))
        lines = [
            json.dumps({"id": "a", "text": "Remove the test."}),
            "",
            json.dumps({"text": "Ensure the test."}),
        ]
        code, doc, _ = run(["check", "--jsonl", "--text", "\n".join(lines)], capsys)
        assert code == 0 and built == [1] and doc["version"] == "v0.1.2"
        assert (doc["schema_version"], doc["data"]) == (3, None)
        assert (doc["ok"], doc["texts"], doc["accepted"]) == (False, 2, 0)
        first, second = doc["reports"]
        assert (first["line"], first["id"], first["ok"]) == (1, "a", True)
        assert (second["line"], "id" in second, second["ok"]) == (3, False, False)

    def test_every_bad_line_is_named_before_any_fetch(self, cache, monkeypatch, capsys):
        def offline(*_a, **_k):
            raise AssertionError("a rejected batch must not load a release")

        monkeypatch.setattr(cli, "client_for", offline)
        lines = ['{"text": "x"}', "not json", '{"txt": "y"}', '{"text": " "}']
        code, doc, _ = run(["check", "--jsonl", "--text", "\n".join(lines)], capsys)
        assert code == 1 and doc["unchanged"].startswith("nothing")
        wheres = [r["where"] for r in doc["rejected"]]
        assert wheres == ["line 2", "line 3.text", "line 3.txt", "line 4.text"]

    def test_one_cause_on_many_lines_is_one_fix(self, served, capsys):
        lines = [json.dumps({"text": "Remove it."})] * 2
        argv = ["check", "--jsonl", "--section", "A", "--text", "\n".join(lines)]
        code, doc, _ = run(argv, capsys)
        ((problem,),) = [doc["rejected"]]
        assert code == 1 and problem["where"] == "lines 1, 2"
        assert "--format markdown" in problem["fix"]


class TestFind:
    def test_an_unapproved_word_comes_with_its_alternatives(self, served, capsys):
        code, doc, _ = run(["find", "Ensure"], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        assert code == 0 and entry["alternatives"] == ["make sure (v)"]

    def test_each_alternative_sits_beside_its_example(self, served, capsys):
        _, doc, _ = run(["find", "return"], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        (choice,) = entry["choices"]
        assert choice == {
            "use": "do (v)",
            "ste": "DO THE TEST AGAIN.",
            "not_ste": "Return to the test.",
        }
        assert (entry["ste_example"], entry["nonste_example"]) == (None, None)

    def test_each_qualifier_keeps_its_own_alternatives(self, served, capsys):
        _, doc, _ = run(["find", "few"], capsys)
        entries = doc["words"][0]["entries"]
        got = {e.get("qualifier"): e["alternatives"] for e in entries}
        assert got == {None: ["small number"], "a few": ["do (v)"]}

    def test_unpaired_examples_stay_raw(self, served, capsys):
        _, doc, _ = run(["find", "ensure"], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        assert entry["choices"] == [] and entry["ste_example"]

    def test_every_entry_has_every_key_even_with_no_part_of_speech(
        self, served, capsys
    ):
        _, doc, _ = run(["find", "such as", "ensure", "return", "test"], capsys)
        rows = [e for w in doc["words"] for e in w["entries"]]
        assert len({tuple(e) for e in rows}) == 1, "one key set, one order"
        (phrase,) = doc["words"][0]["entries"]
        assert (phrase["pos"], phrase["qualifier"]) == (None, None)

    def test_a_form_finds_its_headword(self, served, capsys):
        _, doc, _ = run(["find", "removed"], capsys)
        assert [e["word"] for e in doc["words"][0]["entries"]] == ["REMOVE"]

    def test_several_words_in_one_call(self, served, capsys):
        _, doc, _ = run(["find", "removed", "frobnicate"], capsys)
        assert [w["word"] for w in doc["words"]] == ["removed", "frobnicate"]

    def test_an_inflected_unapproved_word_finds_its_headword(self, served, capsys):
        _, doc, _ = run(["find", "ensured"], capsys)
        (got,) = doc["words"]
        assert got["headword"] == "ensure" and got["entries"][0]["word"] == "ensure"

    def test_a_noun_plural_finds_its_approved_noun(self, served, capsys):
        _, doc, _ = run(["find", "tests"], capsys)
        (got,) = doc["words"]
        assert [(e["word"], e["pos"]) for e in got["entries"]] == [("TEST", "n")]
        assert "next" not in got

    def test_a_plural_keeps_the_unapproved_verb_it_inflects(self):
        verb = Entry.model_validate(
            {
                "word": "test",
                "pos": "v",
                "qualifier": None,
                "forms": [],
                "status": {"kind": "unapproved", "alternatives": []},
            }
        )
        noun = Entry.model_validate(
            {
                "word": "TEST",
                "pos": "n",
                "qualifier": None,
                "forms": [],
                "status": {"kind": "approved", "alternatives": []},
            }
        )
        got = cli.find_one("tests", {"test": [verb]}, {}, {"tests": [noun]})
        assert got["headword"] == "test"
        assert [(e["word"], e["pos"]) for e in got["entries"]] == [
            ("test", "v"),
            ("TEST", "n"),
        ]

    def test_an_absent_word_says_what_to_do(self, served, capsys):
        _, doc, _ = run(["find", "frobnicate"], capsys)
        (got,) = doc["words"]
        assert got["entries"] == [] and "technical" in got["next"]


class TestGetAndClean:
    def test_get_then_clean_reports_the_bytes(self, served, capsys):
        code, doc, _ = run(["get"], capsys)
        assert code == 0 and len(doc["artifacts"]) == 3
        code, receipt, _ = run(["clean"], capsys)
        assert code == 0 and receipt["bytes_freed"] > 0
        _, again, _ = run(["clean", "--all"], capsys)
        assert again == {"removed": None, "bytes_freed": 0}


@pytest.fixture
def local(cache, monkeypatch, tmp_path, make_release):
    """A ste-tax checkout's data/ directory, and a client that must not run."""

    def offline(*_a, **_k):
        raise AssertionError("--data must not build an HTTP client")

    monkeypatch.setattr(cli, "client_for", offline)
    root = tmp_path / "ste-tax"
    for path, body in make_release().items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(body)
    return root / "data"


class TestLocalData:
    def test_check_reads_the_directory_and_not_the_cache(self, local, cache, capsys):
        argv = ["check", "--text", "Remove the test.", "--data", str(local)]
        code, report, err = run(argv, capsys)
        assert code == 0 and report["ok"] and report["data"] == str(local)
        assert report["version"] is None and err == ""
        assert not cache.exists(), "a local release fills no cache"

    def test_find_reads_the_directory(self, local, capsys):
        code, doc, _ = run(["find", "ensure", "--data", str(local)], capsys)
        ((entry,),) = [w["entries"] for w in doc["words"]]
        assert code == 0 and entry["alternatives"] == ["make sure (v)"]

    def test_every_origin_gives_one_shape(self, local, served, capsys):
        for argv in (["check", "--text", "Remove it."], ["find", "remove"]):
            _, cached, _ = run(argv, capsys)
            _, read, _ = run([*argv, "--data", str(local)], capsys)
            assert list(cached) == list(read), "same keys in the same order"
            assert (cached["schema_version"], cached["data"]) == (3, None)
            assert (read["schema_version"], read["version"]) == (3, None)

    def test_a_file_off_its_digest_is_exit_one_and_kept(self, local, capsys):
        lexicon = local / "lexicon.json"
        lexicon.write_bytes(lexicon.read_bytes() + b" ")
        code, _, err = run(["find", "ensure", "--data", str(local)], capsys)
        assert code == 1 and "data/lexicon.json differs" in err
        assert lexicon.exists(), "the user owns the directory: nothing deleted"

    def test_every_missing_artifact_is_named_at_once(self, local, capsys):
        (local / "lexicon.json").unlink()
        (local / "rules.json").unlink()
        code, _, err = run(["check", "--text", "x", "--data", str(local)], capsys)
        assert code == 1 and "data/lexicon.json, data/rules.json" in err

    def test_a_directory_without_a_manifest_is_exit_one(self, local, capsys):
        code, _, err = run(["find", "x", "--data", str(local.parent)], capsys)
        assert code == 1 and "no manifest.json" in err

    def test_data_and_version_together_is_exit_one(self, local, capsys):
        argv = ["find", "x", "--data", str(local), "--version", "v0.1.2"]
        code, _, err = run(argv, capsys)
        assert code == 1 and "not allowed with" in err
