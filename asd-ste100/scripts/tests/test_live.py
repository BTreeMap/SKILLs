"""Whether the pinned ste-tax release still answers as this skill parses it.

Advisory: this asks the real CDN, and a CDN having a bad afternoon is not
this repository breaking.
"""

from __future__ import annotations

import tempfile

import pytest

from btm_asd_ste100 import artifacts
from btm_asd_ste100.records import Dictionary, Lexicon, Rules
from btm_corekit import build_client

pytestmark = pytest.mark.network


def test_the_pinned_release_downloads_verifies_and_decodes(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    client = build_client(artifacts.SKILL, read_timeout=None)
    manifest = artifacts.fetch(client, artifacts.VERSION)
    lexicon = artifacts.load(manifest, artifacts.VERSION, "lexicon.json", Lexicon)
    rules = artifacts.load(manifest, artifacts.VERSION, "rules.json", Rules)
    dictionary = artifacts.load(
        manifest, artifacts.VERSION, "dictionary.json", Dictionary
    )
    assert len(rules.rules) == 53
    assert any(a.word == "make sure" for a in lexicon.approved)
    assert any(u.word == "whose" and u.help for u in lexicon.unapproved)
    assert len(dictionary.entries) > 2000
