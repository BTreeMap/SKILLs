"""Page selection: pure, total over a validated page count."""

from __future__ import annotations

from functools import partial
from itertools import chain

from btm_corekit import is_digits


def parse_page_token(page_count: int, token: str) -> range:
    """Parse one validated page token into its selected one-based range:
    `N`, `N-M`, or `N-` (through the last page)."""
    head, dash, tail = token.partition("-")
    if not is_digits(head) or (dash and tail and not is_digits(tail)):
        raise ValueError(
            "Invalid page selection. Use one-based page numbers and ranges, "
            "for example: 1-3,5,8-."
        )

    start = int(head)
    end = start if not dash else page_count if tail == "" else int(tail)
    if start < 1 or end < start or end > page_count:
        raise ValueError(
            f"Page selection {token!r} is outside the document's 1-{page_count} range."
        )

    return range(start, end + 1)


def parse_page_specification(specification: str | None, page_count: int) -> list[int]:
    """Return unique one-based page numbers selected by a user page specification."""
    if specification is None:
        return list(range(1, page_count + 1))

    page_ranges = map(
        partial(parse_page_token, page_count), map(str.strip, specification.split(","))
    )
    # Ordered dict keys preserve each page's first selection in Python 3.11+.
    return list(dict.fromkeys(chain.from_iterable(page_ranges)))
