"""The download boundary: the digest gate, self-healing, and the decoders."""

from __future__ import annotations

import pytest

from btm_asd_ste100 import artifacts
from btm_asd_ste100.records import Lexicon, PhraseAlt, RefAlt, TechnicalAlt, spelled
from btm_corekit import CommandError, UpstreamError, parse_model

V = artifacts.VERSION


class TestFetch:
    def test_every_artifact_lands_and_the_manifest_comes_last(
        self, cache, make_release, make_client
    ):
        calls: list[str] = []
        manifest = artifacts.fetch(make_client(make_release(), calls), V)
        assert {a.path for a in manifest.artifacts} == {
            "data/dictionary.json",
            "data/lexicon.json",
            "data/rules.json",
        }
        assert all(artifacts.slot_of(V, a.path).is_file() for a in manifest.artifacts)
        assert artifacts.cached(V) == manifest
        assert len(calls) == 4, "one request for the manifest, one per artifact"

    def test_a_body_off_its_digest_is_deleted_and_retryable(
        self, cache, make_release, make_client
    ):
        """Exit 2, nothing half-cached: no manifest, no corrupt file."""
        client = make_client(make_release(**{"data/lexicon.json": b"{}\n"}))
        with pytest.raises(UpstreamError, match="digest differs"):
            artifacts.fetch(client, V)
        assert not artifacts.slot_of(V, "data/lexicon.json").exists()
        assert artifacts.cached(V) is None

    def test_a_manifest_that_does_not_decode_is_an_upstream_failure(
        self, cache, make_release, make_client
    ):
        client = make_client(
            make_release(**{artifacts.MANIFEST: b"<html>moved</html>"})
        )
        with pytest.raises(UpstreamError, match="not a ste-tax manifest"):
            artifacts.fetch(client, V)


class TestSelfHeal:
    def test_a_tampered_cache_fails_once_then_refetches(
        self, cache, make_release, make_client
    ):
        client = make_client(make_release())
        manifest = artifacts.fetch(client, V)
        slot = artifacts.slot_of(V, "data/lexicon.json")
        slot.write_bytes(slot.read_bytes() + b" ")
        with pytest.raises(UpstreamError, match="rerun to refetch"):
            artifacts.load(manifest, V, "lexicon.json", Lexicon)
        assert not slot.exists()
        healed = artifacts.ensure(client, V)
        assert artifacts.load(healed, V, "lexicon.json", Lexicon).approved

    def test_a_missing_release_names_the_version_and_exits_two(
        self, cache, make_client
    ):
        with pytest.raises(UpstreamError, match=f"ste-tax {V}"):
            artifacts.ensure(make_client({}), V)


class TestTag:
    @pytest.mark.parametrize("raw", ["latest", "0.1.0", "v1.2", "v1.2.3; rm"])
    def test_anything_but_a_semver_tag_is_refused(self, raw):
        with pytest.raises(CommandError, match="no release tag"):
            artifacts.tag(raw)


class TestLexiconDecoder:
    def test_each_alternative_decodes_to_its_variant(self, lexicon_doc):
        lexicon = parse_model(Lexicon, lexicon_doc, "lexicon")
        alts = next(
            u for u in lexicon.unapproved if u.word == "accelerate"
        ).alternatives
        assert [type(a) for a in alts] == [RefAlt, TechnicalAlt, PhraseAlt]
        assert [spelled(a) for a in alts] == [
            "fast (adj): faster",
            "throttle (TN)",
            "make fast",
        ]

    def test_a_stated_pos_stays_a_reference(self, lexicon_doc):
        lexicon = parse_model(Lexicon, lexicon_doc, "lexicon")
        (alt,) = next(u for u in lexicon.unapproved if u.word == "utilize").alternatives
        assert isinstance(alt, RefAlt) and alt.stated_pos == "v"

    def test_a_wrong_schema_version_is_refused(self, lexicon_doc):
        with pytest.raises(CommandError, match="schema_version"):
            parse_model(Lexicon, {**lexicon_doc, "schema_version": 2}, "lexicon")
