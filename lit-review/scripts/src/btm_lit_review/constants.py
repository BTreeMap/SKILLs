"""Endpoints, limits, and the closed vocabularies the domain is built from."""

from __future__ import annotations

from enum import StrEnum

OPENALEX_WORKS = "https://api.openalex.org/works"
ARXIV_QUERY = "https://export.arxiv.org/api/query"
CROSSREF_WORKS = "https://api.crossref.org/works"
DOI_HOST = "doi.org"
TIMEOUT_SECONDS = 30
RESPONSE_CAP_BYTES = (
    16 * 1024 * 1024
)  # an index page is kilobytes; a cap bounds a stall
DEFAULT_LIMIT = 25
MAX_LIMIT = 100
ID_BATCH_SIZE = 50
COURTESY_PAUSE_SECONDS = 0.2
TITLE_MATCH_FLOOR = 0.6
ABSTRACT_SHOW_LIMIT = 1500
AUTHOR_SHOW_LIMIT = 6
PAD_TAIL = 10
HTTP_OK = 200
HTTP_BAD_REQUEST = 400

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


class Status(StrEnum):
    """Where a paper stands in screening. `EXCLUDED` implies a reason; the
    Paper decoder is the one place that holds the implication."""

    CANDIDATE = "candidate"
    INCLUDED = "included"
    EXCLUDED = "excluded"


class ReadLevel(StrEnum):
    """How deeply a paper was read. Ordered by `READ_RANK`, which is the
    order itself rather than an IntEnum, so the value on disk stays a name."""

    NONE = "none"
    ABSTRACT = "abstract"
    FULL_TEXT = "full-text"


READ_RANK = {level: rank for rank, level in enumerate(ReadLevel)}
# The argparse and validation surfaces read the vocabulary off the type, so a
# variant can never be added in one place and forgotten in the other.
STATUSES = tuple(Status)
READ_LEVELS = tuple(ReadLevel)
SOURCES = ("openalex", "arxiv", "crossref")
DIRECTIONS = ("backward", "forward")
DECISION_FIELDS = frozenset({"status", "reason", "read_level"})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
