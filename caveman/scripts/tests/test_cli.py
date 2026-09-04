"""The verbs end to end: admit, prepare, apply, restore, clean."""

from __future__ import annotations

import pytest

from btm_caveman import cli as caveman_cli
from btm_caveman.admit import admit
from btm_caveman.cli import main
from btm_caveman.model import MAX_FILE_SIZE, Plan, Refusal

PROSE = "# Notes\n\nThis is a reasonably long sentence of ordinary prose.\n"


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))


@pytest.fixture
def note(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text(PROSE, encoding="utf-8")
    return path


class TestAdmit:
    def test_ordinary_prose_is_admitted(self, note):
        assert isinstance(admit(note), Plan)

    def test_a_missing_file_is_refused(self, tmp_path):
        assert isinstance(admit(tmp_path / "absent.md"), Refusal)

    def test_an_empty_file_is_refused(self, tmp_path):
        path = tmp_path / "empty.md"
        path.write_text("   \n", encoding="utf-8")
        assert "empty" in admit(path).reason

    def test_a_secret_looking_name_is_refused(self, tmp_path):
        path = tmp_path / "api-key.md"
        path.write_text(PROSE, encoding="utf-8")
        assert "sensitive" in admit(path).reason

    def test_an_oversized_file_is_refused(self, tmp_path):
        path = tmp_path / "big.md"
        path.write_text("x" * (MAX_FILE_SIZE + 1), encoding="utf-8")
        assert "exceeds" in admit(path).reason

    def test_non_utf8_bytes_are_refused(self, tmp_path):
        path = tmp_path / "bin.md"
        path.write_bytes(b"\xff\xfe\x00")
        assert "UTF-8" in admit(path).reason

    def test_a_body_that_is_only_frontmatter_is_refused(self, tmp_path):
        path = tmp_path / "fm.md"
        path.write_text("---\na: 1\n---\n\n", encoding="utf-8")
        assert "empty after frontmatter" in admit(path).reason

    def test_a_code_file_is_admitted_with_guidance(self, tmp_path):
        path = tmp_path / "script.py"
        path.write_text("def f():\n    return 1\n", encoding="utf-8")
        plan = admit(path)
        assert isinstance(plan, Plan)
        assert any("CODE" in note for note in plan.notes)


class TestRoundTrip:
    def test_prepare_then_apply_then_restore(self, note, capsys):
        assert main(["prepare", str(note)]) == 0
        capsys.readouterr()

        body_file = note.parent / "compressed.md"
        body_file.write_text("# Notes\n\nOrdinary prose.\n", encoding="utf-8")
        assert main(["apply", str(note), str(body_file)]) == 0
        assert "Ordinary prose." in note.read_text(encoding="utf-8")

        assert main(["restore", str(note)]) == 0
        assert note.read_text(encoding="utf-8") == PROSE

    def test_apply_refuses_a_body_that_drops_a_heading(self, note, capsys):
        main(["prepare", str(note)])
        capsys.readouterr()
        body_file = note.parent / "compressed.md"
        body_file.write_text("Ordinary prose.\n", encoding="utf-8")
        # The ERROR lines say what to fix, which is what exit 1 means.
        assert main(["apply", str(note), str(body_file)]) == 1
        assert note.read_text(encoding="utf-8") == PROSE  # target untouched

    def test_apply_without_prepare_refuses(self, note, tmp_path):
        body_file = tmp_path / "b.md"
        body_file.write_text("x\n", encoding="utf-8")
        assert main(["apply", str(note), str(body_file)]) == 1

    def test_restore_without_a_backup_refuses(self, note):
        assert main(["restore", str(note)]) == 1


class TestCheckAndClean:
    def test_check_admits_prose_and_reports_no_signal(self, note, capsys):
        assert main(["check", str(note)]) == 0
        assert "OK: admissible" in capsys.readouterr().out

    def test_check_refuses_a_missing_file(self, tmp_path, capsys):
        assert main(["check", str(tmp_path / "absent.md")]) == 1
        assert "REFUSED" in capsys.readouterr().out

    def test_clean_removes_one_file_s_artifacts(self, note, capsys):
        main(["prepare", str(note)])
        capsys.readouterr()
        assert main(["clean", str(note)]) == 0
        assert main(["restore", str(note)]) == 1  # the undo is gone

    def test_clean_all_reports_an_empty_tree(self, capsys):
        assert main(["clean", "--all"]) == 0
        assert "no backups to remove" in capsys.readouterr().out

    def test_prepare_refuses_to_overwrite_an_existing_backup(self, note, capsys):
        """The witness gating destruction: a second prepare must not replace
        the original the first one saved, or restore returns the compressed
        text and the real original is gone."""
        assert main(["prepare", str(note)]) == 0
        note.write_text("# Notes\n\nedited since the first prepare.\n")
        capsys.readouterr()
        assert main(["prepare", str(note)]) == 1
        out = capsys.readouterr().out
        assert "backup already exists" in out
        assert main(["restore", str(note)]) == 0
        assert "reasonably long sentence" in note.read_text(encoding="utf-8")

    def test_prepare_refuses_a_slot_recording_another_file(
        self, note, tmp_path, monkeypatch, capsys
    ):
        """Slots are derived from the path, so a collision would let one file's
        prepare destroy another file's saved original."""
        other = tmp_path / "other.md"
        other.write_text(PROSE, encoding="utf-8")
        assert main(["prepare", str(note)]) == 0
        capsys.readouterr()
        shared = caveman_cli.slot_for(note)
        monkeypatch.setattr(caveman_cli, "slot_for", lambda path: shared)
        assert main(["prepare", str(other)]) == 1
        assert "slot collision" in capsys.readouterr().out

    def test_a_non_markdown_extension_warns_without_refusing(self, tmp_path, capsys):
        path = tmp_path / "notes.rst"
        path.write_text(PROSE, encoding="utf-8")
        assert main(["check", str(path)]) == 0
        assert "checks assume Markdown" in capsys.readouterr().out

    def test_an_unknown_verb_names_the_ones_that_exist(self, capsys):
        assert main(["fly"]) == 1
        assert "invalid choice" in capsys.readouterr().err

    def test_the_self_test_verb_is_gone(self, capsys):
        assert main(["self-test"]) == 1
