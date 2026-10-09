"""Every index behind one shape: a name, a search, and the capabilities it
has, each either a function of the shared signature or None.

A caller names an index and asks for a capability; one asked of an index
that lacks it is a refusal naming the indexes that have it, written here
once. Dispatch is one mapping lookup; the cost is the index's own.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypeVar

import httpx

from btm_corekit.indexes import (
    arxiv,
    crossref,
    firecrawl,
    openalex,
    semanticscholar,
)
from btm_corekit.indexes.work import Found, Passage, Ref, Window, Work
from btm_corekit.report.channels import signal
from btm_corekit.report.errors import CommandError

Search = Callable[[httpx.Client, int, str, int, Window, int], Found]
Lookup = Callable[[httpx.Client, int, Ref], Work | None]
Graph = Callable[[httpx.Client, int, Ref, int], Found]
Passages = Callable[[httpx.Client, int, Ref, str | None, int], tuple[Passage, ...]]

Capability = Literal["lookup", "references", "citations", "passages"]

F = TypeVar("F")


@dataclass(frozen=True, slots=True)
class Index:
    """One index. `windows` says whether its search honours a year window;
    an absent capability is None rather than a function that refuses."""

    name: str
    search: Search
    lookup: Lookup | None
    references: Graph | None
    citations: Graph | None
    passages: Passages | None
    windows: bool


INDEXES: Mapping[str, Index] = MappingProxyType(
    {
        "openalex": Index(
            name="openalex",
            search=openalex.search,
            lookup=openalex.lookup,
            references=openalex.references,
            citations=openalex.citations,
            passages=None,
            windows=True,
        ),
        "crossref": Index(
            name="crossref",
            search=crossref.search,
            lookup=crossref.lookup,
            references=None,
            citations=None,
            passages=None,
            windows=True,
        ),
        "arxiv": Index(
            name="arxiv",
            search=arxiv.search,
            lookup=arxiv.lookup,
            references=None,
            citations=None,
            passages=None,
            windows=False,
        ),
        "semanticscholar": Index(
            name="semanticscholar",
            search=semanticscholar.search,
            lookup=semanticscholar.lookup,
            references=semanticscholar.references,
            citations=semanticscholar.citations,
            passages=None,
            windows=True,
        ),
        "firecrawl": Index(
            name="firecrawl",
            search=firecrawl.search,
            lookup=firecrawl.lookup,
            references=None,
            citations=None,
            passages=firecrawl.passages,
            windows=True,
        ),
    }
)
"""In the order a command line lists them; openalex is every default."""


def having(capability: Capability) -> tuple[str, ...]:
    """The names of the indexes offering `capability`, in registry order."""
    return tuple(name for name, index in INDEXES.items() if getattr(index, capability))


def _capable(index: Index, capability: Capability, function: F | None) -> F:
    if function is None:
        offered = ", ".join(having(capability)) or "none"
        raise CommandError(
            f"{index.name} has no {capability}; indexes that do: {offered}"
        )
    return function


def search(  # noqa: PLR0913, PLR0917 - the index, then the Search signature
    index: Index,
    client: httpx.Client,
    cap: int,
    query: str,
    limit: int,
    window: Window,
    offset: int = 0,
) -> Found:
    """Search one index for `limit` works from rank `offset`, the first rank
    being 0; a window it cannot honour is disclosed, not refused."""
    if window and not index.windows:
        signal(f"{index.name} ignores year bounds; filter after fetching")
    return index.search(client, cap, query, limit, window, offset)


def lookup(index: Index, client: httpx.Client, cap: int, ref: Ref) -> Work | None:
    return _capable(index, "lookup", index.lookup)(client, cap, ref)


def references(
    index: Index, client: httpx.Client, cap: int, ref: Ref, limit: int
) -> Found:
    return _capable(index, "references", index.references)(client, cap, ref, limit)


def citations(
    index: Index, client: httpx.Client, cap: int, ref: Ref, limit: int
) -> Found:
    return _capable(index, "citations", index.citations)(client, cap, ref, limit)


def passages(  # noqa: PLR0913, PLR0917 - the index, then the Passages signature
    index: Index,
    client: httpx.Client,
    cap: int,
    ref: Ref,
    query: str | None,
    limit: int,
) -> tuple[Passage, ...]:
    return _capable(index, "passages", index.passages)(client, cap, ref, query, limit)
