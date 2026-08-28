"""Channel contract: stdout carries the document, stderr carries advisories."""

from __future__ import annotations

import json

from btm_corekit import emit, signal


class TestChannels:
    def test_emit_prints_one_json_document_to_stdout(self, capsys):
        emit({"a": 1})
        out, err = capsys.readouterr()
        assert json.loads(out) == {"a": 1}
        assert err == ""

    def test_signal_prints_a_prefixed_line_to_stderr(self, capsys):
        signal("watch this")
        out, err = capsys.readouterr()
        assert out == ""
        assert err == "signal: watch this\n"
