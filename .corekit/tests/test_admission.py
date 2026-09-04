"""Admission mechanics: decoding, refs with did-you-mean, minting, pad links."""

from __future__ import annotations

import pytest

from btm_corekit import Admission, CommandError, Model, Named, NonEmpty, Pool, suggest


def fake_mint(words):
    return "-".join(words) + "-x"


class Entry(Named):
    q: NonEmpty


class Batch(Model):
    leaves: tuple[dict, ...] = ()


class TestHelpers:
    def test_suggest_prefers_keyword_overlap_then_edit_distance(self):
        assert suggest("rent", ["rent-length-1", "bcl-2"]) == ["rent-length-1"]
        assert suggest("doi:10.1/abc", ["doi:10.1/abd", "title:zzz"]) == [
            "doi:10.1/abd"
        ]
        assert suggest("zzz", ["rent-length-1"]) == []


class TestDecode:
    def test_every_field_problem_comes_back_located(self):
        gate = Admission()
        assert gate.decode(Entry, {"kw": ["a"], "q": "", "x": 1}, "leaves[0]") is None
        assert {p.where for p in gate.problems} == {"leaves[0].q", "leaves[0].x"}

    def test_the_schema_fragment_rides_along(self):
        """pydantic states the fix; the hint keeps the whole entry shape."""
        gate = Admission()
        gate.decode(Entry, {"kw": ["a"], "q": ""}, "leaves[0]", "the shape")
        assert gate.problems[0].hint == "the shape"

    def test_a_root_problem_keeps_the_outer_location(self):
        gate = Admission()
        assert gate.decode(Entry, "not an object", "leaves[0]") is None
        assert gate.problems[0].where == "leaves[0]"

    def test_known_keys_names_what_the_container_does_not_declare(self):
        gate = Admission()
        gate.known_keys({"leaves": [], "bogus": 1}, Batch)
        assert [p.where for p in gate.problems] == ["bogus"]
        assert "leaves" in gate.problems[0].hint


class TestAdmission:
    def test_resolve_ref_covers_every_resolution(self):
        gate = Admission()
        pool = Pool("leaf", ["rent-length-1", "rent-width-2"])
        assert gate.resolve_ref("rent-length-1", pool, "w") == "rent-length-1"
        assert gate.resolve_ref("width", pool, "w") == "rent-width-2"
        assert "recovered leaf" in gate.advisories[0]
        assert gate.resolve_ref("rent", pool, "w") is None
        assert gate.resolve_ref("zzz", pool, "w") is None
        assert [p.fix[:8] for p in gate.problems] == ["replace ", "replace "]

    def test_mint_id_tracks_slugs_ids_and_fresh(self):
        gate = Admission(mint=fake_mint)
        pool = Pool("leaf", [])
        named = Entry(kw=["rent", "length"], q="x")
        full = gate.mint_id(named, pool, "leaves[0]")
        assert full == "rent-length-x"
        assert pool.ids == [full] and pool.minted == {"rent-length": full}
        assert gate.resolve_ref("rent", pool, "w") == full
        assert gate.advisories == []  # fresh ids recover silently
        assert gate.mint_id(named, pool, "leaves[1]") is None
        assert "vary one keyword" in gate.problems[0].fix
        assert gate.mint_id(Entry(ref="explicit", q="x"), pool, "w") == "explicit-x"

    def test_an_entry_that_names_itself_nothing_is_refused(self):
        gate = Admission(mint=fake_mint)
        assert gate.decode(Entry, {"q": "x"}, "leaves[0]") is None
        assert 'add "kw"' in gate.problems[0].fix

    def test_pool_keywords_extend_incrementally(self):
        pool = Pool("leaf", ["rent-length-1"])
        assert pool.keywords() == {"rent-length-1": {"rent", "length", "1"}}
        pool.ids.append("bcl-2")
        assert set(pool.keywords()) == {"rent-length-1", "bcl-2"}
        assert suggest("bcl", pool.ids, keywords=pool.keywords()) == ["bcl-2"]

    def test_minting_without_a_minter_is_a_defect(self):
        with pytest.raises(CommandError):
            Admission().mint_id(Entry(kw=["a", "b"], q="x"), Pool("x", []), "w")

    def test_pad_links_name_the_entry_that_does_not_exist(self):
        gate = Admission(pad={"j1", "j2"})
        assert gate.pad_links(("j1", "j2"), "w") is True
        assert gate.pad_links((), "w") is True
        assert gate.pad_links(("j9",), "w") is False
        assert gate.problems[0].where == "w.from[0]"
