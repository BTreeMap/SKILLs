"""The registry: one shape per index, and the refusals written once."""

from __future__ import annotations

import inspect

import httpx
import pytest

from btm_corekit import INDEXES, CommandError, Window, search
from btm_corekit.indexes import registry
from btm_corekit.indexes.work import ByArxiv, ByDoi, ByNative, Found


def stub(windows: bool, called: list[object] | None = None) -> registry.Index:
    """An index whose search records its call and answers nothing."""

    def answer(*args: object) -> Found:
        if called is not None:
            called.append(args)
        return Found(total=0, works=())

    return registry.Index(
        name="stub",
        search=answer,
        lookup=None,
        references=None,
        citations=None,
        passages=None,
        windows=windows,
    )


class TestShape:
    def test_every_entry_is_named_by_its_key(self):
        assert all(index.name == name for name, index in INDEXES.items())

    def test_openalex_leads_so_it_is_every_default(self):
        assert next(iter(INDEXES)) == "openalex"

    @pytest.mark.parametrize("name", list(INDEXES))
    def test_every_search_takes_the_registry_signature(self, name):
        """A positional mismatch would pass mypy through a lambda and fail
        only at the first live call, so the parameters are read here."""
        parameters = inspect.signature(INDEXES[name].search).parameters
        assert list(parameters) == ["client", "cap", "query", "limit", "window"]

    def test_the_registry_cannot_be_edited_by_a_caller(self):
        with pytest.raises(TypeError):
            INDEXES["x"] = INDEXES["openalex"]  # type: ignore[index]


class TestWindow:
    def test_an_empty_window_is_falsy_and_either_bound_is_not(self):
        assert not Window()
        assert Window(from_year=2020)
        assert Window(to_year=2024)

    def test_a_windowless_index_says_so_once(self, capsys):
        assert not INDEXES["arxiv"].windows
        called: list[object] = []
        search(stub(False, called), httpx.Client(), 1, "q", 1, Window(2020, 2024))
        assert capsys.readouterr().err.count("ignores year bounds") == 1
        assert called, "the search still runs"

    @pytest.mark.parametrize(
        ("windows", "window"),
        [(True, Window(2020, None)), (False, Window()), (True, Window())],
    )
    def test_no_signal_otherwise(self, capsys, windows, window):
        search(stub(windows), httpx.Client(), 1, "q", 1, window)
        assert "ignores" not in capsys.readouterr().err


class TestCapability:
    def test_a_missing_capability_names_the_indexes_that_have_it(self):
        with pytest.raises(CommandError) as raised:
            registry.references(
                INDEXES["crossref"], httpx.Client(), 1, ByNative("x"), 1
            )
        offered = ", ".join(registry.having("references"))
        assert str(raised.value) == (
            f"crossref has no references; indexes that do: {offered}"
        )
        assert type(raised.value) is CommandError, "exit 1: the request's fault"

    @pytest.mark.parametrize("capability", ["references", "citations"])
    def test_having_lists_in_registry_order(self, capability):
        offered = registry.having(capability)
        assert offered[0] == "openalex"
        assert list(offered) == [n for n in INDEXES if n in offered]

    def test_a_capability_no_index_has_says_none(self, monkeypatch):
        monkeypatch.setattr(registry, "INDEXES", {"crossref": INDEXES["crossref"]})
        with pytest.raises(CommandError, match="indexes that do: none"):
            registry.passages(
                INDEXES["crossref"], httpx.Client(), 1, ByNative("x"), None, 1
            )


class TestRef:
    @pytest.mark.parametrize(
        ("build", "raw"),
        [
            (ByDoi, "https://doi.org/10.1/A"),
            (ByDoi, "not-a-doi"),
            (ByArxiv, "arXiv:1706.03762v5"),
            (ByNative, "  "),
        ],
    )
    def test_a_ref_holds_only_its_parsed_form(self, build, raw):
        """Parse first, with the kernel's normalizers; a raw form reaching
        the constructor is a defect, not a request an index can answer."""
        with pytest.raises(ValueError):
            build(raw)

    def test_the_parsed_forms_construct(self):
        assert ByDoi("10.1/a").doi == "10.1/a"
        assert ByArxiv("1706.03762").id == "1706.03762"
        assert ByNative("W123").id == "W123"
