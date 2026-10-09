"""A miniature ste-tax release: the artifact shapes, a dozen words."""

from __future__ import annotations

import hashlib
import json
import tempfile

import httpx
import pytest

from btm_asd_ste100 import artifacts
from btm_corekit import build_client

LEXICON = {
    "schema_version": 1,
    "approved": [
        {
            "id": "remove (v)",
            "word": "remove",
            "pos": "v",
            "forms": ["remove", "removes", "removed", "removed"],
            "plural": None,
        },
        {
            "id": "install (v)",
            "word": "install",
            "pos": "v",
            "forms": ["install", "installs", "installed", "installed"],
            "plural": None,
        },
        {
            "id": "the (art)",
            "word": "the",
            "pos": "art",
            "forms": ["the"],
            "plural": None,
        },
        {"id": "a (art)", "word": "a", "pos": "art", "forms": ["a"], "plural": None},
        {
            "id": "and (conj)",
            "word": "and",
            "pos": "conj",
            "forms": ["and"],
            "plural": None,
        },
        {
            "id": "be (v)",
            "word": "be",
            "pos": "v",
            "forms": ["be", "is", "was", "are", "were"],
            "plural": None,
        },
        {
            "id": "make sure (v)",
            "word": "make sure",
            "pos": "v",
            "forms": ["make sure", "makes sure", "made sure"],
            "plural": None,
        },
        {
            "id": "that (conj)",
            "word": "that",
            "pos": "conj",
            "forms": ["that"],
            "plural": None,
        },
        {
            "id": "test (n)",
            "word": "test",
            "pos": "n",
            "forms": ["test"],
            "plural": "tests",
        },
        {
            "id": "do (v)",
            "word": "do",
            "pos": "v",
            "forms": ["do", "does", "did", "done"],
            "plural": None,
        },
        {
            "id": "not (adv)",
            "word": "not",
            "pos": "adv",
            "forms": ["not"],
            "plural": None,
        },
        {
            "id": "opening (n)",
            "word": "opening",
            "pos": "n",
            "forms": ["opening"],
            "plural": "openings",
        },
        {
            "id": "by (prep)",
            "word": "by",
            "pos": "prep",
            "forms": ["by"],
            "plural": None,
        },
        {
            "id": "with (prep)",
            "word": "with",
            "pos": "prep",
            "forms": ["with"],
            "plural": None,
        },
        {
            "id": "find (v)",
            "word": "find",
            "pos": "v",
            "forms": ["find", "finds", "found", "found"],
            "plural": None,
        },
        {
            "id": "fast (adj)",
            "word": "fast",
            "pos": "adj",
            "forms": ["fast", "faster"],
            "plural": None,
        },
        {
            "id": "turn (v)",
            "word": "turn",
            "pos": "v",
            "forms": ["turn", "turns", "turned", "turned"],
            "plural": None,
        },
        {
            "id": "off (adv)",
            "word": "off",
            "pos": "adv",
            "forms": ["off"],
            "plural": None,
        },
        {
            "id": "rear (n)",
            "word": "rear",
            "pos": "n",
            "forms": ["rear"],
            "plural": "rears",
        },
        {
            "id": "long (adj)",
            "word": "long",
            "pos": "adj",
            "forms": ["long", "longer", "longest"],
            "plural": None,
        },
        {"id": "no (adj)", "word": "no", "pos": "adj", "forms": ["no"], "plural": None},
        {
            "id": "of (prep)",
            "word": "of",
            "pos": "prep",
            "forms": ["of"],
            "plural": None,
        },
        {
            "id": "get (v)",
            "word": "get",
            "pos": "v",
            "forms": ["get", "gets", "got"],
            "plural": None,
        },
        {
            "id": "away from (prep)",
            "word": "away from",
            "pos": "prep",
            "forms": ["away from"],
            "plural": None,
        },
    ],
    "unapproved": [
        {
            "word": "rear of",
            "pos": "prep",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "with (prep)"}],
            "note": None,
        },
        {
            "word": "long",
            "pos": "adv",
            "qualifier": "no longer",
            "forms": [],
            "alternatives": [{"ref": "not (adv)"}],
            "note": None,
        },
        {
            "word": "get away",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "remove (v)"}],
            "note": None,
        },
        {
            "word": "turn off",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"phrase": "set to off"}],
            "note": None,
        },
        {
            "word": "hand-tighten",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "install (v)"}],
            "note": None,
        },
        {
            "word": "ensure",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "make sure (v)"}],
            "note": None,
        },
        {
            "word": "test",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "test (n)"}, {"ref": "do (v)"}],
            "note": None,
        },
        {
            "word": "accelerate",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [
                {"ref": "fast (adj)", "form": "faster"},
                {"technical": "throttle", "class": "tn"},
                {"phrase": "make fast"},
            ],
            "note": None,
            "extra_field_from_a_newer_writer": True,
        },
        {
            "word": "finding",
            "pos": "n",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "test (n)"}],
            "note": None,
        },
        {
            "word": "return",
            "pos": "n",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "do (v)"}],
            "note": None,
        },
        {
            "word": "return",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "do (v)"}],
            "note": None,
        },
        {
            "word": "few",
            "pos": "adj",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"phrase": "small number"}],
            "note": None,
        },
        {
            "word": "few",
            "pos": "adj",
            "qualifier": "a few",
            "forms": [],
            "alternatives": [{"ref": "do (v)"}],
            "note": None,
        },
        {
            "word": "whose",
            "pos": "pron",
            "qualifier": None,
            "forms": [],
            "alternatives": [],
            "note": None,
            "help": "Use a different construction.",
        },
        {
            "word": "re-",
            "pos": "prefix",
            "qualifier": None,
            "forms": [],
            "alternatives": [],
            "note": None,
            "help": "Use AGAIN (adv) or BACK (adv) with the basic word.",
        },
        {
            "word": "utilize",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "alternatives": [{"ref": "use (v)", "stated_pos": "v"}],
            "note": None,
        },
    ],
}

RULES = {
    "schema_version": 1,
    "rules": [
        {
            "id": "3.5",
            "title": "t",
            "paraphrase": "p",
            "check": "pattern",
            "parameters": {"ing_approved": ["opening (n)", "during (prep)"]},
        },
        {
            "id": "5.1",
            "title": "t",
            "paraphrase": "p",
            "check": "count",
            "parameters": {
                "mode": "procedure",
                "max_words_per_sentence": 7,
                "notes_max_words_per_sentence": 10,
            },
        },
        {
            "id": "6.3",
            "title": "t",
            "paraphrase": "p",
            "check": "count",
            "parameters": {"mode": "description", "max_words_per_sentence": 8},
        },
        {
            "id": "6.6",
            "title": "t",
            "paraphrase": "p",
            "check": "count",
            "parameters": {"mode": "description", "max_sentences_per_paragraph": 2},
        },
        {
            "id": "8.1",
            "title": "t",
            "paraphrase": "p",
            "check": "pattern",
            "parameters": {"forbidden_punctuation": [";"]},
        },
    ],
}

DICTIONARY = {
    "schema_version": 1,
    "entries": [
        {
            "word": "ensure",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "status": {
                "kind": "unapproved",
                "alternatives": [
                    {"kind": "word", "word": "MAKE SURE", "pos": "v", "context": None}
                ],
                "help": None,
                "note": None,
            },
            "ste_example": "MAKE SURE THAT THE TEST IS DONE.",
            "nonste_example": None,
            "page": "2-1-E5",
        },
        {
            "word": "return",
            "pos": "v",
            "qualifier": None,
            "forms": [],
            "status": {
                "kind": "unapproved",
                "alternatives": [
                    {"kind": "word", "word": "DO", "pos": "v", "context": None},
                ],
                "help": None,
                "note": None,
            },
            "ste_example": "DO THE TEST AGAIN.",
            "nonste_example": "Return to the test.",
            "page": "2-1-R7",
        },
        {
            "word": "few",
            "pos": "adj",
            "qualifier": None,
            "forms": [],
            "status": {"kind": "unapproved", "alternatives": [], "help": None},
            "page": "2-1-F3",
        },
        {
            "word": "few",
            "pos": "adj",
            "qualifier": "a few",
            "forms": [],
            "status": {"kind": "unapproved", "alternatives": [], "help": None},
            "page": "2-1-F3",
        },
        {  # recorded from v0.1.2: a headword with no part of speech
            "word": "such as",
            "pos": None,
            "qualifier": None,
            "forms": [],
            "status": {
                "kind": "unapproved",
                "alternatives": [
                    {"kind": "phrase", "text": "FOR EXAMPLE", "context": None}
                ],
                "help": None,
                "note": None,
            },
            "ste_example": "WHEN YOU REMOVE THE STUD, USE APPLICABLE TOOLS. "
            "FOR EXAMPLE, USE A PLASTIC MALLET AND A PUNCH.",
            "nonste_example": "When you remove the stud, use applicable tools "
            "such as a plastic mallet and a punch.",
            "page": "2-1-S28",
        },
        {
            "word": "TEST",
            "pos": "n",
            "qualifier": None,
            "forms": [],
            "status": {
                "kind": "approved",
                "meaning": "Procedure that finds the condition of an item",
                "help": None,
                "alternatives": [],
            },
            "ste_example": None,
            "nonste_example": None,
            "page": "2-1-T4",
        },
        {
            "word": "REMOVE",
            "pos": "v",
            "qualifier": None,
            "forms": ["REMOVES", "REMOVED", "REMOVED"],
            "status": {
                "kind": "approved",
                "meaning": "To take away",
                "help": None,
                "alternatives": [],
            },
            "ste_example": None,
            "nonste_example": None,
            "page": "2-1-R9",
        },
    ],
}


@pytest.fixture
def lexicon_doc() -> dict:
    return LEXICON


@pytest.fixture
def rules_doc() -> dict:
    return RULES


@pytest.fixture
def make_release():
    return release


@pytest.fixture
def make_client():
    return serving


def blob(doc: dict) -> bytes:
    return (json.dumps(doc, indent=1) + "\n").encode()


def release(**overrides: bytes) -> dict[str, bytes]:
    """Path -> served bytes. The manifest digests the honest bytes, so an
    override serves a body the manifest does not vouch for."""
    honest = {
        "data/dictionary.json": blob(DICTIONARY),
        "data/lexicon.json": blob(LEXICON),
        "data/rules.json": blob(RULES),
    }
    manifest = {
        "schema_version": 1,
        "source": {"issue": 9},
        "artifacts": [
            {"path": p, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
            for p, b in honest.items()
        ],
    }
    return {**honest, artifacts.MANIFEST: blob(manifest), **overrides}


def serving(files: dict[str, bytes], calls: list[str] | None = None) -> httpx.Client:
    prefix = f"/gh/RadonSys/ste-tax@{artifacts.VERSION}/"

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        path = request.url.path.removeprefix(prefix)
        if path in files:
            return httpx.Response(200, content=files[path])
        return httpx.Response(404)

    return build_client(artifacts.SKILL, transport=httpx.MockTransport(handler))


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path / f"btm-{artifacts.SKILL}"
