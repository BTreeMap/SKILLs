"""Endpoints, limits, and the closed vocabularies the domain is built from."""

from __future__ import annotations

import re

OPENALEX_WORKS = "https://api.openalex.org/works"
ARXIV_QUERY = "https://export.arxiv.org/api/query"
CROSSREF_WORKS = "https://api.crossref.org/works"
DOI_HOST = "doi.org"
TIMEOUT_SECONDS = 30
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

STATUSES = ("candidate", "included", "excluded")
READ_LEVELS = ("none", "abstract", "full-text")
SOURCES = ("openalex", "arxiv", "crossref")
DIRECTIONS = ("backward", "forward")
DECISION_FIELDS = frozenset({"status", "reason", "read_level"})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?$")
JATS_TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^a-z0-9]+")
