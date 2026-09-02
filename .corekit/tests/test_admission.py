"""Admission mechanics: keys, rows, shape, refs with did-you-mean, minting, links."""

from __future__ import annotations

import pytest

from btm_corekit import Admission, CommandError, Pool, field_text, suggest


def fake_mint(words):
    return "-".join(words) + "-x"


class TestHelpers:
    def test_field_text_reads_only_non_empty_strings(self):
        assert field_text({"a": " b "}, "a") == "b"
        assert field_text({"a": "  "}, "a") is None
        assert field_text({"a": 3}, "a") is None

    def test_suggest_prefers_keyword_overlap_then_edit_distance(self):
        assert suggest("rent", ["rent-length-1", "bcl-2"]) == ["rent-length-1"]
        assert suggest("doi:10.1/abc", ["doi:10.1/abd", "title:zzz"]) == [
            "doi:10.1/abd"
        ]
        assert suggest("zzz", ["rent-length-1"]) == []


class TestAdmission:
    def test_keys_rows_and_shape_report_without_raising(self):
        gate = Admission()
        gate.keys({"leaves": [], "bogus": 1}, ("leaves",))
        assert gate.rows("nope", "leaves", {"leaves": "shape"}) == []
        assert gate.rows(None, "leaves") == []
        assert gate.shape({"q": 1, "extra": 2}, ("q",), "leaves[0]") is False
        wheres = [p.where for p in gate.problems]
        assert wheres == ["bogus", "leaves", "leaves[0]"]
        assert gate.problems[1].hint == "shape"

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
        full = gate.mint_id({"kw": ["rent", "length"]}, pool, "leaves[0]")
        assert full == "rent-length-x"
        assert pool.ids == [full] and pool.minted == {"rent-length": full}
        assert gate.resolve_ref("rent", pool, "w") == full
        assert gate.advisories == []  # fresh ids recover silently
        assert gate.mint_id({"kw": ["rent", "length"]}, pool, "leaves[1]") is None
        assert gate.mint_id({"ref": "explicit"}, pool, "leaves[2]") == "explicit-x"
        assert gate.mint_id({"kw": []}, pool, "leaves[3]") is None
        assert "vary one keyword" in gate.problems[0].fix

    def test_minting_without_a_minter_is_a_defect(self):
        with pytest.raises(CommandError):
            Admission().mint_id({"kw": ["a", "b"]}, Pool("x", []), "w")

    def test_links_validate_pad_ids(self):
        gate = Admission(pad={"j1", "j2"})
        assert gate.links({"from": ["j1", "j2"]}, "w") == ("j1", "j2")
        assert gate.links({}, "w") == ()
        assert gate.links({"from": ["j9"]}, "w") is None
        assert gate.links({"from": "j1"}, "w") is None
        assert gate.clean is False
