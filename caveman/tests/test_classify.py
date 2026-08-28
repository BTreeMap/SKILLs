"""Content assessment: a guess with evidence, never a verdict."""

from __future__ import annotations

from pathlib import Path

import pytest

from btm_caveman.classify import assess
from btm_caveman.model import FileKind
from btm_caveman.sensitive import is_sensitive


def kind(path: Path, text: str | None = None) -> FileKind:
    return assess(path, text).kind


class TestByName:
    @pytest.mark.parametrize(
        "name", ["Dockerfile", "CMakeLists.txt", "a.cs", "module.py"]
    )
    def test_known_code_names_are_code(self, name):
        assert kind(Path(name)) is FileKind.CODE

    def test_markdown_is_prose(self):
        assert kind(Path("notes.md")) is FileKind.NATURAL_LANGUAGE

    @pytest.mark.parametrize("name", ["conf.yaml", "data.csv"])
    def test_config_and_data_share_a_kind(self, name):
        assert kind(Path(name)) is FileKind.CONFIG


class TestByContent:
    def test_a_shebang_marks_code(self):
        assert kind(Path("run"), "#!/bin/sh\necho hi\n") is FileKind.CODE

    def test_go_source_without_a_suffix_is_code(self):
        go = 'package main\n\nfunc main() {\n\tfmt.Println("hi")\n}\n'
        assert kind(Path("main"), go) is FileKind.CODE

    def test_sql_without_a_suffix_is_code(self):
        assert kind(Path("q"), "SELECT id\nFROM t;\n") is FileKind.CODE

    def test_env_assignments_are_config(self):
        assert kind(Path(".env.local"), "A=1\n") is FileKind.CONFIG

    def test_plain_sentences_are_prose(self):
        text = "Buy milk.\nShip release.\n"
        assert kind(Path("TODO"), text) is FileKind.NATURAL_LANGUAGE

    def test_a_bare_json_scalar_is_inconclusive(self):
        assert kind(Path("n"), "42") is FileKind.UNKNOWN

    def test_content_without_prose_evidence_is_inconclusive(self):
        assert kind(Path("x"), "zx9\nq7\n") is FileKind.UNKNOWN


class TestSignals:
    def test_a_clean_prose_guess_carries_no_signal(self):
        assert assess(Path("notes.md"), None).signals == ()

    def test_a_code_guess_carries_its_evidence(self):
        assert assess(Path("a.py"), None).signals

    def test_an_inconclusive_guess_states_its_ratios(self):
        inconclusive = assess(Path("x"), "zx9\nq7\n")
        assert inconclusive.kind is FileKind.UNKNOWN
        assert any("code-like" in signal for signal in inconclusive.signals)


class TestSensitive:
    @pytest.mark.parametrize(
        "path", ["/home/u/.aws/config", "api-key.md", "/home/u/.ssh/config"]
    )
    def test_secret_bearing_paths_are_refused(self, path):
        assert is_sensitive(Path(path))

    def test_an_ordinary_note_is_not_sensitive(self):
        assert not is_sensitive(Path("notes.md"))
