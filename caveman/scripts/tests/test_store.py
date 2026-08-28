"""Backup slots: deterministic, injective, total, and identity-checked."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from btm_caveman.model import Refusal
from btm_caveman.store import (
    backup_base,
    load_slot,
    read_utf8,
    slot_for,
    write_text_atomic,
)

SLOT_NAME_LIMIT = 81  # slug(64) + "-" + hex(16)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))


class TestSlotDerivation:
    def test_the_same_path_always_derives_the_same_slot(self):
        path = Path("/repo/docs/api/readme.md")
        assert slot_for(path) == slot_for(path)

    def test_equal_names_under_different_parents_stay_distinct(self):
        a = slot_for(Path("/repo/docs/api/readme.md"))
        b = slot_for(Path("/repo/src/api/readme.md"))
        assert a.directory != b.directory

    @pytest.mark.parametrize(
        "path", ["/x/" + "n" * 300 + ".md", "/x/notes \udcff*.md", "/x/ .md"]
    )
    def test_every_representable_name_yields_one_safe_component(self, path):
        name = slot_for(Path(path)).directory.name
        assert re.fullmatch(r"[A-Za-z0-9._-]+", name)
        assert len(name.encode()) <= SLOT_NAME_LIMIT

    def test_the_backup_root_lives_under_the_library_namespace(self):
        assert backup_base().parts[-3:] == ("btm-skills", "caveman", "backups")


class TestLoadSlot:
    def test_a_missing_backup_refuses(self, tmp_path):
        result = load_slot(tmp_path / "absent.md")
        assert isinstance(result, Refusal)
        assert "run prepare first" in result.reason

    def test_a_backup_without_metadata_refuses(self, tmp_path):
        target = tmp_path / "notes.md"
        target.write_text("body", encoding="utf-8")
        slot = slot_for(target.resolve())
        slot.directory.mkdir(parents=True)
        slot.backup_path.write_text("body", encoding="utf-8")
        result = load_slot(target.resolve())
        assert isinstance(result, Refusal)
        assert "metadata missing or unreadable" in result.reason

    def test_a_slot_recording_another_file_refuses(self, tmp_path):
        target = tmp_path / "notes.md"
        target.write_text("body", encoding="utf-8")
        slot = slot_for(target.resolve())
        slot.directory.mkdir(parents=True)
        slot.backup_path.write_text("body", encoding="utf-8")
        slot.meta_path.write_text('{"source": "/elsewhere/other.md"}', encoding="utf-8")
        result = load_slot(target.resolve())
        assert isinstance(result, Refusal)
        assert "identity mismatch" in result.reason


class TestFileIO:
    def test_atomic_write_replaces_the_whole_file(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_text("before", encoding="utf-8")
        write_text_atomic(path, "after")
        assert path.read_text(encoding="utf-8") == "after"

    def test_atomic_write_leaves_no_temporary_behind(self, tmp_path):
        path = tmp_path / "a.md"
        write_text_atomic(path, "text")
        assert [p.name for p in tmp_path.iterdir()] == ["a.md"]

    def test_undecodable_bytes_read_as_none(self, tmp_path):
        path = tmp_path / "bin"
        path.write_bytes(b"\xff\xfe\x00")
        assert read_utf8(path) is None
