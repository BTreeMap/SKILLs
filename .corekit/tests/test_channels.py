"""Channel contract: stdout carries the document, stderr carries advisories."""

from __future__ import annotations

import json
import sys

from btm_corekit import emit, signal

DOCUMENT = {"ok": True, "findings": [{"rule": "length", "line": 3}]}


class TestChannels:
    def test_emit_prints_one_json_document_to_stdout(self, capsys):
        emit({"a": 1})
        out, err = capsys.readouterr()
        assert json.loads(out) == {"a": 1}
        assert err == ""

    def test_a_pipe_gets_one_line(self, capsys):
        emit(DOCUMENT)
        out = capsys.readouterr().out
        assert out.count("\n") == 1
        assert json.loads(out) == DOCUMENT
        assert '"ok": true' in out

    def test_a_terminal_gets_the_indented_form(self, capsys, monkeypatch):
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
        emit(DOCUMENT)
        out = capsys.readouterr().out
        assert out == json.dumps(DOCUMENT, indent=2) + "\n"

    def test_signal_prints_a_prefixed_line_to_stderr(self, capsys):
        signal("watch this")
        out, err = capsys.readouterr()
        assert out == ""
        assert err == "signal: watch this\n"
