"""Endpoints, caps, and the closed vocabularies the verbs are built from."""

from __future__ import annotations

from enum import StrEnum

INSTANT_ANSWER = "https://api.duckduckgo.com/"
WIKI_SEARCH = "https://en.wikipedia.org/w/rest.php/v1/search/page"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"

APP = "btm-skills"  # the instant-answer API asks callers to name themselves
TIMEOUT_SECONDS = 30
RESPONSE_CAP_BYTES = 16 * 1024 * 1024
PAGE_CAP_BYTES = 8 * 1024 * 1024
DEFAULT_RESULTS = 8
MAX_RESULTS = 50
SNIPPET_CHARS = 400  # enough to judge a hit, not enough to read the page


class Scholar(StrEnum):
    """Which scholarly index answers. OpenAlex spans every field; Crossref is
    the DOI registry; arXiv is preprints and the only one with full text."""

    OPENALEX = "openalex"
    CROSSREF = "crossref"
    ARXIV = "arxiv"


SCHOLAR_SOURCES = tuple(Scholar)
