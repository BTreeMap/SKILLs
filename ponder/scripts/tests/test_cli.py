"""The command surface end to end, against an isolated state root."""

from __future__ import annotations

import json

import pytest

from btm_ponder.cli import main


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test owns its own sessions root, so none can see another's."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return tmp_path


def run(argv, capsys, stdin: str | None = None, monkeypatch=None):
    """Run one command and return (exit code, parsed stdout, stderr)."""
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(stdin))
    code = main(argv)
    captured = capsys.readouterr()
    document = json.loads(captured.out) if captured.out.strip() else None
    return code, document, captured.err


def opened(capsys) -> str:
    code, document, _ = run(["init", "rent length", "--question", "q"], capsys)
    assert code == 0
    return document["session"]


class TestOpen:
    def test_open_with_a_question_creates_and_echoes_the_session(self, capsys):
        code, document, _ = run(["init", "rent length", "--question", "why"], capsys)
        assert code == 0
        assert document["session"].startswith("rent-length-")
        assert document["question"] == "why"

    def test_reopening_by_full_id_orients_without_a_signal(self, capsys):
        session = opened(capsys)
        code, document, err = run(["status", session], capsys)
        assert code == 0
        assert document["counts"] == {}
        assert "recovered" not in err

    def test_a_keyword_subset_recovers_and_says_so(self, capsys):
        session = opened(capsys)
        code, document, err = run(["status", "rent"], capsys)
        assert code == 0
        assert document["session"] == session
        assert "recovered session" in err

    def test_opening_an_unknown_session_without_a_question_fails(self, capsys):
        code, _, err = run(["status", "absent thing"], capsys)
        assert code == 1
        assert "run init first" in err

    def test_an_off_band_name_advises(self, capsys):
        _, _, err = run(["init", "solo", "--question", "q"], capsys)
        assert "two or three keywords" in err


class TestNoteAndCheck:
    def batch(self) -> str:
        return json.dumps(
            {
                "leaves": [{"kw": ["rent", "length"], "q": "what does Rent guarantee"}],
                "sources": [
                    {
                        "kw": ["bcl", "rent"],
                        "leaf": "rent length",
                        "cls": "constitutive",
                        "title": "BCL source",
                    }
                ],
                "closes": [
                    {"leaf": "rent length", "state": "retrieved", "sources": ["bcl"]}
                ],
                "sweeps": [
                    {"checked": "rivals", "candidates": ["folk"], "survivors": []}
                ],
                "checkpoints": [{"label": "round-1", "searches": 4}],
            }
        )

    def test_a_full_round_records_and_counts(self, capsys, monkeypatch):
        session = opened(capsys)
        code, document, _ = run(
            ["note", session], capsys, stdin=self.batch(), monkeypatch=monkeypatch
        )
        assert code == 0
        assert document["counts"] == {"retrieved": 1}
        assert document["open"] == []

    def test_check_derives_the_scaffold_from_the_ledger(self, capsys, monkeypatch):
        session = opened(capsys)
        run(["note", session], capsys, stdin=self.batch(), monkeypatch=monkeypatch)
        code, document, _ = run(["check", session], capsys)
        assert code == 0
        assert document["sections"] == ["answer", "rival", "sources"]
        assert document["violations"] == []
        assert document["markers"]["S1"]["title"] == "BCL source"
        assert document["scaffold"]["answer"][0]["markers"] == ["S1"]

    def test_check_on_an_unswept_session_reports_the_violation(
        self, capsys, monkeypatch
    ):
        session = opened(capsys)
        batch = json.dumps({"leaves": [{"kw": ["a", "b"], "q": "q"}]})
        run(["note", session], capsys, stdin=batch, monkeypatch=monkeypatch)
        code, document, err = run(["check", session], capsys)
        assert code == 0  # advisory: violations never block the command
        assert any("no sweep recorded" in line for line in document["violations"])
        assert any("open leaf blocks draft" in line for line in document["violations"])
        assert "signal:" in err

    def test_an_empty_note_body_is_refused(self, capsys, monkeypatch):
        session = opened(capsys)
        code, _, err = run(
            ["note", session], capsys, stdin="  ", monkeypatch=monkeypatch
        )
        assert code == 1
        assert "read from stdin or --file" in err

    def test_a_rejected_batch_appends_nothing(self, capsys, monkeypatch):
        session = opened(capsys)
        bad = json.dumps({"leaves": [{"kw": ["a", "b"], "q": ""}]})
        code, document, _ = run(
            ["note", session], capsys, stdin=bad, monkeypatch=monkeypatch
        )
        assert code == 1
        assert document["unchanged"] == "ledger"
        _, document, _ = run(["status", session], capsys)
        assert document["counts"] == {}

    def test_a_rejection_lists_every_problem_at_once(self, capsys, monkeypatch):
        session = opened(capsys)
        bad = json.dumps(
            {
                "leaves": [{"kw": ["a", "b"], "q": ""}],
                "sweeps": [{"checked": "x", "candidates": ["c"], "survivors": [9]}],
            }
        )
        code, document, _ = run(
            ["note", session], capsys, stdin=bad, monkeypatch=monkeypatch
        )
        assert code == 1
        wheres = {problem["where"] for problem in document["rejected"]}
        assert {"leaves[0]", "sweeps[0].survivors[0]"} <= wheres

    def test_note_reads_a_batch_file(self, capsys, tmp_path, monkeypatch):
        session = opened(capsys)
        batch_file = tmp_path / "batch.json"
        batch_file.write_text(self.batch(), encoding="utf-8")
        code, document, _ = run(["note", session, "--file", str(batch_file)], capsys)
        assert code == 0
        assert document["admitted"]["add_source"] == 1

    def test_invalid_json_is_a_located_rejection(self, capsys, monkeypatch):
        session = opened(capsys)
        code, document, _ = run(
            ["note", session], capsys, stdin="{nope", monkeypatch=monkeypatch
        )
        assert code == 1
        assert "valid JSON" in document["rejected"][0]["fix"]


class TestStatusAndSchema:
    def test_status_reports_the_brief_view(self, capsys, monkeypatch):
        session = opened(capsys)
        batch = json.dumps(
            {
                "leaves": [{"kw": ["a", "b"], "q": "still open"}],
                "sources": [
                    {"kw": ["s", "one"], "leaf": "a b", "cls": "reported", "title": "t"}
                ],
            }
        )
        run(["note", session], capsys, stdin=batch, monkeypatch=monkeypatch)
        code, document, _ = run(["status", session], capsys)
        assert code == 0
        assert document["open"] == [
            {"id": document["open"][0]["id"], "q": "still open", "sources": 1}
        ]
        assert document["swept"] is False

    def test_schema_prints_the_batch_shape(self, capsys):
        code, document, _ = run(["schema"], capsys)
        assert code == 0
        assert "survivors" in document["note_batch"]["sweeps"]


class TestInformalMode:
    def test_informal_demotes_draft_blockers_to_advisories(self, capsys, monkeypatch):
        code, document, _ = run(
            ["init", "loose idea", "--question", "q", "--mode", "informal"], capsys
        )
        session = document["session"]
        batch = json.dumps({"leaves": [{"kw": ["a", "b"], "q": "q"}]})
        run(["note", session], capsys, stdin=batch, monkeypatch=monkeypatch)
        code, document, _ = run(["check", session], capsys)
        assert code == 0
        assert document["violations"] == []
        assert any("open leaf" in line for line in document["advisories"])
        assert any("no sweep" in line for line in document["advisories"])


class TestPad:
    def test_jot_and_recall_round_trip(self, capsys):
        session = opened(capsys)
        code, receipt, _ = run(["jot", session, '{"kind": "hunch", "n": 1}'], capsys)
        assert code == 0
        assert receipt["jotted"] == "j1"
        code, view, _ = run(["recall", session, "--kind", "hunch"], capsys)
        assert code == 0
        assert view["entries"][0]["body"] == {"kind": "hunch", "n": 1}

    def test_prose_is_stored_as_text_with_an_advisory(self, capsys):
        session = opened(capsys)
        code, _, err = run(["jot", session, "plain prose"], capsys)
        assert code == 0
        assert "not a JSON object" in err
        _, view, _ = run(["recall", session], capsys)
        assert view["entries"][0]["body"] == {"text": "plain prose"}

    def test_jot_needs_an_existing_session(self, capsys):
        code, _, err = run(["jot", "absent thing", "{}"], capsys)
        assert code == 1
        assert "no session" in err


class TestClean:
    def test_bare_clean_lists_sessions_and_the_next_step(self, capsys):
        opened(capsys)
        code, document, _ = run(["clean"], capsys)
        assert code == 0
        assert len(document["sessions"]) == 1
        assert "next" in document

    def test_clean_removes_one_session_and_reports_bytes(self, capsys):
        session = opened(capsys)
        code, document, _ = run(["clean", session], capsys)
        assert code == 0
        assert document["removed"].endswith(session)
        assert document["bytes_freed"] >= 0

    def test_clean_all_empties_the_root(self, capsys):
        opened(capsys)
        code, _, _ = run(["clean", "--all"], capsys)
        assert code == 0
        _, document, _ = run(["clean"], capsys)
        assert document["sessions"] == []

    def test_a_session_and_all_together_are_refused(self, capsys):
        session = opened(capsys)
        code, _, err = run(["clean", session, "--all"], capsys)
        assert code == 1
        assert "one of the two" in err

    def test_a_directory_without_a_ledger_is_never_removed(self, capsys, tmp_path):
        stray = tmp_path / "not-a-session"
        stray.mkdir()
        code, _, err = run(["clean", str(stray)], capsys)
        assert code == 1
        assert "refusing to remove" in err
        assert stray.exists()
