"""The command surface end to end, against an isolated state root."""

from __future__ import annotations

import io
import json
import sys

import pytest

from btm_ponder.cli import main


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test owns its own sessions root, so none can see another's."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return tmp_path


def run(argv, capsys, stdin: str | None = None, monkeypatch=None):
    """Run one command and return (exit code, parsed stdout, stderr).

    stdin is swapped here rather than through monkeypatch so a caller needs no
    fixture: content now reaches most subcommands this way."""
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


def opened(capsys) -> str:
    code, document, _ = run(["init", "rent length"], capsys, stdin='{"question": "q"}')
    assert code == 0
    return document["session"]


class TestOpen:
    def test_open_with_a_question_creates_and_echoes_the_session(self, capsys):
        code, document, _ = run(
            ["init", "rent length"], capsys, stdin='{"question": "why"}'
        )
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
        _, _, err = run(["init", "solo"], capsys, stdin='{"question": "q"}')
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
            ["init", "loose idea", "--mode", "informal"],
            capsys,
            stdin='{"question": "q"}',
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
        code, receipt, _ = run(
            ["jot", session], capsys, stdin='{"kind": "hunch", "n": 1}'
        )
        assert code == 0
        assert receipt["jotted"] == "j1"
        code, view, _ = run(["recall", session, "--kind", "hunch"], capsys)
        assert code == 0
        assert view["entries"][0]["body"] == {"kind": "hunch", "n": 1}

    def test_prose_is_stored_as_text_with_an_advisory(self, capsys):
        session = opened(capsys)
        code, _, err = run(["jot", session], capsys, stdin="plain prose")
        assert code == 0
        assert "not a JSON object" in err
        _, view, _ = run(["recall", session], capsys)
        assert view["entries"][0]["body"] == {"text": "plain prose"}

    def test_jot_needs_an_existing_session(self, capsys):
        code, _, err = run(["jot", "absent thing"], capsys, stdin="{}")
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


def contained(small, big) -> bool:
    """Structural containment: every field of `small` appears in `big` at the
    same path with a contained value, and lists keep their length."""
    if isinstance(small, dict):
        return isinstance(big, dict) and all(
            key in big and contained(value, big[key]) for key, value in small.items()
        )
    if isinstance(small, list):
        return (
            isinstance(big, list)
            and len(small) == len(big)
            and all(contained(a, b) for a, b in zip(small, big, strict=True))
        )
    return bool(small == big)


class TestViewChain:
    """`View` is a chain: each level is a superset of the one before, so a
    caller that asks for more never loses a field, and a field is declared at
    exactly one level."""

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
                        "url": "https://example.org/bcl",
                    }
                ],
                "closes": [
                    {
                        "leaf": "rent length",
                        "state": "retrieved",
                        "sources": ["bcl"],
                        "premise": "Rent guarantees at-least length",
                        "detail": "the exact overload is the other one",
                    }
                ],
                "sweeps": [{"checked": "rivals", "candidates": [], "survivors": []}],
            }
        )

    def noted(self, capsys) -> str:
        """One session with one closed round, reusable across views."""
        session = opened(capsys)
        run(["note", session], capsys, stdin=self.batch())
        return session

    def viewed(self, capsys, session: str, view: str | None = None) -> dict:
        argv = ["check", session] + (["--view", view] if view else [])
        code, document, _ = run(argv, capsys)
        assert code == 0
        return document

    def checked(self, capsys, view: str | None = None) -> dict:
        return self.viewed(capsys, self.noted(capsys), view)

    def test_each_level_is_a_superset_of_the_one_before(self, capsys):
        session = self.noted(capsys)
        plan = set(self.viewed(capsys, session, "plan"))
        draft = set(self.viewed(capsys, session, "draft"))
        full = set(self.viewed(capsys, session, "full"))
        assert plan < draft < full

    def test_a_richer_view_only_ever_adds(self, capsys):
        """The chain law where it bites, and it is structural, not top-level:
        `scaffold` is a shared key whose rows themselves grow. A richer view
        adds fields at some depth and rewrites none, so a caller can trust
        what a cheaper view already told it. Row cardinality is preserved:
        a view projects fields, never filters records."""
        session = self.noted(capsys)
        plan = self.viewed(capsys, session, "plan")
        draft = self.viewed(capsys, session, "draft")
        full = self.viewed(capsys, session, "full")
        assert contained(plan, draft)
        assert contained(draft, full)

    def test_scaffold_rows_grow_the_same_way(self, capsys):
        session = self.noted(capsys)

        def row(view: str) -> set[str]:
            return set(self.viewed(capsys, session, view)["scaffold"]["answer"][0])

        assert row("plan") < row("draft") <= row("full")

    def test_plan_withholds_the_prose_it_was_handed(self, capsys):
        """premise and detail are the agent's own words; echoing them back
        into the window that wrote them is the cost this level removes."""
        document = self.checked(capsys, "plan")
        answer = document["scaffold"]["answer"][0]
        assert "premise" not in answer
        assert "detail" not in answer

    def test_plan_keeps_the_marker_refs_that_carry_the_derivation(self, capsys):
        answer = self.checked(capsys, "plan")["scaffold"]["answer"][0]
        assert answer["markers"] == ["S1"]
        assert answer["stated"] == "plain"

    def test_plan_omits_the_source_table(self, capsys):
        assert "markers" not in self.checked(capsys, "plan")

    def test_draft_is_the_default(self, capsys):
        session = self.noted(capsys)
        assert self.viewed(capsys, session) == self.viewed(capsys, session, "draft")

    def test_draft_carries_the_prose_and_the_table(self, capsys):
        document = self.checked(capsys, "draft")
        assert document["scaffold"]["answer"][0]["premise"].startswith("Rent")
        assert document["markers"]["S1"]["title"] == "BCL source"

    def test_the_marker_table_drops_the_minted_id(self, capsys):
        """A draft cites S1 and renders a title and a url; the ledger's own
        identifier is never read, and 41 of them are 1.9 KB."""
        assert set(self.checked(capsys, "draft")["markers"]["S1"]) == {
            "cls",
            "title",
            "url",
        }

    def test_the_scaffold_is_emitted_before_the_table(self, capsys):
        keys = list(self.checked(capsys, "draft"))
        assert keys.index("scaffold") < keys.index("markers")

    def test_full_adds_the_record_dump(self, capsys):
        assert "leaves" in self.checked(capsys, "full")
        assert "leaves" not in self.checked(capsys, "draft")

    def test_a_note_receipt_withholds_minted_ids_below_draft(self, capsys):
        session = opened(capsys)
        code, receipt, _ = run(
            ["note", session, "--view", "plan"], capsys, stdin=self.batch()
        )
        assert code == 0
        assert "minted" not in receipt
        assert receipt["counts"] == {"retrieved": 1}

    def test_a_note_receipt_carries_minted_ids_by_default(self, capsys):
        session = opened(capsys)
        _, receipt, _ = run(["note", session], capsys, stdin=self.batch())
        assert "bcl-rent" in receipt["minted"]["sources"]

    def test_an_unknown_view_names_the_vocabulary(self, capsys):
        session = opened(capsys)
        code, _, err = run(["check", session, "--view", "everything"], capsys)
        assert code == 1
        assert "invalid choice" in err or "invalid View value" in err
