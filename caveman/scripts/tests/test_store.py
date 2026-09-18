"""Backup slots: deterministic, injective, total, and identity-checked."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from btm_caveman.store import (
    backup_base,
    load_slot,
    read_meta,
    read_utf8,
    slot_for,
)
from btm_corekit import CommandError, write_atomic

SLOT_NAME_LIMIT = 81  # slug(64) + "-" + hex(16)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))


def planted(target: Path, meta: str | None) -> Path:
    """A slot holding a backup, and the meta.json text given (none if None)."""
    slot = slot_for(target.resolve())
    slot.directory.mkdir(parents=True)
    slot.backup_path.write_text("body", encoding="utf-8")
    if meta is not None:
        slot.meta_path.write_text(meta, encoding="utf-8")
    return target.resolve()


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
        assert backup_base().parts[-3:] == ("btm-skills", "caveman", "sessions")


class TestMeta:
    def test_an_unprepared_slot_records_nothing(self, tmp_path):
        assert read_meta(slot_for(tmp_path / "notes.md")) is None

    def test_a_malformed_record_rejects_naming_the_file(self, tmp_path):
        """meta.json is the identity proof, so an unreadable one is a refusal,
        never a slot treated as anonymous."""
        target = planted(tmp_path / "notes.md", "{not json")
        with pytest.raises(CommandError, match=r"unreadable .*meta\.json"):
            read_meta(slot_for(target))


class TestLoadSlot:
    def test_a_missing_backup_refuses(self, tmp_path):
        with pytest.raises(CommandError, match="run prepare first"):
            load_slot(tmp_path / "absent.md")

    def test_a_backup_without_metadata_refuses(self, tmp_path):
        target = planted(tmp_path / "notes.md", None)
        with pytest.raises(CommandError, match="metadata missing"):
            load_slot(target)

    def test_a_slot_recording_another_file_refuses(self, tmp_path):
        target = planted(tmp_path / "notes.md", '{"source": "/elsewhere/other.md"}')
        with pytest.raises(CommandError, match="identity mismatch"):
            load_slot(target)


class TestFileIO:
    def test_atomic_write_replaces_the_whole_file(self, tmp_path):
        path = tmp_path / "a.md"
        path.write_text("before", encoding="utf-8")
        write_atomic(path, "after")
        assert path.read_text(encoding="utf-8") == "after"

    def test_atomic_write_leaves_no_temporary_behind(self, tmp_path):
        path = tmp_path / "a.md"
        write_atomic(path, "text")
        assert [p.name for p in tmp_path.iterdir()] == ["a.md"]

    def test_undecodable_bytes_reject(self, tmp_path):
        path = tmp_path / "bin"
        path.write_bytes(b"\xff\xfe\x00")
        with pytest.raises(CommandError, match="UTF-8"):
            read_utf8(path)
