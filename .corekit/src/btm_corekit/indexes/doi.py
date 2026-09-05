"""The DOI resolver: whether an identifier leads anywhere.

Separate from Crossref on purpose. Crossref answers what it registered;
doi.org answers whether the handle resolves at all, including for DOIs
another agency registered.
"""

from __future__ import annotations

import urllib.parse

import httpx

from btm_corekit.net.http import head_status

HOST = "doi.org"

RESOLVED = 302
"""doi.org redirects a live handle to its publisher and 404s an unknown one."""


def target(doi: str) -> str:
    """`quote` keeps a `#` or `?` inside a DOI part of the path rather than
    letting it start a fragment or a query."""
    return f"https://{HOST}/{urllib.parse.quote(doi)}"


def resolves(client: httpx.Client, doi: str) -> int:
    """The status doi.org gives this handle, redirect unfollowed."""
    return head_status(client, target(doi))
