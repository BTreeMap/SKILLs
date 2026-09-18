"""The regenerable cache: one directory per skill, one slot per natural key."""

from __future__ import annotations

import tempfile

import pytest

from btm_corekit import cache_dir, cache_slot, clean_cache


@pytest.fixture(autouse=True)
def _temp_root(tmp_path, monkeypatch):
    """No test may write to the real temp root, nor remove what lives there."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))


def test_the_directory_names_its_owner():
    assert cache_dir("search-web").name == "btm-search-web"
    assert cache_dir("read-pdf") != cache_dir("search-web")


def test_one_key_always_names_one_slot_inside_the_directory():
    slot = cache_slot("search-web", "a query", ".json")
    assert slot == cache_slot("search-web", "a query", ".json")
    assert slot != cache_slot("search-web", "another query", ".json")
    assert slot.parent == cache_dir("search-web") and slot.suffix == ".json"


def test_clean_reports_what_it_freed_and_an_absent_cache_frees_nothing():
    assert clean_cache("search-web") == {"removed": None, "bytes_freed": 0}
    slot = cache_slot("search-web", "a query", ".json")
    slot.parent.mkdir(parents=True)
    slot.write_text("0123456789", encoding="utf-8")
    assert clean_cache("search-web") == {
        "removed": str(cache_dir("search-web")),
        "bytes_freed": 10,
    }
    assert not cache_dir("search-web").exists()
