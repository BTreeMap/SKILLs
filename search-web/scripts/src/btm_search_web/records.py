"""One result shape, whichever backend answered."""

from __future__ import annotations

from pydantic import TypeAdapter

from btm_corekit import Model, NonEmpty, collapse_whitespace
from btm_search_web.constants import SNIPPET_CHARS


def trimmed(text: str | None, limit: int = SNIPPET_CHARS) -> str:
    """Whitespace collapsed and cut to a length a caller can scan."""
    folded = collapse_whitespace(text or "")
    return folded if len(folded) <= limit else folded[:limit].rstrip() + "..."


class Result(Model):
    """One hit. The scholarly fields are absent for a web or reference hit,
    and `dump` omits them, so every backend returns the same record."""

    title: NonEmpty
    url: str = ""
    snippet: str = ""
    source: NonEmpty
    published: str | None = None
    doi: str | None = None
    year: int | None = None
    cited_by: int | None = None


Results: TypeAdapter[list[Result]] = TypeAdapter(list[Result])
