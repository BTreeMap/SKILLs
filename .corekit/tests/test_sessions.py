"""SessionStore: resolution, recovery, listing, and marker-guarded removal."""

from __future__ import annotations

import pytest

from btm_corekit import CommandError, SessionStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return SessionStore("alpha", marker="meta.json", hint="run init first")


def make_session(store: SessionStore, name: str) -> None:
    directory = store.root() / name
    directory.mkdir(parents=True)
    (directory / "meta.json").write_text("{}", encoding="utf-8")


class TestSessionStore:
    def test_a_full_identifier_resolves_exactly(self, store):
        make_session(store, "deep-sea-abc123")
        assert store.dir_of("deep-sea-abc123") == store.root() / "deep-sea-abc123"

    def test_a_keyword_subset_recovers_with_a_signal(self, store, capsys):
        make_session(store, "deep-sea-abc123")
        assert store.dir_of("sea") == store.root() / "deep-sea-abc123"
        assert "recovered" in capsys.readouterr().err

    def test_a_path_argument_stands_as_given(self, store, tmp_path):
        assert store.dir_of(str(tmp_path / "x")) == tmp_path / "x"

    def test_clean_lists_sessions_with_sizes(self, store):
        make_session(store, "deep-sea-abc123")
        listing = store.clean(None, remove_all=False)
        assert [row["session"] for row in listing["sessions"]] == ["deep-sea-abc123"]

    def test_clean_refuses_a_directory_without_the_marker(self, store):
        (store.root() / "stray").mkdir(parents=True)
        with pytest.raises(CommandError, match="refusing"):
            store.clean("stray", remove_all=False)

    def test_clean_removes_one_session_and_reports_bytes(self, store):
        make_session(store, "deep-sea-abc123")
        report = store.clean("deep-sea-abc123", remove_all=False)
        assert report["bytes_freed"] > 0
        assert store.ids() == []

    def test_clean_all_with_a_session_is_refused(self, store):
        with pytest.raises(CommandError, match="one of the two"):
            store.clean("deep-sea-abc123", remove_all=True)


class TestCreateAndMeta:
    def test_create_mints_under_the_root_and_refuses_twice(self, store, capsys):
        made = store.create("deep sea")
        assert made.name.startswith("deep-sea-")
        assert made.directory == store.root() / made.name
        store.write_meta(made.directory, {"k": 1})
        assert store.read_meta(made.directory) == {"k": 1}
        with pytest.raises(CommandError, match="already exists"):
            store.create(str(made.directory))

    def test_a_path_stands_as_given_and_band_advises(self, store, tmp_path, capsys):
        made = store.create(str(tmp_path / "here"))
        assert made.directory == tmp_path / "here"
        store.create("solo")
        assert "two or three keywords" in capsys.readouterr().err

    def test_directory_requires_the_marker(self, store):
        make_session(store, "deep-sea-abc123")
        assert store.directory("sea") == store.root() / "deep-sea-abc123"
        with pytest.raises(CommandError, match="run init first"):
            store.directory("absent")
